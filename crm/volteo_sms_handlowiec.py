# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do handlowca po umówieniu spotkania (PLAN-SMS-HANDLOWIEC.md): logika czysta.

Handlowiec (rola `Volteo D2D Sales`) dostaje SMS, gdy dla niego powstaje spotkanie
(lead z `lead_owner` = handlowiec i `custom_termin_spotkania` w przyszłości), gdy termin
się zmienia i (osobny przełącznik) gdy spotkanie zostaje odwołane albo przekazane innej
osobie. Adapter `crm/api/sms_handlowiec.py` czyta bazę i Redis, wysyła i zapisuje ślad;
ten moduł odpowiada za wszystko poza I/O: stan (właściciel, termin), decyzję jakie
zdarzenia wynikają ze zmiany stanu, próg masowej zmiany, dane i treść SMS z szablonu,
klucze Redis i tekst śladu w Aktywności.

Moduł celowo nie importuje ``frappe`` (precedens `crm/volteo_sms.py`,
`crm/volteo_dyzury.py`). Przypadki z tabeli 4 planu, które wymagają bazy danych (6:
zmiana przez samego odbiorcę, 8: odbiorca nie jest aktywnym handlowcem, 13: brak
numeru, 14: limit dzienny), rozstrzyga adapter; `ustal_zdarzenia` zwraca zdarzenia
także dla odbiorców, którzy potem okażą się np. kontem CC.

Tożsamość CC nigdy nie trafia do treści: `dane_do_szablonu` czyta wyłącznie klucze
z `POLA_LEADA` (permlevel 0, bez `custom_cc`) i nie ma placeholdera autora zapisu.
Numer telefonu handlowca nie trafia ani do kluczy Redis, ani do śladu. Decyzje Jana
z 2026-11-06 (zastępują plan): bez telefonu klienta i bez linku w treści SMS (placeholdery
`{telefon}` i `{link}` usunięte), limit dzienny 100, cisza nocna 21:00 do 08:00
(`czy_cisza_nocna`, `najblizszy_start_wysylki`; kolejkę odroczonych i harmonogram robi adapter).
"""

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any, NamedTuple

from crm.volteo_dyzury import waliduj_limit_dyzur
from crm.volteo_kalendarz import normalizuj_termin
from crm.volteo_powiadomienia import POLA_LEADA, formatuj_termin, sklej_adres
from crm.volteo_sms import waliduj_szablon, wypelnij_szablon

TYP_NOWE: str = "nowe"
TYP_ZMIANA: str = "zmiana"
TYP_ODWOLANIE: str = "odwolanie"
TYPY: tuple[str, ...] = (TYP_NOWE, TYP_ZMIANA, TYP_ODWOLANIE)
"""Typy zdarzeń; wartość wchodzi do klucza rezerwacji i jest parametrem `typ` SMS testowego w panelu."""

PLACEHOLDERY_HANDLOWIEC: tuple[str, ...] = (
	"termin",
	"stary_termin",
	"data",
	"godzina",
	"klient",
	"adres",
	"miejscowosc",
)
"""Znane placeholdery treści SMS do handlowca (plan 5.1 bez `{telefon}` i `{link}`, decyzja Jana
D1 i D2). Celowo bez autora zapisu, CC, uwag, telefonu klienta i linku."""

DANE_PRZYKLADOWE_HANDLOWIEC: Mapping[str, str] = {
	"termin": "pt. 07.11 14:30",
	"stary_termin": "czw. 06.11 10:00",
	"data": "pt. 07.11",
	"godzina": "14:30",
	"klient": "Jan Kowalski",
	"adres": "Parkowa 5, 64-100 Leszno",
	"miejscowosc": "Leszno",
}
"""Dane do podglądu i SMS testowego w panelu (komplet placeholderów)."""

TRESC_NOWE_DOMYSLNA: str = "Nowe spotkanie {termin}: {klient}, {adres}. Szczegóły w CRM."
TRESC_ZMIANA_DOMYSLNA: str = (
	"Zmiana terminu: {klient}, {adres}, teraz {termin} (było {stary_termin}). Szczegóły w CRM."
)
TRESC_ODWOLANIE_DOMYSLNA: str = (
	"Spotkanie {stary_termin}: {klient}, {miejscowosc}, odwołane albo przekazane innej osobie. Nie jedź."
)
"""Treści domyślne (decyzja Jana 2026-11-06, pkt 7) = wartości siane przez `ops/crm-sms-handlowiec.py`, znak w znak.
Pusty szablon w Single = stała z tego modułu (`szablon_dla`)."""

POLA_SZABLONOW: Mapping[str, str] = {
	TYP_NOWE: "tresc_handlowiec_nowe",
	TYP_ZMIANA: "tresc_handlowiec_zmiana",
	TYP_ODWOLANIE: "tresc_handlowiec_odwolanie",
}
"""Pole Single `Volteo SMS Ustawienia` z szablonem dla typu zdarzenia."""

TRESCI_DOMYSLNE: Mapping[str, str] = {
	TYP_NOWE: TRESC_NOWE_DOMYSLNA,
	TYP_ZMIANA: TRESC_ZMIANA_DOMYSLNA,
	TYP_ODWOLANIE: TRESC_ODWOLANIE_DOMYSLNA,
}

POLE_WLACZONE: str = "handlowiec_wlaczone"
POLE_ODWOLANIE_WLACZONE: str = "handlowiec_odwolanie_wlaczone"
POLE_LIMITU: str = "limit_dzienny_handlowiec"

LIMIT_DZIENNY_DOMYSLNY: int = 100
"""Seed `limit_dzienny_handlowiec` i wartość przy braku pola (decyzja Jana D5: 100)."""

PROG_MASOWY: int = 5
"""Ile kandydatów w jednym żądaniu albo zadaniu idzie normalnie; kolejni są pomijani (decyzja D7)."""

PREFIKS_KLUCZA: str = "volteo:sms_handlowiec:"
TTL_STANU_SEK: int = 14 * 24 * 3600
TTL_REZERWACJI_SEK: int = 3 * 24 * 3600
TTL_LICZNIKA_SEK: int = 2 * 24 * 3600
TTL_ALERTU_SEK: int = 2 * 24 * 3600

KLUCZ_ODROCZONYCH: str = f"{PREFIKS_KLUCZA}odroczone"
"""Kolejka leadów odroczonych przez ciszę nocną (decyzja Jana D4): jeden klucz Redis, pole = nazwa
leada, wartość = `zakoduj_odroczenie` z PIERWSZEGO odroczenia (kolejne zapisy jej nie nadpisują)."""
TTL_ODROCZONYCH_SEK: int = 2 * 24 * 3600

CISZA_OD: str = "21:00"
CISZA_DO: str = "08:00"
"""Cisza nocna (czas serwera, Europe/Warsaw): SMS-y najpóźniej do `CISZA_OD`, odroczone wychodzą
od `CISZA_DO`. Jedyne miejsce w kodzie z tymi godzinami."""

PUSTE_KLIENT: str = "bez nazwy"
PUSTE_ADRES: str = "brak adresu"
PUSTE_INNE: str = "brak"

WYNIK_WYSLANY: str = "wyslany"
WYNIK_TEST: str = "test"
WYNIK_BRAK_NUMERU: str = "brak_numeru"
WYNIK_WLASNA_ZMIANA: str = "wlasna_zmiana"
WYNIK_LIMIT: str = "limit"
WYNIK_BLAD: str = "blad"
WYNIK_ODLOZONY: str = "odlozony"

OPISY_WYNIKU: Mapping[str, str] = {
	WYNIK_WYSLANY: "wysłany",
	WYNIK_TEST: "tryb testowy, SMS nie wyszedł do sieci",
	WYNIK_BRAK_NUMERU: "pominięty, brak numeru telefonu w profilu handlowca",
	WYNIK_WLASNA_ZMIANA: "pominięty, zmiana wprowadzona przez handlowca",
	WYNIK_LIMIT: "pominięty, dzienny limit SMS do handlowców wyczerpany",
	WYNIK_BLAD: "błąd wysyłki, szczegóły w Error Log",
	WYNIK_ODLOZONY: f"odłożony do {CISZA_DO} (cisza nocna)",
}
"""Wyniki śladu w Aktywności (plan 7.4 i decyzja Jana D4)."""

Stan = tuple[str, str]
"""(właściciel, termin `RRRR-MM-DD GG:MM`); pusty string zamiast braku."""

STAN_PUSTY: Stan = ("", "")

_FORMAT_TERMINU = "%Y-%m-%d %H:%M"
_SEPARATOR_STANU = "|"
_CIAG_CYFR = re.compile(r"\+?\d(?:[\s\-.]?\d){4,}")


class Zdarzenie(NamedTuple):
	"""Jedno zdarzenie do jednego odbiorcy.

	`termin`: termin, którego dotyczy zdarzenie (NOWE i ZMIANA: nowy termin; ODWOLANIE:
	odwołany termin), wchodzi do klucza rezerwacji. `stary_termin`: termin bazowy (ZMIANA:
	poprzedni termin; ODWOLANIE: odwołany termin, czyli to samo co `termin`; NOWE: pusty).
	"""

	typ: str
	odbiorca: str
	termin: str
	stary_termin: str


def _tekst(wartosc: Any) -> str:
	"""Wartość pola na przycięty tekst; None daje pusty string."""
	if wartosc is None:
		return ""
	if isinstance(wartosc, bytes):
		wartosc = wartosc.decode("utf-8", "replace")
	return str(wartosc).strip()


def normalizuj_termin_do_minuty(termin: Any) -> str:
	"""Termin (string albo `datetime`) na `RRRR-MM-DD GG:MM`; pusty i nieparsowalny daje pusty string."""
	try:
		pelny = normalizuj_termin(termin)
	except (ValueError, TypeError):
		return ""
	return pelny[:16] if pelny else ""


def normalizuj_stan(wlasciciel: Any, termin: Any) -> Stan:
	"""(właściciel, termin do minuty); None i nieparsowalny termin dają pusty string. Nigdy nie rzuca."""
	return _tekst(wlasciciel), normalizuj_termin_do_minuty(termin)


def _pelny(stan: Stan) -> bool:
	return bool(stan[0] and stan[1])


def czy_kandydat(przed: Stan, po: Stan) -> bool:
	"""Czy zapis leada może dać SMS: para się zmieniła, a przed albo po zapisie jest spotkanie
	(właściciel i termin naraz). Insert = `przed` równe `STAN_PUSTY`. Zmiana samych sekund
	terminu nie jest zmianą."""
	przed_n = normalizuj_stan(*przed)
	po_n = normalizuj_stan(*po)
	if przed_n == po_n:
		return False
	return _pelny(przed_n) or _pelny(po_n)


def _jako_datetime(termin: str) -> datetime | None:
	try:
		return datetime.strptime(termin, _FORMAT_TERMINU)
	except (ValueError, TypeError):
		return None


def czy_w_przyszlosci(termin: str, teraz: datetime) -> bool:
	"""Termin `RRRR-MM-DD GG:MM` później niż `teraz` (spotkanie za 30 minut też się liczy)."""
	moment = _jako_datetime(termin)
	if moment is None:
		return False
	if teraz.tzinfo is not None:
		teraz = teraz.replace(tzinfo=None)
	return moment > teraz


def ustal_zdarzenia(baza: Stan, po: Stan, *, teraz: datetime, odwolania: bool) -> list[Zdarzenie]:
	"""Zdarzenia SMS wynikające ze zmiany stanu `baza` -> `po` (plan, tabela 4, bez przypadków bazodanowych).

	- NOWE do nowego właściciela, gdy po zapisie ma spotkanie w przyszłości, a wcześniej
	  go nie miał (inny właściciel albo brak terminu): przypadki 1 i 2.
	- ZMIANA do tego samego właściciela, gdy termin zmienił się na inny przyszły: przypadek 3.
	- ODWOLANIE (tylko przy `odwolania`) do poprzedniego właściciela, gdy jego przyszłe
	  spotkanie przestało być jego (inny właściciel, brak właściciela, brak terminu):
	  przypadki 2, 4, 5. Termin bazowy z przeszłości nie daje odwołania.
	- Nowy termin w przeszłości nie daje NOWE ani ZMIANA: przypadek 7.
	Kolejność: ODWOLANIE przed NOWE.
	"""
	baza_n = normalizuj_stan(*baza)
	po_n = normalizuj_stan(*po)
	if baza_n == po_n:
		return []
	w_baza, t_baza = baza_n
	w_po, t_po = po_n
	zdarzenia: list[Zdarzenie] = []

	ten_sam = bool(w_po) and w_po == w_baza
	if odwolania and _pelny(baza_n) and not (ten_sam and t_po) and czy_w_przyszlosci(t_baza, teraz):
		zdarzenia.append(Zdarzenie(TYP_ODWOLANIE, w_baza, t_baza, t_baza))

	if _pelny(po_n) and czy_w_przyszlosci(t_po, teraz):
		if ten_sam and t_baza:
			zdarzenia.append(Zdarzenie(TYP_ZMIANA, w_po, t_po, t_baza))
		else:
			zdarzenia.append(Zdarzenie(TYP_NOWE, w_po, t_po, ""))
	return zdarzenia


def czy_masowa(licznik: int, prog: int = PROG_MASOWY) -> bool:
	"""True dla kandydata ponad progiem (licznik po zwiększeniu: pierwsze `prog` idą normalnie)."""
	return licznik > prog


def formatuj_termin_sms(termin: Any) -> str:
	"""`pt. 07.11 14:30` (krótki dzień, data, godzina) albo pusty string."""
	_pelna, godzina, krotko = formatuj_termin(normalizuj_termin_do_minuty(termin) or None)
	return f"{krotko} {godzina}" if krotko else ""


def dane_do_szablonu(lead: Mapping[str, Any], zdarzenie: Zdarzenie) -> dict[str, str]:
	"""Słownik placeholderów dla zdarzenia (plan 5.1), z wartościami zastępczymi dla pustych.

	Czyta wyłącznie klucze z `POLA_LEADA` (inne klucze, np. `custom_cc`, są ignorowane);
	telefon klienta (`mobile_no`) nie trafia do wyniku (decyzja Jana D1).
	"""
	pola = {pole: _tekst(lead.get(pole)) for pole in POLA_LEADA}
	_pelna, godzina, krotko = formatuj_termin(zdarzenie.termin or None)
	return {
		"termin": formatuj_termin_sms(zdarzenie.termin) or PUSTE_INNE,
		"stary_termin": formatuj_termin_sms(zdarzenie.stary_termin) or PUSTE_INNE,
		"data": krotko or PUSTE_INNE,
		"godzina": godzina or PUSTE_INNE,
		"klient": pola["lead_name"] or PUSTE_KLIENT,
		"adres": sklej_adres(pola) or PUSTE_ADRES,
		"miejscowosc": pola["custom_install_city"] or PUSTE_INNE,
	}


def zbuduj_tresc_handlowiec(szablon: str | None, dane: Mapping[str, Any]) -> tuple[str, str | None]:
	"""(treść po transliteracji GSM-7, ostrzeżenie o liczbie części lub None)."""
	return wypelnij_szablon(szablon, dane, PLACEHOLDERY_HANDLOWIEC)


def waliduj_tresc_handlowiec(szablon: Any) -> str | None:
	"""Komunikat błędu po polsku albo None (niepusta treść, wyłącznie znane placeholdery)."""
	return waliduj_szablon(szablon, PLACEHOLDERY_HANDLOWIEC)


def waliduj_limit_handlowiec(limit: Any) -> str | None:
	"""Komunikat błędu albo None; limit 0..1000 (0 blokuje wysyłkę), jak w SMS do dyżurnego."""
	return waliduj_limit_dyzur(limit)


def szablon_dla(typ: str, ustawienia: Mapping[str, Any]) -> str:
	"""Szablon typu z ustawień Single; pusty albo brak = stała domyślna. Nieznany typ: ValueError."""
	if typ not in POLA_SZABLONOW:
		raise ValueError(f"Nieznany typ SMS do handlowca: {typ}.")
	zapisany = ustawienia.get(POLA_SZABLONOW[typ])
	if isinstance(zapisany, str) and zapisany.strip():
		return zapisany
	return TRESCI_DOMYSLNE[typ]


def czy_flaga(ustawienia: Mapping[str, Any], pole: str) -> bool:
	"""Flaga Check z `get_singles_dict` jak `cint`: brak, pusty i nieliczbowy tekst = wyłączone."""
	wartosc = ustawienia.get(pole)
	try:
		return int(float(wartosc)) != 0 if wartosc not in (None, "") else False
	except (TypeError, ValueError):
		return False


def limit_dzienny(ustawienia: Mapping[str, Any]) -> int:
	"""`limit_dzienny_handlowiec`; brak albo nieliczbowa wartość = `LIMIT_DZIENNY_DOMYSLNY`, ujemna = 0."""
	wartosc = ustawienia.get(POLE_LIMITU)
	if wartosc in (None, ""):
		return LIMIT_DZIENNY_DOMYSLNY
	try:
		return max(0, int(float(wartosc)))
	except (TypeError, ValueError):
		return LIMIT_DZIENNY_DOMYSLNY


def _godzina(tekst: str) -> time:
	godzina, minuta = tekst.split(":")
	return time(int(godzina), int(minuta))


def czy_cisza_nocna(teraz: datetime, od: str = CISZA_OD, do: str = CISZA_DO) -> bool:
	"""Czy `teraz` wypada w ciszy nocnej: od `od` włącznie do `do` wyłącznie, także przez północ.

	Domyślnie 21:00 do 08:00: 20:59 wysyła, 21:00 odracza, 07:59 odracza, 08:00 wysyła.
	`od == do` oznacza brak ciszy.
	"""
	poczatek, koniec = _godzina(od), _godzina(do)
	chwila = teraz.time().replace(microsecond=0)
	if poczatek == koniec:
		return False
	if poczatek < koniec:
		return poczatek <= chwila < koniec
	return chwila >= poczatek or chwila < koniec


def najblizszy_start_wysylki(teraz: datetime, od: str = CISZA_OD, do: str = CISZA_DO) -> datetime:
	"""`teraz` poza ciszą nocną, inaczej najbliższy koniec ciszy (`do`, dziś albo jutro)."""
	if not czy_cisza_nocna(teraz, od, do):
		return teraz
	koniec = _godzina(do)
	start = teraz.replace(hour=koniec.hour, minute=koniec.minute, second=0, microsecond=0)
	if start <= teraz:
		start += timedelta(days=1)
	return start


def zakoduj_odroczenie(przed: Stan, autor: str) -> str:
	"""Wartość w `KLUCZ_ODROCZONYCH`: stan "przed" z pierwszego odroczenia i autor zapisu (JSON)."""
	wlasciciel, termin = normalizuj_stan(*przed)
	return json.dumps({"przed_wlasciciel": wlasciciel, "przed_termin": termin, "autor": _tekst(autor)})


def odkoduj_odroczenie(tekst: Any) -> tuple[Stan, str] | None:
	"""(stan "przed", autor) z wartości kolejki odroczonych (str albo bytes); None dla nieczytelnej."""
	try:
		dane = json.loads(_tekst(tekst))
	except (ValueError, TypeError):
		return None
	if not isinstance(dane, dict):
		return None
	return normalizuj_stan(dane.get("przed_wlasciciel"), dane.get("przed_termin")), _tekst(dane.get("autor"))


def _dzien(dzien: date) -> str:
	return dzien.strftime("%Y-%m-%d")


def klucz_stanu(lead: str) -> str:
	"""Klucz Redis ostatniego przetworzonego stanu leada (prefiks site dokłada adapter przez `make_key`)."""
	return f"{PREFIKS_KLUCZA}stan:{lead}"


def klucz_rezerwacji(lead: str, typ: str, odbiorca: str, termin: str) -> str:
	"""Klucz SET NX jednego zdarzenia: (lead, typ, odbiorca = login użytkownika, termin). Bez numeru telefonu."""
	return f"{PREFIKS_KLUCZA}wyslane:{lead}:{typ}:{odbiorca}:{termin}"


def klucz_licznika_dnia(dzien: date) -> str:
	"""Klucz dziennego licznika wysłanych SMS do handlowców (`date` albo `datetime`)."""
	return f"{PREFIKS_KLUCZA}{_dzien(dzien)}"


def klucz_alertu(rodzaj: str, dzien: date) -> str:
	"""Klucz SET NX "jeden Error Log na dobę" dla rodzaju alertu (np. `limit`, `masowa`)."""
	return f"{PREFIKS_KLUCZA}alert:{rodzaj}:{_dzien(dzien)}"


def zakoduj_stan(stan: Stan) -> str:
	"""`właściciel|termin` do zapisu w Redis."""
	wlasciciel, termin = normalizuj_stan(*stan)
	return f"{wlasciciel}{_SEPARATOR_STANU}{termin}"


def odkoduj_stan(tekst: Any) -> Stan | None:
	"""Stan z wartości Redis (str albo bytes); None dla braku albo nieczytelnej wartości."""
	surowy = _tekst(tekst)
	if not surowy or _SEPARATOR_STANU not in surowy:
		return None
	wlasciciel, _sep, termin = surowy.rpartition(_SEPARATOR_STANU)
	if termin and not normalizuj_termin_do_minuty(termin):
		return None
	return normalizuj_stan(wlasciciel, termin)


def _opis_zdarzenia(zdarzenie: Zdarzenie) -> str:
	termin = formatuj_termin_sms(zdarzenie.termin) or PUSTE_INNE
	if zdarzenie.typ == TYP_NOWE:
		return f"nowe spotkanie {termin}"
	if zdarzenie.typ == TYP_ZMIANA:
		return f"zmiana terminu na {termin}"
	if zdarzenie.typ == TYP_ODWOLANIE:
		return f"odwołanie spotkania {formatuj_termin_sms(zdarzenie.stary_termin or zdarzenie.termin) or PUSTE_INNE}"
	return zdarzenie.typ


def opis_sladu(zdarzenie: Zdarzenie, odbiorca_nazwa: str | None, wynik: str, powod: str | None = None) -> str:
	"""`SMS do handlowca <imię> (<opis zdarzenia>): <wynik>.` (plan 7.4).

	`wynik` to jedna ze stałych `WYNIK_*` (inny tekst przechodzi bez zmian). `powod` jest
	opcjonalnym dopiskiem (np. ostrzeżenie o 2 częściach); ciągi cyfr wyglądające na numer
	telefonu są z niego wycinane. Ślad nigdy nie zawiera treści SMS, numeru ani autora zapisu.
	"""
	osoba = _tekst(odbiorca_nazwa) or zdarzenie.odbiorca
	tekst = f"SMS do handlowca {osoba} ({_opis_zdarzenia(zdarzenie)}): {OPISY_WYNIKU.get(wynik, wynik)}"
	dopisek = _CIAG_CYFR.sub("***", _tekst(powod)).rstrip(".").strip()
	if dopisek:
		tekst = f"{tekst}; {dopisek}"
	return f"{tekst}."
