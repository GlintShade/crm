# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do dyżurnego backoffice po leadzie z Facebooka (ops#313): logika czysta.

Grafik tygodniowy co do godziny (wiersze `Volteo Dyzur SMS`: dzień tygodnia, od, do,
użytkownik, aktywny) mówi, kto w danej chwili ma dyżur. Adapter `crm/api/sms_dyzur.py`
czyta grafik i numery z bazy, a ten moduł odpowiada za wszystko poza I/O: wybór
dyżurnych w chwili, walidację wiersza, sklejenie treści, klucz dziennego licznika
i decyzję o wysyłce razem z tekstem śladu w Aktywności.

Moduł celowo nie importuje ``frappe`` (precedens `crm/volteo_sms.py`). Transliteracja,
numer w formacie SMSAPI i parametry zlecenia pochodzą z `crm/volteo_sms.py`.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from crm.volteo_sms import przygotuj_tresc

DNI_TYGODNIA: tuple[str, ...] = (
	"Poniedziałek",
	"Wtorek",
	"Środa",
	"Czwartek",
	"Piątek",
	"Sobota",
	"Niedziela",
)
"""Literały Select `dzien_tygodnia`; indeks = `datetime.weekday()`."""

TRESC_DYZUR_DOMYSLNA: str = "Nowy lead FB: {klient}, tel. {telefon}, {kod}. {link}"
"""Seed `tresc_dyzur`."""

LIMIT_DZIENNY_DYZUR_DOMYSLNY: int = 100
"""Seed `limit_dzienny_dyzur`: maks. realnie wysłanych SMS dyżurowych na dobę serwera."""

PLACEHOLDERY_DYZUR: tuple[str, ...] = ("klient", "telefon", "kod", "miejscowosc", "link")
"""Znane placeholdery treści SMS dyżurowego."""

DANE_PRZYKLADOWE_DYZUR: Mapping[str, str] = {
	"klient": "Jan Testowy",
	"telefon": "500 100 200",
	"kod": "00-001",
	"miejscowosc": "Warszawa",
}
"""Dane do podglądu i SMS testowego; `link` dokłada adapter (zależy od URL site)."""

LIMIT_DYZUR_MAX: int = 1000

PREFIKS_KLUCZA_LICZNIKA: str = "volteo:sms_dyzur:"
TTL_LICZNIKA_SEK: int = 2 * 24 * 3600

_WZORZEC_DATY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_BRAK = object()
_FALSZ = (None, "", 0, "0", False)

_WZORZEC_CZASU = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def normalizuj_numer_pl(surowy: str | None) -> str | None:
	"""Polski numer komórkowy na `+48XXXXXXXXX`; None dla pustego i niepoprawnego wejścia.

	Przyjmuje `+48...`, `48...`, `0048...` i gołe 9 cyfr (spacje, kropki, myślniki
	są ignorowane). 9 cyfr zaczynających się od 0 jest odrzucane.
	"""
	if not surowy or not str(surowy).strip():
		return None
	cyfry = re.sub(r"[\s\-.]", "", str(surowy))
	if cyfry.startswith("+"):
		cyfry = cyfry[1:]
		if not cyfry.startswith("48"):
			return None
	elif cyfry.startswith("0048"):
		cyfry = cyfry[2:]
	if not cyfry.isdigit() or not cyfry.isascii():
		return None
	if len(cyfry) == 11 and cyfry.startswith("48"):
		cyfry = cyfry[2:]
	if len(cyfry) != 9 or cyfry.startswith("0"):
		return None
	return "+48" + cyfry


def dzien_tygodnia(chwila: datetime) -> str:
	"""Polska nazwa dnia tygodnia dla chwili."""
	return DNI_TYGODNIA[chwila.weekday()]


def parsuj_czas(wartosc: Any) -> time | None:
	"""`time`, `timedelta` (tak Frappe zwraca pole Time) albo "HH:MM[:SS]" na `time`; inaczej None."""
	if isinstance(wartosc, datetime):
		return wartosc.time().replace(microsecond=0)
	if isinstance(wartosc, time):
		return wartosc.replace(microsecond=0)
	if isinstance(wartosc, timedelta):
		sekundy = int(wartosc.total_seconds())
		if sekundy < 0 or sekundy >= 24 * 3600:
			return None
		return time(sekundy // 3600, (sekundy % 3600) // 60, sekundy % 60)
	if isinstance(wartosc, str):
		trafienie = _WZORZEC_CZASU.match(wartosc.strip())
		if not trafienie:
			return None
		g, m, s = int(trafienie.group(1)), int(trafienie.group(2)), int(trafienie.group(3) or 0)
		if g > 23 or m > 59 or s > 59:
			return None
		return time(g, m, s)
	return None


def parsuj_date(wartosc: Any) -> date | None:
	"""`date`, `datetime` albo "RRRR-MM-DD" na `date`; inaczej None."""
	if isinstance(wartosc, datetime):
		return wartosc.date()
	if isinstance(wartosc, date):
		return wartosc
	if isinstance(wartosc, str):
		trafienie = _WZORZEC_DATY.match(wartosc.strip())
		if not trafienie:
			return None
		try:
			return date(int(trafienie.group(1)), int(trafienie.group(2)), int(trafienie.group(3)))
		except ValueError:
			return None
	return None


def opis_daty(d: Any) -> str:
	"""`11.11.2026` do śladu i komunikatów."""
	parsed = parsuj_date(d)
	return parsed.strftime("%d.%m.%Y") if parsed else ""


def dzien_z_daty(d: Any) -> str | None:
	"""Polska nazwa dnia tygodnia dla daty (wyliczana dla wyjątków)."""
	parsed = parsuj_date(d)
	return DNI_TYGODNIA[parsed.weekday()] if parsed else None


def _aktywny(wiersz: Mapping[str, Any]) -> bool:
	return wiersz.get("aktywny", 1) not in _FALSZ


def _wyjatki_dnia(grafik: list[Mapping[str, Any]], dzien: date) -> list[Mapping[str, Any]]:
	"""Aktywne wiersze-wyjątki z datą równą `dzien`."""
	return [w for w in grafik or [] if _aktywny(w) and parsuj_date(w.get("data")) == dzien]


def czy_wyjatek_dnia(grafik: list[Mapping[str, Any]], chwila: datetime) -> bool:
	"""Czy na dzień chwili istnieje aktywny wyjątek (wtedy grafik tygodniowy nie obowiązuje)."""
	return bool(_wyjatki_dnia(grafik, chwila.date()))


def dyzurni_w_chwili(grafik: list[Mapping[str, Any]], chwila: datetime) -> list[str]:
	"""Unikalni użytkownicy aktywnych wierszy pasujących do chwili (`od` włącznie, `do` wyłącznie).

	Gdy na dzień chwili istnieje aktywny wyjątek (wiersz z `data`), grafik tygodniowy tego dnia
	jest ignorowany w całości: dyżurnych wyznaczają wyłącznie wyjątki tej daty z
	`bez_dyzuru == 0`. Wyjątek `bez_dyzuru` sam nikogo nie dodaje, ale wyłącza grafik tygodniowy.
	Kolejność stabilna wg (od, użytkownik). Wiersz z błędnym czasem jest pomijany.
	"""
	wyjatki = _wyjatki_dnia(grafik, chwila.date())
	if wyjatki:
		kandydaci = [w for w in wyjatki if w.get("bez_dyzuru") in _FALSZ]
	else:
		dzien = dzien_tygodnia(chwila)
		kandydaci = [
			w for w in grafik or [] if _aktywny(w) and not w.get("data") and w.get("dzien_tygodnia") == dzien
		]
	teraz = chwila.time().replace(microsecond=0)
	trafione: list[tuple[time, str]] = []
	for wiersz in kandydaci:
		uzytkownik = wiersz.get("uzytkownik")
		od, do = parsuj_czas(wiersz.get("od")), parsuj_czas(wiersz.get("do"))
		if not uzytkownik or od is None or do is None:
			continue
		if od <= teraz < do:
			trafione.append((od, str(uzytkownik)))
	widziani: set[str] = set()
	wynik: list[str] = []
	for _od, uzytkownik in sorted(trafione):
		if uzytkownik not in widziani:
			widziani.add(uzytkownik)
			wynik.append(uzytkownik)
	return wynik


def waliduj_wiersz(
	dzien: Any,
	od: Any,
	do: Any,
	*,
	data: Any = None,
	bez_dyzuru: Any = False,
	uzytkownik: Any = _BRAK,
) -> str | None:
	"""Komunikat błędu po polsku albo None, gdy wiersz jest poprawny.

	Wołane 3-argumentowo waliduje wiersz tygodniowy jak dawniej. `uzytkownik` jest sprawdzany
	tylko gdy został podany. Wyjątek (`data`) ma dzień wyliczany z daty, więc `dzien` pomija.
	"""
	jest_data = data not in _FALSZ
	if bez_dyzuru not in _FALSZ and not jest_data:
		return "Opcja 'nikt nie ma dyżuru' dotyczy tylko wyjątku z datą."
	if jest_data and parsuj_date(data) is None:
		return "Data wyjątku musi mieć format RRRR-MM-DD."
	if bez_dyzuru not in _FALSZ:
		return None
	if not jest_data and dzien not in DNI_TYGODNIA:
		return "Dzień tygodnia musi być jednym z: " + ", ".join(DNI_TYGODNIA) + "."
	t_od, t_do = parsuj_czas(od), parsuj_czas(do)
	if t_od is None or t_do is None:
		return "Godziny dyżuru muszą mieć format GG:MM."
	if t_od >= t_do:
		return "Godzina początku dyżuru musi być wcześniejsza niż godzina końca."
	if uzytkownik is not _BRAK and not uzytkownik:
		return "Wybierz użytkownika."
	return None


class _SlownikBezBrakow(dict):
	def __missing__(self, klucz: str) -> str:
		return ""


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def zbuduj_tresc_dyzur(szablon: str, dane: Mapping[str, Any]) -> tuple[str, str | None]:
	"""Podstawia placeholdery, potem transliteracja GSM-7 (`przygotuj_tresc`).

	Brakujący klucz w `dane` daje pusty string, nieznany placeholder zostaje bez zmian.
	Zwraca (treść, ostrzeżenie o liczbie części lub None).
	"""
	znane = set(PLACEHOLDERY_DYZUR)

	def _podstaw(trafienie: re.Match) -> str:
		klucz = trafienie.group(1)
		if klucz not in znane:
			return trafienie.group(0)
		wartosc = dane.get(klucz)
		return "" if wartosc is None else str(wartosc)

	surowa = _PLACEHOLDER.sub(_podstaw, szablon or "")
	surowa = re.sub(r"[ \t]+", " ", surowa)
	surowa = re.sub(r"\s+([,.;:])", r"\1", surowa)
	surowa = re.sub(r"([,;:])\s*(?=[.])", "", surowa)
	return przygotuj_tresc(surowa)


def waliduj_tresc_dyzur(szablon: Any) -> str | None:
	"""Komunikat błędu po polsku albo None, gdy treść szablonu jest poprawna."""
	if not isinstance(szablon, str) or not szablon.strip():
		return "Treść SMS nie może być pusta."
	for nazwa in _PLACEHOLDER.findall(szablon):
		if nazwa not in PLACEHOLDERY_DYZUR:
			dozwolone = ", ".join("{" + p + "}" for p in PLACEHOLDERY_DYZUR)
			return f"Nieznany placeholder {{{nazwa}}}. Dozwolone: {dozwolone}."
	return None


def waliduj_limit_dyzur(limit: Any) -> str | None:
	"""Komunikat błędu albo None; limit 0..1000 (0 blokuje wysyłkę)."""
	try:
		wartosc = int(limit)
	except (TypeError, ValueError):
		wartosc = -1
	if not 0 <= wartosc <= LIMIT_DYZUR_MAX:
		return f"Limit dzienny musi być liczbą od 0 do {LIMIT_DYZUR_MAX} (0 blokuje wysyłkę)."
	return None


def klucz_licznika_dnia(chwila: datetime) -> str:
	"""Klucz Redis dziennego licznika wysłanych SMS dyżurowych (prefiks site dokłada adapter)."""
	return f"{PREFIKS_KLUCZA_LICZNIKA}{chwila.strftime('%Y-%m-%d')}"


def opis_chwili(chwila: datetime) -> str:
	"""`sobota 14:05` do śladu o braku dyżuru."""
	return f"{dzien_tygodnia(chwila).lower()} {chwila.strftime('%H:%M')}"


@dataclass(frozen=True)
class DecyzjaDyzur:
	wyslij: bool
	slad: str = ""
	zapisz_slad: bool = True
	limit_wyczerpany: bool = False


def zdecyduj_wysylke_dyzur(
	*,
	wlaczone: bool,
	token_ustawiony: bool,
	chwila: datetime,
	dyzurni: list[str],
	imie_dyzurnego: str | None = None,
	numer: str | None = None,
	limit_dzienny: int = LIMIT_DZIENNY_DYZUR_DOMYSLNY,
	wyslane_dzis: int = 0,
	wyjatek_dnia: bool = False,
) -> DecyzjaDyzur:
	"""Czysta decyzja dla jednego dyżurnego (albo dla całej chwili, gdy `dyzurni` jest puste).

	Kolejność: wyłączone (bez śladu), brak dyżuru, brak tokenu, brak numeru, limit, wysyłaj.
	Tekst śladu nie zawiera numeru telefonu ani tokenu.
	"""
	if not wlaczone:
		return DecyzjaDyzur(False, zapisz_slad=False)
	if not dyzurni:
		if wyjatek_dnia:
			return DecyzjaDyzur(
				False,
				f"SMS dyżurowy: brak dyżuru ({opis_chwili(chwila)}, "
				f"wyjątek od grafiku na {opis_daty(chwila)})",
			)
		return DecyzjaDyzur(False, f"SMS dyżurowy: brak dyżuru ({opis_chwili(chwila)})")
	osoba = imie_dyzurnego or (dyzurni[0] if dyzurni else "")
	if not token_ustawiony:
		return DecyzjaDyzur(False, f"SMS dyżurowy pominięty: brak tokenu SMSAPI ({osoba})")
	if not numer:
		return DecyzjaDyzur(False, f"SMS dyżurowy pominięty: {osoba} bez numeru telefonu")
	if wyslane_dzis >= limit_dzienny:
		return DecyzjaDyzur(
			False,
			f"SMS dyżurowy pominięty: wyczerpany limit dzienny {limit_dzienny} SMS",
			limit_wyczerpany=True,
		)
	return DecyzjaDyzur(True)
