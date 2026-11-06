# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Panel "SMS do handlowców" (PLAN-SMS-HANDLOWIEC.md, sekcja 8.4): API dla Ustawienia.

Odczyt i zapis ustawień SMS do handlowca w Single `Volteo SMS Ustawienia`
(`handlowiec_wlaczone`, `handlowiec_odwolanie_wlaczone`, trzy szablony,
`limit_dzienny_handlowiec`), podgląd szablonu na danych przykładowych, SMS testowy na
numer zalogowanego administratora i lista handlowców (`Volteo D2D Sales`) ze stanem
numeru telefonu. Numer handlowca zapisuje istniejące
`crm.api.dyzury.volteo_dyzur_telefon_zapisz` (bez zmian w tamtym module).

Dostęp wyłącznie dla `Volteo Core Admin` / `System Manager` (`frappe.only_for` jako
pierwsza instrukcja każdej metody, wzorzec `crm.api.dyzury`). Panel nigdy nie zmienia
`tryb_testowy` ani tokenu (oba wspólne z SMS powitalnym i dyżurowym) i nigdy nie zwraca
tokenu (tylko `token_ustawiony`). SMS testowy liczy się do dziennego limitu SMS do
handlowców (klucz Redis z rdzenia `crm.volteo_sms_handlowiec.klucz_licznika_dnia`, ten sam,
który zwiększa adapter), respektuje `tryb_testowy` i ignoruje ciszę nocną (jawna akcja
administratora). Numer telefonu wołającego nie trafia do odpowiedzi ani do Error Log.

Cała logika treści i walidacji jest w `crm/volteo_sms_handlowiec.py` (bez `frappe`).
"""

import re
from typing import Any

import frappe
import redis
from frappe import _
from frappe.utils import cint, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.api.sms_dyzur import wyslij_sms_do_numeru
from crm.api.sms_powitalny import DOCTYPE_USTAWIEN
from crm.volteo_dyzury import normalizuj_numer_pl
from crm.volteo_sms import dlugosc_gsm7, liczba_czesci_sms, numer_do_smsapi
from crm.volteo_sms_handlowiec import (
	CISZA_DO,
	CISZA_OD,
	DANE_PRZYKLADOWE_HANDLOWIEC,
	PLACEHOLDERY_HANDLOWIEC,
	POLA_SZABLONOW,
	POLE_LIMITU,
	POLE_ODWOLANIE_WLACZONE,
	POLE_WLACZONE,
	TRESCI_DOMYSLNE,
	TTL_LICZNIKA_SEK,
	TYP_NOWE,
	TYP_ODWOLANIE,
	TYP_ZMIANA,
	TYPY,
	czy_flaga,
	klucz_licznika_dnia,
	limit_dzienny,
	szablon_dla,
	waliduj_limit_handlowiec,
	waliduj_tresc_handlowiec,
	zbuduj_tresc_handlowiec,
)

DOPUSZCZONE_ROLE_WOLAJACEGO = ["Volteo Core Admin", "System Manager"]
ROLA_HANDLOWCA = "Volteo D2D Sales"
POLE_LINII_LEADY = "custom_linia_leady"
TYTUL_BLEDU = "SMS do handlowców (test)"

_CIAG_CYFR = re.compile(r"\+?\d(?:[\s\-.]?\d){4,}")


def _bez_numerow(tekst: Any) -> str:
	"""Tekst powodu bez ciągów cyfr wyglądających na numer telefonu (odpowiedź SMSAPI bywa z numerem)."""
	return _CIAG_CYFR.sub("***", str(tekst or ""))


def _ustawienia() -> dict[str, Any]:
	return frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}


def _token_ustawiony() -> bool:
	return bool(
		get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
	)


def _wyslane_dzis() -> int | None:
	"""Dzisiejszy licznik SMS do handlowców (bez zwiększania); None, gdy Redis niedostępny."""
	cache = frappe.cache()
	try:
		wartosc = cache.get(cache.make_key(klucz_licznika_dnia(now_datetime())))
	except redis.exceptions.RedisError:
		return None
	if isinstance(wartosc, bytes):
		wartosc = wartosc.decode("utf-8", "replace")
	return max(0, cint(wartosc))


def _zwieksz_licznik() -> tuple[int | None, str]:
	"""INCR dziennego licznika SMS do handlowców; (wartość po INCR albo None przy awarii Redis, klucz)."""
	cache = frappe.cache()
	klucz = cache.make_key(klucz_licznika_dnia(now_datetime()))
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


def _numer_ok(mobile_no: Any) -> bool:
	return bool(numer_do_smsapi(normalizuj_numer_pl(mobile_no)))


def _handlowcy() -> list[dict[str, Any]]:
	"""Aktywni użytkownicy z rolą `Volteo D2D Sales`: najpierw bez poprawnego numeru, potem z linią Leady."""
	nazwy = frappe.get_all(
		"Has Role",
		filters={"role": ROLA_HANDLOWCA, "parenttype": "User"},
		pluck="parent",
		distinct=True,
		limit_page_length=1000,
	)
	nazwy = [n for n in nazwy if n not in ("Administrator", "Guest")]
	if not nazwy:
		return []
	ma_pole_linii = frappe.get_meta("User").has_field(POLE_LINII_LEADY)
	pola = ["name", "full_name", "mobile_no"] + ([POLE_LINII_LEADY] if ma_pole_linii else [])
	wiersze = frappe.get_all(
		"User",
		filters={"name": ["in", nazwy], "enabled": 1},
		fields=pola,
		order_by="full_name asc",
		limit_page_length=1000,
	)
	handlowcy = [
		{
			"uzytkownik": u["name"],
			"imie_nazwisko": u.get("full_name") or u["name"],
			# brak pola na site = linia Leady dozwolona (jak `crm.permissions.org_hierarchy`)
			"linia_leady": 1 if (cint(u.get(POLE_LINII_LEADY)) if ma_pole_linii else 1) else 0,
			"mobile_no": u.get("mobile_no") or "",
			"numer_ok": _numer_ok(u.get("mobile_no")),
		}
		for u in wiersze
	]
	handlowcy.sort(key=lambda h: (h["numer_ok"], not h["linia_leady"], h["imie_nazwisko"].lower()))
	return handlowcy


def _stan() -> dict[str, Any]:
	ustawienia = _ustawienia()
	return {
		POLE_WLACZONE: 1 if czy_flaga(ustawienia, POLE_WLACZONE) else 0,
		POLE_ODWOLANIE_WLACZONE: 1 if czy_flaga(ustawienia, POLE_ODWOLANIE_WLACZONE) else 0,
		**{pole: szablon_dla(typ, ustawienia) for typ, pole in POLA_SZABLONOW.items()},
		POLE_LIMITU: limit_dzienny(ustawienia),
		"tryb_testowy": cint(ustawienia.get("tryb_testowy")),
		"token_ustawiony": _token_ustawiony(),
		"wyslane_dzis": _wyslane_dzis(),
		"cisza_od": CISZA_OD,
		"cisza_do": CISZA_DO,
		"placeholdery": list(PLACEHOLDERY_HANDLOWIEC),
		"dane_przykladowe": dict(DANE_PRZYKLADOWE_HANDLOWIEC),
		"tresci_domyslne": {POLA_SZABLONOW[typ]: tresc for typ, tresc in TRESCI_DOMYSLNE.items()},
		"handlowcy": _handlowcy(),
	}


@frappe.whitelist()
def volteo_sms_handlowiec_lista() -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	return _stan()


@frappe.whitelist()
def volteo_sms_handlowiec_zapisz(
	handlowiec_wlaczone: int | None = None,
	handlowiec_odwolanie_wlaczone: int | None = None,
	tresc_handlowiec_nowe: str | None = None,
	tresc_handlowiec_zmiana: str | None = None,
	tresc_handlowiec_odwolanie: str | None = None,
	limit_dzienny_handlowiec: int | None = None,
) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	zmiany: dict[str, Any] = {}
	if handlowiec_wlaczone is not None:
		zmiany[POLE_WLACZONE] = 1 if cint(handlowiec_wlaczone) else 0
	if handlowiec_odwolanie_wlaczone is not None:
		zmiany[POLE_ODWOLANIE_WLACZONE] = 1 if cint(handlowiec_odwolanie_wlaczone) else 0

	szablony = {
		POLA_SZABLONOW[TYP_NOWE]: (tresc_handlowiec_nowe, "nowe spotkanie"),
		POLA_SZABLONOW[TYP_ZMIANA]: (tresc_handlowiec_zmiana, "zmiana terminu"),
		POLA_SZABLONOW[TYP_ODWOLANIE]: (tresc_handlowiec_odwolanie, "odwołanie"),
	}
	for pole, (tresc, nazwa) in szablony.items():
		if tresc is None:
			continue
		komunikat = waliduj_tresc_handlowiec(tresc)
		if komunikat:
			frappe.throw(_("Szablon SMS ({0}): {1}").format(nazwa, _(komunikat)))
		zmiany[pole] = tresc.strip()

	if limit_dzienny_handlowiec is not None:
		komunikat = waliduj_limit_handlowiec(limit_dzienny_handlowiec)
		if komunikat:
			frappe.throw(_(komunikat))
		zmiany[POLE_LIMITU] = cint(limit_dzienny_handlowiec)

	# zapis dopiero po walidacji wszystkich pól: błąd w jednym nie zostawia połowy zmian
	for pole, wartosc in zmiany.items():
		frappe.db.set_single_value(DOCTYPE_USTAWIEN, pole, wartosc)
	return _stan()


@frappe.whitelist()
def volteo_sms_handlowiec_podglad(tresc: str | None = None) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	blad = waliduj_tresc_handlowiec(tresc)
	gotowa, ostrzezenie = zbuduj_tresc_handlowiec(tresc or "", DANE_PRZYKLADOWE_HANDLOWIEC)
	return {
		"tresc": gotowa,
		"dlugosc": dlugosc_gsm7(gotowa),
		"czesci": liczba_czesci_sms(gotowa),
		"ostrzezenie": ostrzezenie,
		"blad": blad,
	}


@frappe.whitelist()
def volteo_sms_handlowiec_test(typ: str = TYP_NOWE) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	if typ not in TYPY:
		frappe.throw(_("Nieznany rodzaj SMS testowego. Dozwolone: nowe, zmiana, odwolanie."))
	ustawienia = _ustawienia()
	token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
	if not token:
		frappe.throw(_("Brak tokenu SMSAPI. Uzupełnij go w Desk: Volteo SMS Ustawienia."))
	numer = numer_do_smsapi(
		normalizuj_numer_pl(frappe.db.get_value("User", frappe.session.user, "mobile_no"))
	)
	if not numer:
		frappe.throw(
			_(
				"Brak Twojego numeru telefonu komórkowego albo numer jest niepoprawny. Uzupełnij go w"
				" Ustawienia, Dyżury SMS, sekcja Numery telefonów dyżurnych, albo w profilu użytkownika"
				" (pole Mobile No)."
			)
		)
	tresc, ostrzezenie = zbuduj_tresc_handlowiec(szablon_dla(typ, ustawienia), DANE_PRZYKLADOWE_HANDLOWIEC)
	limit = limit_dzienny(ustawienia)

	# cisza nocna celowo pominięta: SMS testowy to jawna akcja administratora
	licznik, klucz = _zwieksz_licznik()
	if licznik is not None and licznik - 1 >= limit:
		_cofnij_licznik(klucz)
		return {
			"ok": False,
			"powod": _("Wyczerpany dzienny limit SMS do handlowców ({0}).").format(limit),
			"tryb_testowy": cint(ustawienia.get("tryb_testowy")),
			"tresc": tresc,
			"ostrzezenie": ostrzezenie,
		}

	ok, powod, tryb_testowy = wyslij_sms_do_numeru(numer, tresc, ustawienia, token)
	powod = _bez_numerow(powod)
	if not ok:
		if licznik is not None:
			_cofnij_licznik(klucz)
		frappe.log_error(title=TYTUL_BLEDU, message=f"Typ {typ}: {powod}")
	elif tryb_testowy and licznik is not None:
		_cofnij_licznik(klucz)  # tryb testowy: SMS nie wyszedł do sieci, jak w SMS dyżurowym
	return {
		"ok": bool(ok),
		"powod": powod,
		"tryb_testowy": 1 if tryb_testowy else 0,
		"tresc": tresc,
		"ostrzezenie": ostrzezenie,
	}
