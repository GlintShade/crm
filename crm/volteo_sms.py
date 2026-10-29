# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS powitalny po leadzie z Facebooka (ops#305): logika czysta.

Gdy webhook Make.com zaklada NOWEGO `CRM Lead`, adapter `crm/api/sms_powitalny.py`
wysyla klientowi SMS przez SMSAPI. Ten modul odpowiada za wszystko poza I/O:
transliteracje do GSM-7, liczenie czesci, numer w formacie SMSAPI, parametry
zlecenia, interpretacje odpowiedzi, decyzje czy wysylac i sklejenie wyniku.

Modul celowo nie importuje ``frappe`` ani ``requests`` (precedens
`crm/volteo_geokodowanie.py`): HTTP wchodzi przez wstrzykiwana funkcje
`http_post(url, dane, naglowki) -> (kod_http, slownik | None)`, a dane z bazy
(ustawienia, status leada, inne leady z tym samym numerem) przychodza jako
argumenty. Token SMSAPI jest uzywany wylacznie w naglowku `Authorization`
i NIGDY nie trafia do zadnego zwracanego tekstu, sladu ani logu.
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
"""Seed `tresc_powitalna` (decyzja wlasciciela 2026-10-29: bez polskich znakow, 1 czesc)."""

NADAWCA_DOMYSLNY: str = "ProEnergy"

STATUS_WYSLANY: str = "Wysłany"
STATUS_BLAD: str = "Błąd"
STATUS_POMINIETY: str = "Pominięty"

OKNO_DUBLA_GODZIN: int = 24
"""Ten sam numer nie dostaje drugiego SMS-a powitalnego w ciagu tylu godzin."""

LIMIT_JEDNEJ_CZESCI: int = 160
LIMIT_CZESCI_WIELOKROTNEJ: int = 153
FORMAT_DATY: str = "%Y-%m-%d %H:%M:%S"

_TRANSLITERACJA: dict[str, str] = {
	"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
	"Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
	"\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
	" ": " ",
}  # fmt: skip

_ZNAKI_ROZSZERZENIA_GSM: frozenset[str] = frozenset("^{}\\[]~|")
"""Znaki ASCII, ktore w GSM-7 zajmuja dwa miejsca (tablica rozszerzen)."""


def transliteruj_gsm7(tekst: str) -> str:
	"""Polskie znaki na ASCII, reszta spoza ASCII przez rozklad NFKD albo pominiecie."""
	pol = "".join(_TRANSLITERACJA.get(z, z) for z in tekst or "")
	rozlozony = unicodedata.normalize("NFKD", pol)
	return "".join(z for z in rozlozony if (z.isascii() and (z.isprintable() or z == "\n")))


def dlugosc_gsm7(tekst: str) -> int:
	"""Liczba miejsc w GSM-7: znaki tablicy rozszerzen licza sie podwojnie."""
	return sum(2 if z in _ZNAKI_ROZSZERZENIA_GSM else 1 for z in tekst)


def liczba_czesci_sms(tekst: str) -> int:
	"""Liczba czesci SMS dla tekstu w GSM-7 (160 w jednej, po 153 w wielokrotnym)."""
	dlugosc = dlugosc_gsm7(tekst)
	if dlugosc == 0:
		return 0
	if dlugosc <= LIMIT_JEDNEJ_CZESCI:
		return 1
	return -(-dlugosc // LIMIT_CZESCI_WIELOKROTNEJ)


def przygotuj_tresc(surowa: str) -> tuple[str, str | None]:
	"""(tresc po transliteracji, ostrzezenie lub None gdy tresc jest dluzsza niz 1 czesc)."""
	tresc = transliteruj_gsm7(surowa or "").strip()
	czesci = liczba_czesci_sms(tresc)
	if czesci > 1:
		return tresc, f"Tresc SMS ma {dlugosc_gsm7(tresc)} znakow, wyjdzie {czesci} czesci (limit jednej to 160)."
	return tresc, None


def numer_do_smsapi(mobile_no: str | None) -> str | None:
	"""`+48XXXXXXXXX` na `48XXXXXXXXX`; cokolwiek innego niz 11 cyfr z prefiksem 48 daje None."""
	if not mobile_no:
		return None
	cyfry = re.sub(r"[\s\-.]", "", str(mobile_no))
	if cyfry.startswith("+"):
		cyfry = cyfry[1:]
	if len(cyfry) == 11 and cyfry.isdigit() and cyfry.startswith("48"):
		return cyfry
	return None


def zbuduj_parametry(numer: str, tresc: str, nadawca: str, tryb_testowy: bool) -> dict[str, str]:
	"""Parametry formularza dla `POST /sms.do`; `test=1` tylko w trybie testowym."""
	parametry = {
		"to": numer,
		"message": tresc,
		"from": nadawca,
		"format": "json",
		"encoding": "utf-8",
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
	"""Sukces z id wiadomosci albo blad z kodem i opisem (SMSAPI zwraca oba ksztalty JSON)."""
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
	"""Tekst pola info: opis zdarzenia plus znacznik czasu (z niego liczy sie okno 24 h)."""
	return f"{tresc} [{teraz.strftime(FORMAT_DATY)}]"


_WZORZEC_DATY = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*$")


def data_z_info(info: str | None) -> datetime | None:
	"""Znacznik czasu z konca pola info (`... [RRRR-MM-DD GG:MM:SS]`) albo None."""
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


def zdecyduj_wysylke(
	*,
	wlaczone: bool,
	token_ustawiony: bool,
	numer: str | None,
	status_leada: str | None,
	daty_innych_wyslanych: list[datetime],
	teraz: datetime,
) -> Decyzja:
	"""Czy wysylac. `daty_innych_wyslanych`: daty z info innych leadow z tym samym numerem i statusem Wysłany."""
	if not wlaczone:
		return Decyzja(False, "wyłączone")
	if not token_ustawiony:
		return Decyzja(False, "brak tokenu SMSAPI")
	if not numer:
		return Decyzja(False, "brak lub niepoprawny numer telefonu")
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


HttpPost = Callable[[str, dict[str, str], dict[str, str]], tuple[int | None, Mapping[str, Any] | None]]


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
) -> WynikSms:
	"""Cala decyzja i wysylka bez I/O poza `http_post`; nigdy nie rzuca, token nie wycieka do wyniku."""
	numer = numer_do_smsapi(mobile_no)
	decyzja = zdecyduj_wysylke(
		wlaczone=wlaczone,
		token_ustawiony=bool(token),
		numer=numer,
		status_leada=status_leada,
		daty_innych_wyslanych=daty_innych_wyslanych,
		teraz=teraz,
	)
	if not decyzja.wyslij:
		opis = f"Pominięty ({decyzja.powod})"
		return WynikSms(STATUS_POMINIETY, zbuduj_info(opis, teraz), f"SMS powitalny pominięty: {decyzja.powod}")

	tresc, ostrzezenie = przygotuj_tresc(tresc_surowa)
	if not tresc:
		return WynikSms(
			STATUS_POMINIETY,
			zbuduj_info("Pominięty (pusta treść SMS)", teraz),
			"SMS powitalny pominięty: pusta treść",
		)
	parametry = zbuduj_parametry(numer or "", tresc, nadawca, tryb_testowy)
	naglowki = {"Authorization": f"Bearer {token}"}
	try:
		kod_http, odpowiedz = http_post(SMSAPI_URL, parametry, naglowki)
	except Exception as wyjatek:  # wyjatek HTTP nigdy nie moze ruszyc leada ani wyniesc tokenu
		powod = f"Błąd połączenia z SMSAPI ({type(wyjatek).__name__})."
		return WynikSms(
			STATUS_BLAD, zbuduj_info(powod, teraz), f"SMS powitalny nie wysłany: {powod}", powod, ostrzezenie
		)
	wynik = interpretuj_odpowiedz(kod_http, odpowiedz)
	if not wynik.ok:
		return WynikSms(
			STATUS_BLAD,
			zbuduj_info(wynik.powod, teraz),
			f"SMS powitalny nie wysłany: {wynik.powod}",
			wynik.powod,
			ostrzezenie,
		)
	opis = f"SMSAPI id {wynik.id_wiadomosci}" + (" (tryb testowy)" if tryb_testowy else "")
	return WynikSms(
		STATUS_WYSLANY,
		zbuduj_info(opis, teraz),
		f"SMS powitalny wysłany na +{numer}" + (" (tryb testowy)" if tryb_testowy else ""),
		None,
		ostrzezenie,
	)
