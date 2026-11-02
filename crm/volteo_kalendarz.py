# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kalendarz spotkan handlowcow (ops#318): czysta logika bez `frappe`.

Spotkanie to `CRM Lead` z `custom_termin_spotkania` (Datetime) i `lead_owner`
(handlowiec). Modul celowo nie importuje ``frappe``: zakres uprawnien, daty,
walidacja zakresu i grupowanie da sie wtedy przetestowac lokalnie. Odczyt
bazy i `throw` mieszkaja w adapterze `crm/api/kalendarz.py`.
"""

import json
from datetime import date, datetime, timedelta

ZAKRES_WSZYSCY = "wszyscy"
ZAKRES_WLASNY = "wlasny"

ROLE_WSZYSCY: frozenset[str] = frozenset(
	{"System Manager", "Volteo Core Admin", "Volteo Backend", "Volteo Call Center"}
)
"""Role widzace tablice wszystkich handlowcow."""

ROLA_HANDLOWCA: str = "Volteo D2D Sales"
"""Rola handlowca: bez ról uprzywilejowanych widzi tylko wlasny kalendarz."""

MAKS_DNI_ZAKRESU: int = 62


def zakres_kalendarza(user: str, roles) -> str | None:
	""" "wszyscy" | "wlasny" | None (brak dostepu) dla `user` z rolami `roles`."""
	if user == "Administrator":
		return ZAKRES_WSZYSCY
	zbior = set(roles or ())
	if zbior & ROLE_WSZYSCY:
		return ZAKRES_WSZYSCY
	if ROLA_HANDLOWCA in zbior:
		return ZAKRES_WLASNY
	return None


def _parsuj_date(tekst) -> date:
	"""`YYYY-MM-DD` (rowniez z doklejona godzina) na `date`; ValueError przy bledzie."""
	if isinstance(tekst, datetime):
		return tekst.date()
	if isinstance(tekst, date):
		return tekst
	if not isinstance(tekst, str) or len(tekst.strip()) < 10:
		raise ValueError("Niepoprawna data (oczekiwano RRRR-MM-DD).")
	try:
		return date.fromisoformat(tekst.strip()[:10])
	except ValueError as exc:
		raise ValueError("Niepoprawna data (oczekiwano RRRR-MM-DD).") from exc


def zakres_tygodnia(data_iso: str) -> tuple[str, str]:
	"""(poniedzialek, niedziela) tygodnia zawierajacego `data_iso`, RRRR-MM-DD."""
	d = _parsuj_date(data_iso)
	poniedzialek = d - timedelta(days=d.weekday())
	niedziela = poniedzialek + timedelta(days=6)
	return poniedzialek.isoformat(), niedziela.isoformat()


def zakres_dnia(data_iso: str) -> tuple[str, str]:
	"""(dzien, dzien) dla widoku dnia."""
	d = _parsuj_date(data_iso).isoformat()
	return d, d


def waliduj_zakres_dat(od: str, do: str, max_dni: int = MAKS_DNI_ZAKRESU) -> None:
	"""ValueError przy zlym formacie, `od` > `do` albo zakresie ponad `max_dni` dni."""
	d_od = _parsuj_date(od)
	d_do = _parsuj_date(do)
	if d_od > d_do:
		raise ValueError("Data początkowa jest późniejsza niż końcowa.")
	if (d_do - d_od).days + 1 > max_dni:
		raise ValueError(f"Zakres dat jest zbyt duży (maksymalnie {max_dni} dni).")


def granice_czasu(od: str, do: str) -> tuple[str, str]:
	"""Granice Datetime dla filtra `between`: `od 00:00:00` i `do 23:59:59`."""
	return f"{_parsuj_date(od).isoformat()} 00:00:00", f"{_parsuj_date(do).isoformat()} 23:59:59"


def normalizuj_termin(termin) -> str | None:
	"""Termin z formularza na `RRRR-MM-DD GG:MM:SS`; pusty => None (czyszczenie).

	Przyjmuje separator spacje albo `T`, sekundy opcjonalne. ValueError przy
	niepoprawnym formacie.
	"""
	if termin is None:
		return None
	if isinstance(termin, datetime):
		return termin.strftime("%Y-%m-%d %H:%M:%S")
	if not isinstance(termin, str):
		raise ValueError("Niepoprawny termin spotkania.")
	tekst = termin.strip()
	if not tekst:
		return None
	tekst = tekst.replace("T", " ")
	for wzor in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
		try:
			return datetime.strptime(tekst, wzor).strftime("%Y-%m-%d %H:%M:%S")
		except ValueError:
			continue
	raise ValueError("Niepoprawny termin spotkania (oczekiwano RRRR-MM-DD GG:MM).")


def normalizuj_handlowcow(handlowcy) -> list[str]:
	"""Lista maili z JSON-a (string), listy albo pojedynczego stringa; bez duplikatow."""
	if handlowcy is None or handlowcy == "":
		return []
	if isinstance(handlowcy, str):
		tekst = handlowcy.strip()
		if not tekst:
			return []
		try:
			handlowcy = json.loads(tekst)
		except ValueError:
			handlowcy = [tekst]
	if isinstance(handlowcy, str):
		handlowcy = [handlowcy]
	if not isinstance(handlowcy, (list, tuple)):
		return []
	wynik: list[str] = []
	for h in handlowcy:
		if isinstance(h, str) and h.strip() and h.strip() not in wynik:
			wynik.append(h.strip())
	return wynik


def przetnij_handlowcow(zadani: list[str], dostepni: list[str]) -> list[str]:
	"""Czesc wspolna `zadani` i `dostepni`, w kolejnosci `dostepni`.

	Pusta lista `zadani` oznacza wszystkich dostepnych; nieznane maile sa pomijane.
	"""
	if not zadani:
		return list(dostepni)
	zbior = set(zadani)
	return [u for u in dostepni if u in zbior]


def _klucz_handlowca(h) -> str | None:
	if isinstance(h, str):
		return h
	if isinstance(h, dict):
		return h.get("user") or h.get("name")
	return None


def _klucz_terminu(wiersz) -> str:
	return str(wiersz.get("custom_termin_spotkania") or "")


def pogrupuj_spotkania(wiersze, handlowcy) -> dict:
	"""handlowiec -> lista wierszy posortowana po terminie.

	Kazdy handlowiec z `handlowcy` (maile albo slowniki z `user`) dostaje klucz,
	takze bez spotkan; kolejnosc zachowana. Wiersze bez terminu lub z wlascicielem
	spoza listy sa pomijane.
	"""
	wynik: dict[str, list] = {}
	for h in handlowcy or []:
		klucz = _klucz_handlowca(h)
		if klucz:
			wynik[klucz] = []
	for w in wiersze or []:
		if not w.get("custom_termin_spotkania"):
			continue
		wlasciciel = w.get("lead_owner")
		if wlasciciel in wynik:
			wynik[wlasciciel].append(w)
	for lista in wynik.values():
		lista.sort(key=_klucz_terminu)
	return wynik
