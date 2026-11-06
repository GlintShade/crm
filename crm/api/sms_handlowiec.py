# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do handlowca po umówieniu spotkania (PLAN-SMS-HANDLOWIEC.md, 7.1 do 7.4): adapter.

Hak `zakolejkuj_sms_handlowca(doc)` woła `CRMLead.on_update` zaraz po
`powiadom_o_zmianie_terminu`. Hak tylko kolejkuje: po commicie (własny callback
`after_commit`) rusza zadanie `wyslij_sms_handlowcowi` w kolejce "short". Wycofana
transakcja nie wysyła nic. Moduł nie jest whitelisted (to nie jest API).

Zadanie czyta BIEŻĄCY stan leada, porównuje go z bazą (ostatni przetworzony stan z
Redis albo stan "przed" z ładunku) i dla każdego zdarzenia z rdzenia
(`crm/volteo_sms_handlowiec.py`) sprawdza odbiorcę (aktywne konto z rolą
`Volteo D2D Sales`), własną zmianę, numer `User.mobile_no`, rezerwację, limit dzienny,
po czym wysyła przez wspólny `crm.api.sms_dyzur.wyslij_sms_do_numeru` i zapisuje ślad
w Aktywności jako `Administrator` (autor śladu nigdy nie zdradza CC).

Cisza nocna (decyzja Jana D4, 21:00 do 08:00): zadanie w ciszy nie wysyła, tylko odkłada
lead do kolejki odroczonych w Redis (`KLUCZ_ODROCZONYCH`, HSETNX: zostaje stan "przed"
z PIERWSZEGO odroczenia) i raz na noc zapisuje ślad "odłożony". Harmonogram
`przetworz_odroczone` (cron co 15 minut) po końcu ciszy przetwarza każdy odroczony lead
od nowa na bieżącym stanie: jeden właściwy SMS, nawet gdy w nocy termin zmieniano kilka
razy; spotkanie już w przeszłości nie daje SMS. Restart Redis w nocy gubi kolejkę
(ryzyko przyjęte, REVISIT).

Wymaganie właściciela: brak albo niepoprawny numer handlowca, usunięty lead, wyłączone
konto, brak tokenu, błąd SMSAPI czy niedostępny Redis NIGDY nie psują zapisu leada ani
żadnego żądania. Hak i zadanie łapią każdy wyjątek do Error Log. Ślady i Error Log nie
niosą numeru handlowca ani klienta, tokenu ani treści SMS.
"""

import re
from functools import partial

import frappe
import redis
from frappe.utils import cint, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.api.sms_dyzur import wyslij_sms_do_numeru
from crm.api.sms_powitalny import DOCTYPE_USTAWIEN
from crm.volteo_aktywnosc import ROLA_D2D, zapisz_slad
from crm.volteo_dyzury import normalizuj_numer_pl
from crm.volteo_powiadomienia import POLA_LEADA
from crm.volteo_sms import numer_do_smsapi
from crm.volteo_sms_handlowiec import (
	KLUCZ_ODROCZONYCH,
	POLE_ODWOLANIE_WLACZONE,
	POLE_WLACZONE,
	STAN_PUSTY,
	TTL_ALERTU_SEK,
	TTL_LICZNIKA_SEK,
	TTL_ODROCZONYCH_SEK,
	TTL_REZERWACJI_SEK,
	TTL_STANU_SEK,
	WYNIK_BLAD,
	WYNIK_BRAK_NUMERU,
	WYNIK_LIMIT,
	WYNIK_ODLOZONY,
	WYNIK_TEST,
	WYNIK_WLASNA_ZMIANA,
	WYNIK_WYSLANY,
	Zdarzenie,
	czy_cisza_nocna,
	czy_flaga,
	czy_kandydat,
	czy_masowa,
	dane_do_szablonu,
	klucz_alertu,
	klucz_licznika_dnia,
	klucz_rezerwacji,
	klucz_stanu,
	limit_dzienny,
	normalizuj_stan,
	odkoduj_odroczenie,
	odkoduj_stan,
	opis_sladu,
	szablon_dla,
	ustal_zdarzenia,
	zakoduj_odroczenie,
	zakoduj_stan,
	zbuduj_tresc_handlowiec,
)

TYTUL_BLEDU = "SMS do handlowców"
METODA_ZADANIA = "crm.api.sms_handlowiec.wyslij_sms_handlowcowi"

FLAGA_BEZ_SMS = "volteo_bez_sms_handlowca"
"""Ustawiona przez `crm.api.volteo_leady.przydziel` (pakiet nie wysyła, decyzja D7) i przez
skrypty ops, które zapisują leady przez `doc.save()`."""
FLAGA_LICZNIKA = "volteo_sms_handlowiec_licznik"
FLAGA_POMINIETYCH = "volteo_sms_handlowiec_pominiete"
FLAGI_WYJSCIA: tuple[str, ...] = (
	"in_import",
	"in_migrate",
	"in_patch",
	"in_install",
	"in_setup_wizard",
	FLAGA_BEZ_SMS,
)

# Wyniki techniczne (tylko w liście zwracanej przez `_przetworz`, nigdy w śladzie).
WYNIK_WYLACZONE = "wylaczone"
WYNIK_BRAK_LEADA = "brak_leada"
WYNIK_NIE_HANDLOWIEC = "nie_handlowiec"
WYNIK_DUPLIKAT = "duplikat"
WYNIK_ODLOZONY_BEZ_REDIS = "odlozony_bez_redis"

_CIAG_CYFR = re.compile(r"\+?\d(?:[\s\-.]?\d){4,}")


def _bez_numerow(tekst: str | None) -> str:
	"""Wycina z tekstu (np. powodu z SMSAPI) ciągi cyfr wyglądające na numer telefonu."""
	return _CIAG_CYFR.sub("***", str(tekst or ""))


# --- Redis (wszystko przez `make_key`, fail open) ---------------------------------


def _odczytaj_stan(lead: str) -> tuple[str, str] | None:
	cache = frappe.cache()
	try:
		return odkoduj_stan(cache.get(cache.make_key(klucz_stanu(lead))))
	except redis.exceptions.RedisError:
		return None


def _zapisz_stan(lead: str, stan: tuple[str, str]) -> None:
	cache = frappe.cache()
	try:
		cache.set(cache.make_key(klucz_stanu(lead)), zakoduj_stan(stan), ex=TTL_STANU_SEK)
	except redis.exceptions.RedisError:
		pass


def _rezerwuj(klucz: str) -> bool | None:
	"""SET NX na kluczu zdarzenia; None gdy Redis niedostępny (fail open)."""
	cache = frappe.cache()
	try:
		return bool(cache.set(cache.make_key(klucz), "1", nx=True, ex=TTL_REZERWACJI_SEK))
	except redis.exceptions.RedisError:
		return None


def _cofnij_rezerwacje(klucz: str) -> None:
	cache = frappe.cache()
	try:
		cache.delete(cache.make_key(klucz))
	except redis.exceptions.RedisError:
		pass


def _licznik_dnia(chwila) -> tuple[int | None, str]:
	"""INCR dziennego licznika; (wartość po INCR albo None gdy Redis niedostępny, klucz)."""
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


def _alert_raz_na_dobe(rodzaj: str, chwila) -> bool:
	"""True, gdy to pierwszy alert danego rodzaju w dobie (albo Redis niedostępny)."""
	cache = frappe.cache()
	try:
		return bool(cache.set(cache.make_key(klucz_alertu(rodzaj, chwila)), "1", nx=True, ex=TTL_ALERTU_SEK))
	except redis.exceptions.RedisError:
		return True


def _klucz_odroczonych() -> str:
	return frappe.cache().make_key(KLUCZ_ODROCZONYCH)


def _odloz(lead: str, przed: tuple[str, str], autor: str | None) -> bool | None:
	"""HSETNX leada w kolejce odroczonych: True = pierwsze odroczenie tej nocy, False = już
	czeka (ładunek "przed" z pierwszego odroczenia zostaje), None = Redis niedostępny.

	Metody hash wołane bezpośrednio z `redis.Redis`: `RedisWrapper` nadpisuje część z nich
	(pickle, lokalny cache procesu), a ta kolejka trzyma zwykły tekst JSON."""
	cache = frappe.cache()
	klucz = _klucz_odroczonych()
	try:
		nowy = bool(redis.Redis.hsetnx(cache, klucz, lead, zakoduj_odroczenie(przed, autor or "")))
		cache.expire(klucz, TTL_ODROCZONYCH_SEK)
		return nowy
	except redis.exceptions.RedisError:
		return None


def _odczytaj_odroczenie(lead: str):
	"""(stan "przed", autor) z kolejki odroczonych albo None."""
	cache = frappe.cache()
	try:
		surowy = redis.Redis.hget(cache, _klucz_odroczonych(), lead)
	except redis.exceptions.RedisError:
		return None
	return odkoduj_odroczenie(surowy) if surowy is not None else None


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


# --- Hak na leadzie ----------------------------------------------------------------


def _zakolejkuj(ladunek: dict) -> None:
	"""Callback `after_commit`: kolejkuje zadanie; błąd Redis kolejki nie wywraca zapisanego leada."""
	try:
		frappe.enqueue(METODA_ZADANIA, queue="short", **ladunek)
	except Exception:
		# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
		try:
			frappe.log_error(
				title=TYTUL_BLEDU,
				message=f"Lead {ladunek.get('lead')}: nie udało się zakolejkować\n{frappe.get_traceback()}",
			)
		except Exception:
			pass


def zakolejkuj_sms_handlowca(doc) -> None:
	"""Hak z `CRMLead.on_update` (plan 7.1). Nigdy nie rzuca: zapis leada zawsze przechodzi.

	`on_update` biegnie też po insercie (`get_doc_before_save()` = None, stan "przed" pusty).
	Licznik kandydatów siedzi w `frappe.flags`, które żyją przez całe żądanie albo zadanie
	RQ, także ponad commitami w pętli edycji zbiorczej (`_bulk_action`)."""
	try:
		if any(frappe.flags.get(flaga) for flaga in FLAGI_WYJSCIA):
			return
		przed_doc = doc.get_doc_before_save()
		przed = (
			normalizuj_stan(przed_doc.get("lead_owner"), przed_doc.get("custom_termin_spotkania"))
			if przed_doc
			else STAN_PUSTY
		)
		po = normalizuj_stan(doc.get("lead_owner"), doc.get("custom_termin_spotkania"))
		if not czy_kandydat(przed, po):
			return
		# Single czytany dopiero po kroku kandydata: zwykłe zapisy nie płacą za odczyt.
		ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
		if not czy_flaga(ustawienia, POLE_WLACZONE):
			return

		licznik = cint(frappe.flags.get(FLAGA_LICZNIKA)) + 1
		frappe.flags[FLAGA_LICZNIKA] = licznik
		if czy_masowa(licznik):
			pominiete = cint(frappe.flags.get(FLAGA_POMINIETYCH)) + 1
			frappe.flags[FLAGA_POMINIETYCH] = pominiete
			if pominiete == 1:
				frappe.log_error(
					title=f"{TYTUL_BLEDU}: masowa zmiana",
					message=(
						f"Więcej niż {licznik - 1} zmian spotkań w jednym żądaniu albo zadaniu: SMS-y dla"
						f" kolejnych leadów pominięte (pierwszy pominięty: {doc.name})."
					),
				)
			return

		ladunek = {
			"lead": doc.name,
			"przed_wlasciciel": przed[0],
			"przed_termin": przed[1],
			"autor": frappe.session.user,
		}
		frappe.db.after_commit.add(partial(_zakolejkuj, ladunek))
	except Exception:
		# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
		try:
			frappe.log_error(
				title=f"{TYTUL_BLEDU}: hak",
				message=f"Lead {getattr(doc, 'name', '')}: nieoczekiwany wyjątek\n{frappe.get_traceback()}",
			)
		except Exception:
			pass


# --- Zadanie -------------------------------------------------------------------------


def _handlowiec(odbiorca: str):
	"""Wiersz `User` (full_name, mobile_no) aktywnego handlowca albo None (cicho dalej)."""
	if not odbiorca:
		return None
	osoba = frappe.db.get_value("User", odbiorca, ["enabled", "full_name", "mobile_no"], as_dict=True)
	if not osoba or not cint(osoba.enabled):
		return None
	if not frappe.db.exists("Has Role", {"parent": odbiorca, "parenttype": "User", "role": ROLA_D2D}):
		return None
	return osoba


def _slad(lead: str, zdarzenie: Zdarzenie, imie: str, wynik: str, powod: str | None = None) -> None:
	zapisz_slad(lead, opis_sladu(zdarzenie, imie, wynik, powod), doctype="CRM Lead")


def _wynik(zdarzenie: Zdarzenie | None, wynik: str) -> dict:
	if zdarzenie is None:
		return {"typ": "", "odbiorca": "", "wynik": wynik}
	return {"typ": zdarzenie.typ, "odbiorca": zdarzenie.odbiorca, "wynik": wynik}


def _obsluz_zdarzenie(
	*,
	lead: str,
	wiersz: dict,
	zdarzenie: Zdarzenie,
	ustawienia: dict,
	autor: str | None,
	teraz,
	kontekst: dict,
) -> str:
	"""Plan 7.2 krok 5 dla jednego zdarzenia; zwraca stałą wyniku. `kontekst` trzyma token
	(czytany raz na zadanie) i znacznik ostrzeżenia o Redis."""
	osoba = _handlowiec(zdarzenie.odbiorca)
	if osoba is None:
		return WYNIK_NIE_HANDLOWIEC  # lead u CC, admina, konto wyłączone albo usunięte: bez śladu
	imie = osoba.full_name or zdarzenie.odbiorca

	if autor and autor == zdarzenie.odbiorca:
		_slad(lead, zdarzenie, imie, WYNIK_WLASNA_ZMIANA)
		return WYNIK_WLASNA_ZMIANA

	numer = numer_do_smsapi(normalizuj_numer_pl(osoba.mobile_no))
	if not numer:
		# Bez Error Log: sześć kont bez numeru nie może zalać logu; stan widać w panelu.
		_slad(lead, zdarzenie, imie, WYNIK_BRAK_NUMERU)
		return WYNIK_BRAK_NUMERU

	klucz_rez = klucz_rezerwacji(lead, zdarzenie.typ, zdarzenie.odbiorca, zdarzenie.termin)
	rezerwacja = _rezerwuj(klucz_rez)
	if rezerwacja is False:
		return WYNIK_DUPLIKAT  # inne zadanie tego samego leada już obsłużyło to zdarzenie
	if rezerwacja is None:
		_ostrzez_redis(lead, kontekst)

	licznik, klucz_licznika = _licznik_dnia(teraz)
	if licznik is None:
		_ostrzez_redis(lead, kontekst)
	elif licznik > limit_dzienny(ustawienia):
		_cofnij_licznik(klucz_licznika)
		_cofnij_rezerwacje(klucz_rez)
		_slad(lead, zdarzenie, imie, WYNIK_LIMIT)
		if _alert_raz_na_dobe("limit", teraz):
			frappe.log_error(
				title=f"{TYTUL_BLEDU}: limit dzienny",
				message=f"Lead {lead}: dzienny limit SMS do handlowców wyczerpany, kolejne SMS-y dziś pominięte.",
			)
		return WYNIK_LIMIT

	def _blad(powod: str) -> str:
		if licznik is not None:
			_cofnij_licznik(klucz_licznika)
		_cofnij_rezerwacje(klucz_rez)
		_slad(lead, zdarzenie, imie, WYNIK_BLAD)
		frappe.log_error(
			title=TYTUL_BLEDU,
			message=f"Lead {lead}, zdarzenie {zdarzenie.typ}, odbiorca {zdarzenie.odbiorca}: {_bez_numerow(powod)}",
		)
		return WYNIK_BLAD

	tresc, ostrzezenie = zbuduj_tresc_handlowiec(
		szablon_dla(zdarzenie.typ, ustawienia), dane_do_szablonu(wiersz, zdarzenie)
	)
	if not tresc:
		return _blad("pusta treść SMS po wypełnieniu szablonu.")

	if "token" not in kontekst:
		kontekst["token"] = get_decrypted_password(
			DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False
		)
	token = kontekst["token"]
	if not token:
		return _blad("brak tokenu SMSAPI w Volteo SMS Ustawienia.")

	ok, powod, tryb_testowy = wyslij_sms_do_numeru(numer, tresc, ustawienia, token)
	if not ok:
		return _blad(powod)

	if tryb_testowy:
		if licznik is not None:
			_cofnij_licznik(klucz_licznika)  # nic nie wyszło do sieci, limit liczy realne SMS-y
		_slad(lead, zdarzenie, imie, WYNIK_TEST, ostrzezenie)
		return WYNIK_TEST
	_slad(lead, zdarzenie, imie, WYNIK_WYSLANY, ostrzezenie)
	return WYNIK_WYSLANY


def _ostrzez_redis(lead: str, kontekst: dict) -> None:
	if kontekst.get("redis_ostrzezono"):
		return
	kontekst["redis_ostrzezono"] = True
	frappe.log_error(
		title=TYTUL_BLEDU,
		message=f"Lead {lead}: Redis cache niedostępny, deduplikacja i limit dzienny pominięte (fail open).",
	)


def _odloz_na_rano(
	*,
	lead: str,
	przed: tuple[str, str],
	autor: str | None,
	zdarzenia: list[Zdarzenie],
) -> list[dict]:
	"""Cisza nocna: lead do kolejki odroczonych, ślad "odłożony" raz na noc, bez wysyłki i bez stanu."""
	nowy = _odloz(lead, przed, autor)
	if nowy is None:
		# Bez Redis nie ma kolejki: SMS w nocy nie wychodzi (decyzja D4 ma pierwszeństwo przed fail open).
		frappe.log_error(
			title=TYTUL_BLEDU,
			message=f"Lead {lead}: cisza nocna, a Redis cache niedostępny: SMS nie odłożony i nie wysłany.",
		)
		return [_wynik(None, WYNIK_ODLOZONY_BEZ_REDIS)]
	wyniki = []
	for zdarzenie in zdarzenia:
		wyniki.append(_wynik(zdarzenie, WYNIK_ODLOZONY))
		if not nowy or (autor and autor == zdarzenie.odbiorca):
			continue
		osoba = _handlowiec(zdarzenie.odbiorca)
		if osoba is not None:
			_slad(lead, zdarzenie, osoba.full_name or zdarzenie.odbiorca, WYNIK_ODLOZONY)
	return wyniki or [_wynik(None, WYNIK_ODLOZONY)]


def _przetworz(
	lead: str,
	przed_wlasciciel: str | None = None,
	przed_termin: str | None = None,
	autor: str | None = None,
	*,
	teraz=None,
	z_kolejki: bool = False,
) -> list[dict]:
	"""Cała logika zadania (plan 7.2) BEZ commita; zwraca listę wyników `{typ, odbiorca, wynik}`
	(dla sond). `teraz` podmienia chwilę (sonda ciszy nocnej). `z_kolejki=True` woła harmonogram
	odroczonych: bez ponownego odkładania, nawet gdy przetwarzanie zahaczy o początek ciszy.

	Uwaga dla sond: funkcja przełącza sesję na `Administrator` i jej nie przywraca."""
	ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
	if not czy_flaga(ustawienia, POLE_WLACZONE):
		return [_wynik(None, WYNIK_WYLACZONE)]

	frappe.set_user("Administrator")  # autor śladu neutralny, nie CC, który kolejkował zapis

	wiersz = frappe.db.get_value("CRM Lead", lead, ["lead_owner", *POLA_LEADA], as_dict=True)
	if not wiersz:
		_usun_odroczenie(lead)
		return [_wynik(None, WYNIK_BRAK_LEADA)]

	teraz = teraz or now_datetime()
	po = normalizuj_stan(wiersz.get("lead_owner"), wiersz.get("custom_termin_spotkania"))
	przed = normalizuj_stan(przed_wlasciciel, przed_termin)
	odroczenie = _odczytaj_odroczenie(lead)
	if odroczenie is not None:
		przed = odroczenie[0]  # stan "przed" z pierwszego odroczenia tej nocy wygrywa
	baza = _odczytaj_stan(lead) or przed
	zdarzenia = ustal_zdarzenia(
		baza, po, teraz=teraz, odwolania=czy_flaga(ustawienia, POLE_ODWOLANIE_WLACZONE)
	)

	if not z_kolejki and czy_cisza_nocna(teraz):
		return _odloz_na_rano(lead=lead, przed=przed, autor=autor, zdarzenia=zdarzenia)

	wyniki: list[dict] = []
	blad = False
	kontekst: dict = {}
	for zdarzenie in zdarzenia:
		try:
			wynik = _obsluz_zdarzenie(
				lead=lead,
				wiersz=wiersz,
				zdarzenie=zdarzenie,
				ustawienia=ustawienia,
				autor=autor,
				teraz=teraz,
				kontekst=kontekst,
			)
		except Exception:
			wynik = WYNIK_BLAD
			# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
			try:
				frappe.log_error(
					title=TYTUL_BLEDU,
					message=f"Lead {lead}, zdarzenie {zdarzenie.typ}: nieoczekiwany wyjątek\n{frappe.get_traceback()}",
				)
			except Exception:
				pass
		blad = blad or wynik == WYNIK_BLAD
		wyniki.append(_wynik(zdarzenie, wynik))

	if not blad:
		_zapisz_stan(lead, po)
	if odroczenie is not None:
		_usun_odroczenie(lead)  # przetworzony teraz, poranny harmonogram nie powtórzy
	return wyniki


def wyslij_sms_handlowcowi(
	lead: str,
	przed_wlasciciel: str | None = None,
	przed_termin: str | None = None,
	autor: str | None = None,
) -> None:
	"""Zadanie RQ (kolejka "short"): `_przetworz` + commit śladów. Nigdy nie rzuca."""
	try:
		_przetworz(lead, przed_wlasciciel, przed_termin, autor)
		frappe.db.commit()
	except Exception:
		# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
		try:
			frappe.log_error(
				title=TYTUL_BLEDU, message=f"Lead {lead}: nieoczekiwany wyjątek\n{frappe.get_traceback()}"
			)
		except Exception:
			pass


def przetworz_odroczone() -> None:
	"""Harmonogram (cron co 15 minut, `hooks.py`): po ciszy nocnej przetwarza kolejkę odroczonych.

	W ciszy i przy pustej kolejce nic nie robi. Każdy lead przechodzi przez `_przetworz` na
	bieżącym stanie (baza = stan z Redis albo "przed" z pierwszego odroczenia); wpis znika
	z kolejki po przetworzeniu, także po błędzie (Error Log, bez ponawiania w nieskończoność).
	Nigdy nie rzuca."""
	try:
		teraz = now_datetime()
		if czy_cisza_nocna(teraz):
			return
		wpisy = _odroczone()
		for lead, surowy in wpisy.items():
			try:
				odczyt = odkoduj_odroczenie(surowy)
				if odczyt is None:
					frappe.log_error(
						title=TYTUL_BLEDU,
						message=f"Lead {lead}: nieczytelny wpis kolejki odroczonych, pominięty.",
					)
				else:
					(przed_wlasciciel, przed_termin), autor = odczyt
					_przetworz(lead, przed_wlasciciel, przed_termin, autor, teraz=teraz, z_kolejki=True)
			except Exception:
				# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
				try:
					frappe.log_error(
						title=TYTUL_BLEDU,
						message=f"Lead {lead}: odroczony SMS, nieoczekiwany wyjątek\n{frappe.get_traceback()}",
					)
				except Exception:
					pass
			finally:
				_usun_odroczenie(lead)
			frappe.db.commit()
	except Exception:
		# Logowanie samo nie może rzucić: twarda zasada Jana, zapis leada nigdy nie pada przez SMS.
		try:
			frappe.log_error(
				title=TYTUL_BLEDU,
				message=f"Kolejka odroczonych: nieoczekiwany wyjątek\n{frappe.get_traceback()}",
			)
		except Exception:
			pass
