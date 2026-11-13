# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Alert "lead bez zmian przez X godzin" (ops#352): logika czysta.

Powiadomienie w CRM (dzwonek), gdy lead z webhooka Make nie ma zadnej zmiany
zrobionej przez czlowieka przez X godzin od utworzenia. Ten modul odpowiada za
wszystko poza I/O: stale reguly, okno czasu, normalizacje ustawien, filtr
autorow technicznych, decyzje o alercie, odbiorcow i tresc powiadomienia.

Modul celowo nie importuje ``frappe`` (precedens `crm/volteo_reguly_przydzialu.py`).
Tozsamosc osoby CC (`custom_cc`) nie wchodzi do zadnej funkcji tego modulu, wiec
nigdy nie trafi do tresci powiadomienia.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta
from html import escape
from typing import Any

from crm.volteo_leady_webhook import ROLA_INTEGRACJI

KLUCZ_REGULY: str = "lead_bez_zmian"
"""Klucz wiersza `Volteo Automatyzacja` (typ "Powiadomienie")."""

ZAKRES_WSZYSTKIE: str = "Wszystkie leady z Facebooka"
ZAKRES_Z_HANDLOWCEM: str = "Leady z przypisanym handlowcem"
ZAKRES_Z_REGULY: str = "Leady z reguły bezpośredniej"
ZAKRESY: tuple[str, ...] = (ZAKRES_WSZYSTKIE, ZAKRES_Z_HANDLOWCEM, ZAKRES_Z_REGULY)
"""Dozwolone wartosci `zakres_leadow`; te same literaly sa opcjami Select w skrypcie ops
i wartosciami listy wyboru w panelu Automatyzacje."""

PROG_DOMYSLNY_GODZIN: int = 48
PROG_MIN_GODZIN: int = 1
PROG_MAX_GODZIN: int = 720

SZEROKOSC_OKNA_GODZIN: int = 24
"""Alert tylko, gdy wiek leada jest w oknie od X do X + 24 h (ochrona przed fala alertow)."""

LIMIT_LEADOW_NA_PRZEBIEG: int = 50

AUTORZY_TECHNICZNI: frozenset[str] = frozenset({"Administrator", "Guest"})
"""Autorzy, ktorych zmiany nie sa aktywnoscia czlowieka. Dochodza konta z rola `ROLA_INTEGRACJI`."""

TYPY_AKTYWNOSCI: tuple[str, ...] = ("Version", "Comment", "FCRM Note", "CRM Task", "CRM Call Log")
"""Dokumenty niosace aktywnosc czlowieka na leadzie (opis w raporcie i w adapterze)."""

__all__ = ["ROLA_INTEGRACJI"]


def normalizuj_prog(wartosc: Any) -> int:
	"""Prog w godzinach: nieparsowalny albo pusty daje domyslny, reszta jest przycinana do 1..720."""
	try:
		liczba = int(float(wartosc))
	except (TypeError, ValueError):
		return PROG_DOMYSLNY_GODZIN
	if liczba <= 0 and not wartosc:
		return PROG_DOMYSLNY_GODZIN
	return max(PROG_MIN_GODZIN, min(PROG_MAX_GODZIN, liczba))


def czy_prog_poprawny(wartosc: Any) -> bool:
	"""Walidacja zapisu z panelu: liczba calkowita w 1..720 (bez przycinania)."""
	if isinstance(wartosc, bool):
		return False
	try:
		liczba = int(wartosc)
	except (TypeError, ValueError):
		return False
	return PROG_MIN_GODZIN <= liczba <= PROG_MAX_GODZIN


def normalizuj_zakres(wartosc: Any) -> str:
	"""Pusta albo nieznana wartosc znaczy "Wszystkie leady z Facebooka"."""
	tekst = (wartosc or "").strip() if isinstance(wartosc, str) else ""
	return tekst if tekst in ZAKRESY else ZAKRES_WSZYSTKIE


def czy_zakres_poprawny(wartosc: Any) -> bool:
	return isinstance(wartosc, str) and wartosc in ZAKRESY


def okno_utworzenia(teraz: datetime, prog_godzin: int) -> tuple[datetime, datetime]:
	"""Zakres `creation` leadow, ktore maja wiek w oknie [X, X + 24 h]: (od, do), oba wlacznie."""
	prog = timedelta(hours=normalizuj_prog(prog_godzin))
	return teraz - prog - timedelta(hours=SZEROKOSC_OKNA_GODZIN), teraz - prog


def czy_w_oknie(creation: datetime | None, teraz: datetime, prog_godzin: int) -> bool:
	if creation is None:
		return False
	od, do = okno_utworzenia(teraz, prog_godzin)
	return od <= creation <= do


def czy_autor_czlowiek(autor: str | None, konta_integracji: Iterable[str] = ()) -> bool:
	"""Autor technicznym jest `Administrator`, `Guest` i konto z rola integracji; pusty autor tez."""
	if not autor:
		return False
	if autor in AUTORZY_TECHNICZNI:
		return False
	return autor not in set(konta_integracji)


def leady_z_aktywnoscia_czlowieka(
	wiersze: Iterable[tuple[str | None, str | None]],
	konta_integracji: Iterable[str] = (),
) -> set[str]:
	"""Z par (nazwa leada, autor) zbiera nazwy leadow, na ktorych jest aktywnosc czlowieka."""
	integracji = set(konta_integracji)
	return {lead for lead, autor in wiersze if lead and czy_autor_czlowiek(autor, integracji)}


def czy_lead_w_zakresie(
	zakres: Any,
	lead_owner: str | None,
	przydzial_bezposredni: Any,
	pole_przydzialu_istnieje: bool = True,
) -> bool:
	"""Zakres reguly zawęża leady z webhooka. Brak pola przydzialu w bazie: zero leadow dla zakresu reguly."""
	wybrany = normalizuj_zakres(zakres)
	if wybrany == ZAKRES_Z_HANDLOWCEM:
		return bool(lead_owner)
	if wybrany == ZAKRES_Z_REGULY:
		if not pole_przydzialu_istnieje:
			return False
		try:
			return int(przydzial_bezposredni or 0) == 1
		except (TypeError, ValueError):
			return False
	return True


def czy_wyslac_alert(
	w_oknie: bool,
	z_webhooka: bool,
	w_zakresie: bool,
	ma_aktywnosc_czlowieka: bool,
	znacznik: Any,
) -> bool:
	"""Lead kwalifikuje sie do alertu: w oknie wieku, z webhooka, w zakresie, bez zmian czlowieka,
	bez wczesniejszego znacznika. Odbiorcow sprawdza wolajacy (bez nich nie ma znacznika)."""
	if not (w_oknie and z_webhooka and w_zakresie):
		return False
	if ma_aktywnosc_czlowieka:
		return False
	return not znacznik


def zbierz_odbiorcow(
	z_tabeli: Iterable[str | None],
	wlasciciel_leada: str | None,
	odbiorca_handlowiec: Any,
	aktywni: Iterable[str],
) -> list[str]:
	"""Odbiorcy jednego leada: tabela reguly plus (gdy wlaczone) wlasciciel leada, tylko konta wlaczone,
	posortowani. Nikogo sie nie odejmuje (zadanie dziala jako Administrator)."""
	zbior = {u for u in z_tabeli if u}
	if odbiorca_handlowiec and wlasciciel_leada:
		zbior.add(wlasciciel_leada)
	dozwoleni = set(aktywni)
	return sorted(u for u in zbior if u in dozwoleni)


def ogranicz_przebieg(kandydaci: list[Any], limit: int = LIMIT_LEADOW_NA_PRZEBIEG) -> tuple[list[Any], int]:
	"""Hamulec: najwyzej `limit` leadow na przebieg, zwraca (do przetworzenia, liczba pominietych)."""
	if limit < 0:
		limit = 0
	return kandydaci[:limit], max(0, len(kandydaci) - limit)


def tresc_powiadomienia(prog_godzin: int, klient: str | None, kod: str | None, handlowiec: str | None) -> str:
	"""Tresc dzwonka. Wejscie jest zabezpieczone przed HTML (tresc idzie do `v-html` po sanityzacji).
	Brak handlowca: "Bez handlowca, pula CC." (bez wskazywania osoby CC)."""
	godziny = normalizuj_prog(prog_godzin)
	osoba = escape((klient or "").strip() or "bez nazwy")
	kod_czysty = escape((kod or "").strip())
	opis = f"{osoba}, {kod_czysty}" if kod_czysty else osoba
	koniec = (
		f"Handlowiec: {escape(handlowiec.strip())}."
		if (handlowiec or "").strip()
		else "Bez handlowca, pula CC."
	)
	return f"Lead bez zmian od {godziny} h: {opis}. {koniec}"
