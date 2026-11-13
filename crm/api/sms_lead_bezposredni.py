# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do handlowca o leadzie przydzielonym regułą obszaru (ops#347): zadanie i kolejka nocna.

`powiadom_handlowca(lead, ponowne)` jest kolejkowane z `crm.api.leady_webhook` (kolejka
"short", callback `after_commit`) ZAMIAST SMS do dyżurnego CC, ale tylko dla leada z
`custom_przydzial_bezposredni = 1`. Nie jest metodą whitelisted.

Ustawienia siedzą w Single `Volteo SMS Ustawienia` (`lead_bezposredni_wlaczone`,
`tresc_lead_bezposredni`, `limit_dzienny_lead_bezposredni`; token, nadawca i tryb
testowy wspólne z innymi SMS-ami). Przy wyłączonym kanale funkcja kończy się od razu,
bez śladu i bez zapisu. Odbiorcą jest `lead_owner` z chwili wykonania zadania, numer z
`User.mobile_no`. Brak numeru: nikt nie dostaje SMS (decyzja właściciela), tylko ślad,
bez Error Log. Cisza nocna 21:00 do 08:00 (`czy_cisza_nocna`): lead trafia do hasha
Redis `KLUCZ_ODROCZONYCH`, a cron `przetworz_odroczone` co 15 minut wysyła rano, o ile
lead ma nadal tego samego właściciela i znacznik 1. Licznik dnia w Redis jest ten sam,
który czyta panel ustawień (`klucz_licznika_dnia`). Rezerwacja `SET NX` (24 h) chroni
przed podwójną wysyłką; ponowne zgłoszenie ją omija.

Zadanie działa jako `Administrator`, czyta tylko pola z `_dane_leada` (bez `custom_cc`),
a ślady i logi nie niosą numeru, tokenu, treści SMS ani tożsamości CC. Każdy wyjątek
trafia do Error Log, funkcje wejściowe nigdy nie rzucają.
"""

import frappe
import redis
from frappe.utils import cint, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.api.sms_dyzur import _dane_leada, wyslij_sms_do_numeru
from crm.api.sms_handlowiec import _bez_numerow
from crm.api.sms_powitalny import DOCTYPE_USTAWIEN
from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_dyzury import normalizuj_numer_pl
from crm.volteo_reguly_przydzialu import (
	KLUCZ_ODROCZONYCH,
	PLACEHOLDERY_LEAD_BEZPOSREDNI,
	POLE_WLACZONE,
	POLE_ZNACZNIKA,
	TTL_ALERTU_SEK,
	TTL_LICZNIKA_SEK,
	TTL_ODROCZONYCH_SEK,
	TTL_REZERWACJI_SEK,
	WYNIK_BLAD,
	WYNIK_BRAK_NUMERU,
	WYNIK_LIMIT,
	WYNIK_ODLOZ,
	WYNIK_WYLACZONE,
	WYNIK_WYSLIJ,
	czy_wyslac_odroczone,
	czy_znacznik,
	klucz_alertu_limitu,
	klucz_licznika_dnia,
	klucz_rezerwacji,
	limit_dzienny_lead,
	odkoduj_odroczenie_lead,
	szablon_lead_bezposredni,
	tekst_sladu_sms,
	zakoduj_odroczenie_lead,
	zdecyduj_sms,
)
from crm.volteo_sms import numer_do_smsapi, wypelnij_szablon
from crm.volteo_sms_handlowiec import czy_cisza_nocna

TYTUL_BLEDU = "SMS lead bezpośredni"

# Wyniki techniczne (tylko wartość zwracana przez `_przetworz`, nigdy w śladzie).
WYNIK_BRAK_LEADA = "brak_leada"
WYNIK_NIE_DOTYCZY = "nie_dotyczy"
WYNIK_DUPLIKAT = "duplikat"
WYNIK_ODLOZONY_JUZ = "odlozony_juz"


# --- Redis (wszystko przez `make_key`, fail open) ---------------------------------


def _rezerwuj(lead: str) -> bool | None:
	"""SET NX na leadzie (24 h); None gdy Redis niedostępny (fail open)."""
	cache = frappe.cache()
	try:
		return bool(cache.set(cache.make_key(klucz_rezerwacji(lead)), "1", nx=True, ex=TTL_REZERWACJI_SEK))
	except redis.exceptions.RedisError:
		return None


def _cofnij_rezerwacje(lead: str) -> None:
	cache = frappe.cache()
	try:
		cache.delete(cache.make_key(klucz_rezerwacji(lead)))
	except redis.exceptions.RedisError:
		pass


def _wyslane_dzis(chwila) -> int | None:
	"""Dzisiejszy licznik bez zwiększania; None gdy Redis niedostępny."""
	cache = frappe.cache()
	try:
		wartosc = cache.get(cache.make_key(klucz_licznika_dnia(chwila)))
	except redis.exceptions.RedisError:
		return None
	if isinstance(wartosc, bytes):
		wartosc = wartosc.decode("utf-8", "replace")
	return max(0, cint(wartosc))


def _zwieksz_licznik(chwila) -> tuple[int | None, str]:
	"""INCR licznika dnia (ten sam klucz co panel); (wartość po INCR albo None, klucz)."""
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


def _alert_raz_na_dobe(chwila) -> bool:
	"""True, gdy to pierwszy alert "limit" w dobie (albo Redis niedostępny)."""
	cache = frappe.cache()
	try:
		return bool(cache.set(cache.make_key(klucz_alertu_limitu(chwila)), "1", nx=True, ex=TTL_ALERTU_SEK))
	except redis.exceptions.RedisError:
		return True


def _klucz_odroczonych() -> str:
	return frappe.cache().make_key(KLUCZ_ODROCZONYCH)


def _odloz(lead: str, ponowne: bool, wlasciciel: str) -> bool | None:
	"""HSETNX w kolejce odroczonych: True = nowy wpis, False = już czeka, None = Redis niedostępny.

	Metody hash wołane bezpośrednio z `redis.Redis`: `RedisWrapper` nadpisuje część z nich
	(pickle, lokalny cache procesu), a ta kolejka trzyma zwykły tekst JSON."""
	cache = frappe.cache()
	klucz = _klucz_odroczonych()
	try:
		nowy = bool(redis.Redis.hsetnx(cache, klucz, lead, zakoduj_odroczenie_lead(ponowne, wlasciciel)))
		cache.expire(klucz, TTL_ODROCZONYCH_SEK)
		return nowy
	except redis.exceptions.RedisError:
		return None


def _odroczone() -> dict[str, object]:
	"""Cała kolejka odroczonych {lead: surowa wartość}; pusta przy braku albo awarii Redis."""
	cache = frappe.cache()
	try:
		wpisy = redis.Redis.hgetall(cache, _klucz_odroczonych()) or {}
	except redis.exceptions.RedisError:
		return {}
	return {(k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)): v for k, v in wpisy.items()}


def _usun_odroczenie(lead: str) -> None:
	cache = frappe.cache()
	try:
		redis.Redis.hdel(cache, _klucz_odroczonych(), lead)
	except redis.exceptions.RedisError:
		pass


# --- Zadanie -------------------------------------------------------------------------


def _slad(lead: str, wynik: str, imie: str) -> None:
	zapisz_slad(lead, tekst_sladu_sms(wynik, imie), doctype="CRM Lead")


def _loguj(tytul_dopisek: str, lead: str, tresc: str) -> None:
	"""`frappe.log_error` z gwarancją, że samo logowanie nie rzuci."""
	try:
		frappe.log_error(title=f"{TYTUL_BLEDU}{tytul_dopisek}", message=f"Lead {lead}: {tresc}")
	except Exception:
		pass


def _przetworz(lead: str, ponowne: bool = False, *, teraz=None, z_kolejki: bool = False) -> str:
	"""Cała logika zadania BEZ commita; zwraca stałą wyniku (dla sond). `teraz` podmienia chwilę.
	`z_kolejki=True` woła harmonogram odroczonych: bez ponownego odkładania.

	Uwaga dla sond: funkcja przełącza sesję na `Administrator` i jej nie przywraca."""
	ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
	if not cint(ustawienia.get(POLE_WLACZONE)):
		return WYNIK_WYLACZONE

	frappe.set_user("Administrator")  # autor śladu neutralny, zadanie nie dziedziczy sesji webhooka

	wiersz = frappe.db.get_value("CRM Lead", lead, ["lead_owner", POLE_ZNACZNIKA], as_dict=True)
	if not wiersz:
		_usun_odroczenie(lead)
		return WYNIK_BRAK_LEADA
	wlasciciel = wiersz.get("lead_owner") or ""
	if not wlasciciel or not czy_znacznik(wiersz.get(POLE_ZNACZNIKA)):
		return WYNIK_NIE_DOTYCZY  # lead nie jest już przydzielony regułą: bez śladu

	osoba = frappe.db.get_value("User", wlasciciel, ["enabled", "full_name", "mobile_no"], as_dict=True) or {}
	imie = osoba.get("full_name") or wlasciciel
	numer = (
		numer_do_smsapi(normalizuj_numer_pl(osoba.get("mobile_no"))) if cint(osoba.get("enabled")) else None
	)

	teraz = teraz or now_datetime()
	w_ciszy = (not z_kolejki) and czy_cisza_nocna(teraz)
	wyslane = _wyslane_dzis(teraz)
	limit = limit_dzienny_lead(ustawienia)
	wynik = zdecyduj_sms(True, bool(numer), w_ciszy, wyslane or 0, limit)

	if wynik == WYNIK_BRAK_NUMERU:
		_slad(lead, wynik, imie)  # SMS nie idzie do nikogo, bez Error Log
		return wynik

	if wynik == WYNIK_LIMIT:
		_slad(lead, wynik, imie)
		if _alert_raz_na_dobe(teraz):
			_loguj(": limit dzienny", lead, "dzienny limit SMS o leadach dla handlowców wyczerpany.")
		return wynik

	if wynik == WYNIK_ODLOZ:
		nowy = _odloz(lead, ponowne, wlasciciel)
		if nowy is None:
			# Awaria Redis: fail open, wysyłamy od razu (jak SMS powitalny), z wpisem w Error Log.
			_loguj("", lead, "cisza nocna, a Redis niedostępny: SMS wysłany od razu (fail open).")
		else:
			if nowy:
				_slad(lead, WYNIK_ODLOZ, imie)
			return WYNIK_ODLOZ if nowy else WYNIK_ODLOZONY_JUZ

	return _wyslij(lead, ponowne, ustawienia, numer or "", imie, teraz, limit)


def _wyslij(lead: str, ponowne: bool, ustawienia: dict, numer: str, imie: str, teraz, limit: int) -> str:
	"""Rezerwacja, licznik, treść i wysyłka; ślad z wynikiem. Zwraca WYNIK_WYSLIJ albo WYNIK_BLAD itd."""
	zarezerwowano = False
	if not ponowne:
		rezerwacja = _rezerwuj(lead)
		if rezerwacja is False:
			return WYNIK_DUPLIKAT  # inne zadanie tego samego leada już go obsłużyło
		if rezerwacja is None:
			_loguj("", lead, "Redis niedostępny, deduplikacja pominięta (fail open).")
		zarezerwowano = bool(rezerwacja)

	licznik, klucz_licznika = _zwieksz_licznik(teraz)
	if licznik is None:
		_loguj("", lead, "Redis niedostępny, limit dzienny pominięty (fail open).")
	elif licznik > limit:
		_cofnij_licznik(klucz_licznika)
		if zarezerwowano:
			_cofnij_rezerwacje(lead)
		_slad(lead, WYNIK_LIMIT, imie)
		if _alert_raz_na_dobe(teraz):
			_loguj(": limit dzienny", lead, "dzienny limit SMS o leadach dla handlowców wyczerpany.")
		return WYNIK_LIMIT

	def _blad(powod: str) -> str:
		if licznik is not None:
			_cofnij_licznik(klucz_licznika)
		if zarezerwowano:
			_cofnij_rezerwacje(lead)
		_slad(lead, WYNIK_BLAD, imie)
		_loguj("", lead, _bez_numerow(powod))
		return WYNIK_BLAD

	tresc, _ostrzezenie = wypelnij_szablon(
		szablon_lead_bezposredni(ustawienia, ponowne), _dane_leada(lead), PLACEHOLDERY_LEAD_BEZPOSREDNI
	)
	if not tresc:
		return _blad("pusta treść SMS po wypełnieniu szablonu.")

	token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
	if not token:
		return _blad("brak tokenu SMSAPI w Volteo SMS Ustawienia.")

	ok, powod, tryb_testowy = wyslij_sms_do_numeru(numer, tresc, ustawienia, token)
	if not ok:
		return _blad(powod)
	if tryb_testowy and licznik is not None:
		_cofnij_licznik(klucz_licznika)  # nic nie wyszło do sieci, limit liczy realne SMS-y
	_slad(lead, WYNIK_WYSLIJ, imie)
	return WYNIK_WYSLIJ


def powiadom_handlowca(lead: str, ponowne: bool = False) -> None:
	"""Zadanie RQ (kolejka "short"): `_przetworz` + commit śladów. Nigdy nie rzuca."""
	try:
		_przetworz(lead, bool(ponowne))
		frappe.db.commit()
	except Exception:
		_loguj("", lead, f"nieoczekiwany wyjątek\n{frappe.get_traceback()}")


def przetworz_odroczone() -> None:
	"""Harmonogram (cron co 15 minut, `hooks.py`): po ciszy nocnej wysyła odroczone SMS-y.

	W ciszy i przy pustej kolejce nic nie robi. Dla każdego leada sprawdza, że nadal istnieje,
	ma tego samego `lead_owner` i znacznik 1; wtedy wysyła (już bez ciszy), inaczej tylko
	usuwa wpis. Wyjątek przy jednym leadzie nie przerywa pętli, wpis znika po przetworzeniu
	także po błędzie. Nigdy nie rzuca."""
	try:
		teraz = now_datetime()
		if czy_cisza_nocna(teraz):
			return
		for lead, surowy in _odroczone().items():
			try:
				odczyt = odkoduj_odroczenie_lead(surowy)
				if odczyt is None:
					_loguj("", lead, "nieczytelny wpis kolejki odroczonych, pominięty.")
				else:
					ponowne, wlasciciel = odczyt
					biezacy = frappe.db.get_value(
						"CRM Lead", lead, ["lead_owner", POLE_ZNACZNIKA], as_dict=True
					)
					if biezacy and czy_wyslac_odroczone(
						wlasciciel, biezacy.get("lead_owner"), biezacy.get(POLE_ZNACZNIKA)
					):
						_przetworz(lead, ponowne, teraz=teraz, z_kolejki=True)
			except Exception:
				_loguj("", lead, f"odroczony SMS, nieoczekiwany wyjątek\n{frappe.get_traceback()}")
			finally:
				_usun_odroczenie(lead)
			frappe.db.commit()
	except Exception:
		_loguj("", "-", f"kolejka odroczonych: nieoczekiwany wyjątek\n{frappe.get_traceback()}")
