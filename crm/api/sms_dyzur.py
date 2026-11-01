# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do dyżurnego backoffice po leadzie z Facebooka (ops#313): zadanie w tle.

`powiadom_dyzurnego(lead)` jest kolejkowane z `crm.api.leady_webhook.przyjmij`
(kolejka "short", callback `after_commit`) obok SMS powitalnego dla klienta, wyłącznie
po udanym insercie nowego leada. Nie jest metodą whitelisted.

Ustawienia siedzą w Single `Volteo SMS Ustawienia` (token, nadawca i tryb testowy
wspólne z SMS powitalnym; osobne `dyzur_wlaczone`, `tresc_dyzur`,
`limit_dzienny_dyzur`). Checki czytamy zawsze przez `cint(get_singles_dict(...))`.
Przy wyłączonym kanale funkcja kończy się od razu: bez tokenu, bez zapisu, bez śladu.

Dyżurny to użytkownik z aktywnego wiersza grafiku `Volteo Dyzur SMS` pasującego do
chwili (czas serwera w strefie site). Numer czytamy z `User.mobile_no`. Lead NIE jest
przypisywany (to tylko powiadomienie). Wynik ląduje w Aktywności leada; ślad i log nigdy
nie niosą numeru dyżurnego ani tokenu. Dzienny limit liczy atomowo Redis `INCR`
(produkcja ma dwa workery kolejki short), przy awarii Redis działa fail open.

Cała decyzja i treść są w `crm/volteo_dyzury.py` (bez `frappe`); funkcja łapie każdy
wyjątek i nigdy nie rzuca.
"""

import frappe
import redis
from frappe.utils import cint, get_url, getdate, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.api.sms_powitalny import DOCTYPE_USTAWIEN, _http_post
from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_dyzury import (
	LIMIT_DZIENNY_DYZUR_DOMYSLNY,
	TRESC_DYZUR_DOMYSLNA,
	TTL_LICZNIKA_SEK,
	czy_wyjatek_dnia,
	dyzurni_w_chwili,
	klucz_licznika_dnia,
	zbuduj_tresc_dyzur,
	zdecyduj_wysylke_dyzur,
)
from crm.volteo_sms import (
	NADAWCA_DOMYSLNY,
	SMSAPI_URL,
	interpretuj_odpowiedz,
	numer_do_smsapi,
	zbuduj_parametry,
)

DOCTYPE_GRAFIKU = "Volteo Dyzur SMS"
TYTUL_BLEDU = "SMS dyżurowy"


def _licznik_dnia(chwila) -> tuple[int | None, str]:
	"""Zwiększa dzienny licznik; (wartość po INCR albo None gdy Redis niedostępny, klucz)."""
	cache = frappe.cache()
	klucz = cache.make_key(klucz_licznika_dnia(chwila))
	try:
		wartosc = cint(cache.incr(klucz))
		cache.expire(klucz, TTL_LICZNIKA_SEK)
		return wartosc, klucz
	except redis.exceptions.RedisError:
		return None, klucz


def _cofnij_licznik(klucz: str) -> None:
	try:
		frappe.cache().decr(klucz)
	except redis.exceptions.RedisError:
		pass


def _dane_leada(lead: str) -> dict:
	wiersz = frappe.db.get_value(
		"CRM Lead",
		lead,
		["first_name", "last_name", "mobile_no", "custom_install_postal_code", "custom_install_city"],
		as_dict=True,
	)
	if not wiersz:
		return {}
	klient = " ".join(p for p in (wiersz.first_name, wiersz.last_name) if p).strip()
	return {
		"klient": klient,
		"telefon": wiersz.mobile_no or "",
		"kod": wiersz.custom_install_postal_code or "",
		"miejscowosc": wiersz.custom_install_city or "",
		"link": get_url("/crm/leads/" + lead),
	}


def wyslij_sms_do_numeru(numer: str, tresc: str, ustawienia: dict, token: str) -> tuple[bool, str, bool]:
	"""Wspólny rdzeń HTTP do SMSAPI: (ok, powód, tryb_testowy). Nie rzuca przy błędzie połączenia."""
	tryb_testowy = bool(cint(ustawienia.get("tryb_testowy")))
	parametry = zbuduj_parametry(numer, tresc, ustawienia.get("nadawca") or NADAWCA_DOMYSLNY, tryb_testowy)
	try:
		kod_http, odpowiedz = _http_post(SMSAPI_URL, parametry, {"Authorization": f"Bearer {token}"})
		wynik = interpretuj_odpowiedz(kod_http, odpowiedz)
	except Exception as wyjatek:  # tekst wyjątku requests może nieść URL, więc tylko typ
		return False, f"Błąd połączenia z SMSAPI ({type(wyjatek).__name__}).", tryb_testowy
	return bool(wynik.ok), wynik.powod, tryb_testowy


def _wyslij_jednemu(
	*,
	lead: str,
	uzytkownik: str,
	ustawienia: dict,
	token,
	tresc_szablon: str,
	dane: dict,
	chwila,
	redis_ostrzezono: list,
) -> None:
	osoba = frappe.db.get_value("User", uzytkownik, ["full_name", "mobile_no"], as_dict=True) or {}
	imie = osoba.get("full_name") or uzytkownik
	numer = numer_do_smsapi(osoba.get("mobile_no"))
	limit = (
		cint(ustawienia.get("limit_dzienny_dyzur"))
		if ustawienia.get("limit_dzienny_dyzur") not in (None, "")
		else LIMIT_DZIENNY_DYZUR_DOMYSLNY
	)

	licznik, klucz = (None, "")
	wyslane_dzis = 0
	if numer and token:
		licznik, klucz = _licznik_dnia(chwila)
		if licznik is None:
			if not redis_ostrzezono:
				redis_ostrzezono.append(True)
				frappe.log_error(
					title=TYTUL_BLEDU,
					message=f"Lead {lead}: Redis cache niedostępny, limit dzienny pominięty",
				)
		else:
			wyslane_dzis = licznik - 1

	decyzja = zdecyduj_wysylke_dyzur(
		wlaczone=True,
		token_ustawiony=bool(token),
		chwila=chwila,
		dyzurni=[uzytkownik],
		imie_dyzurnego=imie,
		numer=numer,
		limit_dzienny=limit,
		wyslane_dzis=wyslane_dzis,
	)
	if not decyzja.wyslij:
		if licznik is not None:
			_cofnij_licznik(klucz)
		zapisz_slad(lead, decyzja.slad, doctype="CRM Lead")
		frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: {decyzja.slad}")
		return

	tresc, ostrzezenie = zbuduj_tresc_dyzur(tresc_szablon, dane)
	if not tresc:
		if licznik is not None:
			_cofnij_licznik(klucz)
		zapisz_slad(lead, f"SMS dyżurowy pominięty: pusta treść ({imie})", doctype="CRM Lead")
		return

	ok, powod, tryb_testowy = wyslij_sms_do_numeru(numer or "", tresc, ustawienia, token)
	if not ok:
		if licznik is not None:
			_cofnij_licznik(klucz)
		zapisz_slad(lead, f"SMS dyżurowy: błąd SMSAPI ({imie}): {powod}", doctype="CRM Lead")
		frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: {powod}")
		return

	if tryb_testowy:
		if licznik is not None:
			_cofnij_licznik(klucz)
		zapisz_slad(
			lead, f"SMS dyżurowy: test SMSAPI OK (nic nie wysłano), dyżurny {imie}", doctype="CRM Lead"
		)
	else:
		zapisz_slad(lead, f"SMS dyżurowy wysłany do {imie}", doctype="CRM Lead")
	if ostrzezenie:
		frappe.log_error(
			title="SMS dyżurowy: treść dłuższa niż 1 część", message=f"Lead {lead}: {ostrzezenie}"
		)


def powiadom_dyzurnego(lead: str) -> None:
	"""Zadanie w tle: patrz docstring modułu. Nigdy nie rzuca."""
	try:
		ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
		if not cint(ustawienia.get("dyzur_wlaczone")):
			return  # kanał wyłączony: nic nie czytamy i nic nie zapisujemy
		if not frappe.db.exists("CRM Lead", lead):
			return

		chwila = now_datetime()
		grafik = frappe.get_all(
			DOCTYPE_GRAFIKU,
			filters={"aktywny": 1},
			fields=["dzien_tygodnia", "od", "do", "uzytkownik", "aktywny", "data", "bez_dyzuru"],
			or_filters=[["data", "is", "not set"], ["data", ">=", getdate(chwila)]],
			limit_page_length=500,
		)
		dyzurni = dyzurni_w_chwili(grafik, chwila)
		if not dyzurni:
			decyzja = zdecyduj_wysylke_dyzur(
				wlaczone=True,
				token_ustawiony=True,
				chwila=chwila,
				dyzurni=[],
				wyjatek_dnia=czy_wyjatek_dnia(grafik, chwila),
			)
			zapisz_slad(lead, decyzja.slad, doctype="CRM Lead")
			frappe.db.commit()
			return

		token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
		dane = _dane_leada(lead)
		szablon = ustawienia.get("tresc_dyzur") or TRESC_DYZUR_DOMYSLNA
		redis_ostrzezono: list = []
		for uzytkownik in dyzurni:
			try:
				_wyslij_jednemu(
					lead=lead,
					uzytkownik=uzytkownik,
					ustawienia=ustawienia,
					token=token,
					tresc_szablon=szablon,
					dane=dane,
					chwila=chwila,
					redis_ostrzezono=redis_ostrzezono,
				)
			except Exception:
				frappe.log_error(
					title=TYTUL_BLEDU, message=f"Lead {lead}: nieoczekiwany wyjątek\n{frappe.get_traceback()}"
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(
			title=TYTUL_BLEDU, message=f"Lead {lead}: nieoczekiwany wyjątek\n{frappe.get_traceback()}"
		)
