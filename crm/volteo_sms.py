# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS powitalny po leadzie z Facebooka (ops#305): logika czysta.

Gdy webhook Make.com zakłada NOWEGO `CRM Lead`, adapter `crm/api/sms_powitalny.py`
wysyła klientowi SMS przez SMSAPI. Ten moduł odpowiada za wszystko poza I/O:
transliterację do GSM-7, liczenie części, numer w formacie SMSAPI, parametry
zlecenia, interpretację odpowiedzi, decyzję czy wysyłać i sklejenie wyniku.

Moduł celowo nie importuje ``frappe`` ani ``requests`` (precedens
`crm/volteo_geokodowanie.py`): HTTP wchodzi przez wstrzykiwaną funkcję
`http_post(url, dane, naglowki) -> (kod_http, slownik | None)`, rezerwacja numeru
(Redis) przez `rezerwuj`/`zwolnij`, a dane z bazy (ustawienia, status leada, inne
leady z tym samym numerem, licznik dzienny) przychodzą jako argumenty. Token SMSAPI
jest używany wyłącznie w nagłówku `Authorization` i NIGDY nie trafia do żadnego
zwracanego tekstu, śladu ani logu.
"""

import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

SMSAPI_URL: str = "https://api.smsapi.pl/sms.do"

TRESC_DOMYSLNA: str = (
	"Dzien dobry, dziekujemy za kontakt. Nasz doradca wkrotce sie z Panstwem "
	"skontaktuje. Pozdrawiamy, ProEnergy"
)
"""Seed `tresc_powitalna` (decyzja właściciela 2026-10-29: bez polskich znaków, 1 część). Literał bez ogonków celowo."""

NADAWCA_DOMYSLNY: str = "ProEnergy"

STATUS_WYSLANY: str = "Wysłany"
STATUS_BLAD: str = "Błąd"
STATUS_POMINIETY: str = "Pominięty"
STATUS_TEST: str = "Test"

OKNO_DUBLA_GODZIN: int = 24
"""Ten sam numer nie dostaje drugiego SMS-a powitalnego w ciągu tylu godzin."""

TTL_REZERWACJI_SEK: int = OKNO_DUBLA_GODZIN * 3600
LIMIT_DZIENNY_DOMYSLNY: int = 50
"""Seed `limit_dzienny`: maksymalna liczba realnie wysłanych SMS na dobę serwera."""

LIMIT_JEDNEJ_CZESCI: int = 160
LIMIT_CZESCI_WIELOKROTNEJ: int = 153
FORMAT_DATY: str = "%Y-%m-%d %H:%M:%S"

_TRANSLITERACJA: dict[str, str] = {
	"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
	"Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
	"\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'", "`": "'", "\u201c": '"', "\u201d": '"',
	" ": " ",
}  # fmt: skip

_ZNAKI_ROZSZERZENIA_GSM: frozenset[str] = frozenset("^{}\\[]~|")
"""Znaki ASCII, które w GSM-7 zajmują dwa miejsca (tablica rozszerzeń)."""


def transliteruj_gsm7(tekst: str) -> str:
	"""Polskie znaki na ASCII, reszta spoza ASCII przez rozkład NFKD albo pominięcie."""
	pol = "".join(_TRANSLITERACJA.get(z, z) for z in tekst or "")
	rozlozony = unicodedata.normalize("NFKD", pol)
	return "".join(z for z in rozlozony if (z.isascii() and (z.isprintable() or z == "\n")))


def dlugosc_gsm7(tekst: str) -> int:
	"""Liczba miejsc w GSM-7: znaki tablicy rozszerzeń liczą się podwójnie."""
	return sum(2 if z in _ZNAKI_ROZSZERZENIA_GSM else 1 for z in tekst)


def liczba_czesci_sms(tekst: str) -> int:
	"""Liczba części SMS dla tekstu w GSM-7 (160 w jednej, po 153 w wielokrotnym)."""
	dlugosc = dlugosc_gsm7(tekst)
	if dlugosc == 0:
		return 0
	if dlugosc <= LIMIT_JEDNEJ_CZESCI:
		return 1
	return -(-dlugosc // LIMIT_CZESCI_WIELOKROTNEJ)


def przygotuj_tresc(surowa: str) -> tuple[str, str | None]:
	"""(treść po transliteracji, ostrzeżenie lub None gdy treść jest dłuższa niż 1 część)."""
	tresc = transliteruj_gsm7(surowa or "").strip()
	czesci = liczba_czesci_sms(tresc)
	if czesci > 1:
		return tresc, f"Treść SMS ma {dlugosc_gsm7(tresc)} znaków, wyjdzie {czesci} części (limit jednej to 160)."
	return tresc, None


def numer_do_smsapi(mobile_no: str | None) -> str | None:
	"""`+48XXXXXXXXX` na `48XXXXXXXXX`; cokolwiek innego niż 11 cyfr z prefiksem 48 daje None."""
	if not mobile_no:
		return None
	cyfry = re.sub(r"[\s\-.]", "", str(mobile_no))
	if cyfry.startswith("+"):
		cyfry = cyfry[1:]
	if len(cyfry) == 11 and cyfry.isdigit() and cyfry.startswith("48"):
		return cyfry
	return None


def zbuduj_parametry(numer: str, tresc: str, nadawca: str, tryb_testowy: bool) -> dict[str, str]:
	"""Parametry formularza dla `POST /sms.do`; `test=1` tylko w trybie testowym.

	`nounicode=1` (dokumentacja SMSAPI, sms.do): SMSAPI odrzuca wiadomość ze znakami
	specjalnymi (w tym polskimi) błędem 11, zamiast po cichu wysłać ją jako Unicode
	(70 znaków na część, wyższy koszt). To pas bezpieczeństwa na wypadek, gdyby
	transliteracja kiedyś coś przepuściła.
	"""
	parametry = {
		"to": numer,
		"message": tresc,
		"from": nadawca,
		"format": "json",
		"encoding": "utf-8",
		"nounicode": "1",
	}
	if tryb_testowy:
		parametry["test"] = "1"
	return parametry


@dataclass(frozen=True)
class OdpowiedzSmsapi:
	ok: bool
	id_wiadomosci: str | None = None
	kod: str | None = None
	powod: str = ""


def interpretuj_odpowiedz(kod_http: int | None, odpowiedz: Mapping[str, Any] | None) -> OdpowiedzSmsapi:
	"""Sukces z id wiadomości albo błąd z kodem i opisem (SMSAPI zwraca oba kształty JSON)."""
	if not isinstance(odpowiedz, Mapping):
		return OdpowiedzSmsapi(False, powod=f"Nieczytelna odpowiedz SMSAPI (HTTP {kod_http}).")
	if "error" in odpowiedz:
		kod = str(odpowiedz.get("error"))
		opis = str(odpowiedz.get("message") or "").strip()
		return OdpowiedzSmsapi(False, kod=kod, powod=f"SMSAPI odrzucilo zlecenie, kod {kod}: {opis or 'brak opisu'}.")
	lista = odpowiedz.get("list")
	if isinstance(lista, list) and lista and isinstance(lista[0], Mapping) and lista[0].get("id"):
		return OdpowiedzSmsapi(True, id_wiadomosci=str(lista[0]["id"]))
	if odpowiedz.get("message") and (kod_http or 0) >= 400:
		return OdpowiedzSmsapi(False, powod=f"SMSAPI odrzucilo zlecenie (HTTP {kod_http}): {odpowiedz['message']}.")
	return OdpowiedzSmsapi(False, powod=f"Nieoczekiwana odpowiedz SMSAPI (HTTP {kod_http}).")


def zbuduj_info(tresc: str, teraz: datetime) -> str:
	"""Tekst pola info: opis zdarzenia plus znacznik czasu (z niego liczy się okno 24 h)."""
	return f"{tresc} [{teraz.strftime(FORMAT_DATY)}]"


def wzor_info_dnia(teraz: datetime) -> str:
	"""Wzorzec SQL `LIKE` na znacznik czasu z danej doby (do licznika dziennego)."""
	return f"%[{teraz.strftime('%Y-%m-%d')} %]"


_WZORZEC_DATY = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*$")


def data_z_info(info: str | None) -> datetime | None:
	"""Znacznik czasu z końca pola info (`... [RRRR-MM-DD GG:MM:SS]`) albo None."""
	trafienie = _WZORZEC_DATY.search(info or "")
	if not trafienie:
		return None
	try:
		return datetime.strptime(trafienie.group(1), FORMAT_DATY)
	except ValueError:
		return None


@dataclass(frozen=True)
class Decyzja:
	wyslij: bool
	powod: str = ""
	zapisz: bool = True
	limit_wyczerpany: bool = False


def zdecyduj_wysylke(
	*,
	wlaczone: bool,
	token_ustawiony: bool,
	numer: str | None,
	status_leada: str | None,
	daty_innych_wyslanych: list[datetime],
	teraz: datetime,
	limit_dzienny: int = LIMIT_DZIENNY_DOMYSLNY,
	wyslane_dzis: int = 0,
) -> Decyzja:
	"""Czy wysyłać. `daty_innych_wyslanych`: daty z info innych leadów z tym samym numerem i statusem Wysłany."""
	if not wlaczone:
		return Decyzja(False, "wyłączone", zapisz=False)
	if not token_ustawiony:
		return Decyzja(False, "brak tokenu SMSAPI")
	if not numer:
		return Decyzja(False, "brak lub niepoprawny numer telefonu")
	if wyslane_dzis >= limit_dzienny:
		return Decyzja(False, f"wyczerpany limit dzienny {limit_dzienny} SMS", limit_wyczerpany=True)
	if status_leada == STATUS_WYSLANY:
		return Decyzja(False, "SMS już wysłany do tego leada")
	granica = teraz - timedelta(hours=OKNO_DUBLA_GODZIN)
	if any(d >= granica for d in daty_innych_wyslanych):
		return Decyzja(False, f"ten numer dostał SMS w ciągu ostatnich {OKNO_DUBLA_GODZIN} godzin")
	return Decyzja(True)


@dataclass(frozen=True)
class WynikSms:
	status: str
	info: str
	slad: str
	blad_do_logu: str | None = None
	ostrzezenie: str | None = None
	zapisz: bool = True
	limit_wyczerpany: bool = False
	redis_niedostepny: bool = False


HttpPost = Callable[[str, dict[str, str], dict[str, str]], tuple[int | None, Mapping[str, Any] | None]]

Rezerwuj = Callable[[str], bool | None]
"""True = zarezerwowano, False = numer już zarezerwowany, None = Redis niedostępny (fail open)."""
Zwolnij = Callable[[str], None]


def klucz_rezerwacji_numeru(numer: str) -> str:
	"""Klucz Redis rezerwacji numeru (prefiks site dokłada adapter przez `make_key`)."""
	return f"volteo:sms_powitalny:numer:{numer}"


def przetworz(
	*,
	wlaczone: bool,
	token: str | None,
	nadawca: str,
	tresc_surowa: str,
	tryb_testowy: bool,
	mobile_no: str | None,
	status_leada: str | None,
	daty_innych_wyslanych: list[datetime],
	teraz: datetime,
	http_post: HttpPost,
	rezerwuj: Rezerwuj,
	zwolnij: Zwolnij,
	limit_dzienny: int = LIMIT_DZIENNY_DOMYSLNY,
	wyslane_dzis: int = 0,
) -> WynikSms:
	"""Cała decyzja i wysyłka bez I/O poza wstrzykniętymi funkcjami; nigdy nie rzuca, token nie wycieka do wyniku."""
	numer = numer_do_smsapi(mobile_no)
	decyzja = zdecyduj_wysylke(
		wlaczone=wlaczone,
		token_ustawiony=bool(token),
		numer=numer,
		status_leada=status_leada,
		daty_innych_wyslanych=daty_innych_wyslanych,
		teraz=teraz,
		limit_dzienny=limit_dzienny,
		wyslane_dzis=wyslane_dzis,
	)
	if not decyzja.wyslij:
		if not decyzja.zapisz:
			return WynikSms("", "", "", zapisz=False)
		opis = f"Pominięty ({decyzja.powod})"
		return WynikSms(
			STATUS_POMINIETY,
			zbuduj_info(opis, teraz),
			f"SMS powitalny pominięty: {decyzja.powod}",
			limit_wyczerpany=decyzja.limit_wyczerpany,
		)

	tresc, ostrzezenie = przygotuj_tresc(tresc_surowa)
	if not tresc:
		return WynikSms(
			STATUS_POMINIETY,
			zbuduj_info("Pominięty (pusta treść SMS)", teraz),
			"SMS powitalny pominięty: pusta treść",
		)

	stan = rezerwuj(numer or "")
	if stan is False:
		return WynikSms(
			STATUS_POMINIETY,
			zbuduj_info("Pominięty (ten numer ma już rezerwację SMS z ostatnich 24 godzin)", teraz),
			"SMS powitalny pominięty: numer zarezerwowany w ostatnich 24 godzinach",
		)
	redis_niedostepny = stan is None
	zarezerwowano = stan is True

	def _opis(opis: str) -> str:
		return f"{opis}; {ostrzezenie}" if ostrzezenie else opis

	parametry = zbuduj_parametry(numer or "", tresc, nadawca, tryb_testowy)
	naglowki = {"Authorization": f"Bearer {token}"}
	try:
		kod_http, odpowiedz = http_post(SMSAPI_URL, parametry, naglowki)
	except Exception as wyjatek:  # wyjątek HTTP nigdy nie może ruszyć leada ani wynieść tokenu
		if zarezerwowano:
			zwolnij(numer or "")
		powod = f"Błąd połączenia z SMSAPI ({type(wyjatek).__name__})."
		return WynikSms(
			STATUS_BLAD,
			zbuduj_info(_opis(powod), teraz),
			f"SMS powitalny nie wysłany: {powod}",
			powod,
			ostrzezenie,
			redis_niedostepny=redis_niedostepny,
		)
	wynik = interpretuj_odpowiedz(kod_http, odpowiedz)
	if not wynik.ok:
		if zarezerwowano:
			zwolnij(numer or "")
		return WynikSms(
			STATUS_BLAD,
			zbuduj_info(_opis(wynik.powod), teraz),
			f"SMS powitalny nie wysłany: {wynik.powod}",
			wynik.powod,
			ostrzezenie,
			redis_niedostepny=redis_niedostepny,
		)
	if tryb_testowy:
		if zarezerwowano:
			zwolnij(numer or "")
		return WynikSms(
			STATUS_TEST,
			zbuduj_info(_opis(f"SMSAPI test OK, id {wynik.id_wiadomosci}"), teraz),
			f"SMS powitalny: test SMSAPI OK (nic nie wysłano) na +{numer}",
			None,
			ostrzezenie,
			redis_niedostepny=redis_niedostepny,
		)
	return WynikSms(
		STATUS_WYSLANY,
		zbuduj_info(_opis(f"SMSAPI id {wynik.id_wiadomosci}"), teraz),
		f"SMS powitalny wysłany na +{numer}",
		None,
		ostrzezenie,
		redis_niedostepny=redis_niedostepny,
	)
