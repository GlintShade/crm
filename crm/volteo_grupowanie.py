# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta logika grupowania list (ops#413): Umowy (`CRM Deal`), Leady (`CRM Lead`)
i Zadania (`CRM Task`).

Modul celowo nie importuje ``frappe``. Warstwe frappe-owa (liczniki jednym
`frappe.get_list` z `group_by`, filtr wierszy grupy w `get_data`, uprawnienia
pol przez `_pola_dozwolone`) niesie `crm.api.doc`.

Klucz grupy to znormalizowana wartosc pola: pusty string oznacza "brak
wartosci" (NULL i "" to jedna grupa), dla pol dat `RRRR-MM-DD` (dzien) albo
`RRRR-MM` (miesiac). Funkcje sa immutable: zwracaja nowe struktury.
"""

import calendar
import re

from crm.volteo_pipeline import PIPELINE_CP, PIPELINE_OZE, TERMINALE

LIMIT_LEADOW = 2000
"""Powyzej tylu leadow w wyniku listy (po filtrach) serwer odmawia grupowania."""

DOCTYPE_LEADA = "CRM Lead"
DOCTYPE_SZANSY = "CRM Deal"
DOCTYPE_ZADANIA = "CRM Task"

RODZAJE = ("status", "select", "user", "data", "dzien", "miesiac")
"""status = kropka koloru statusu, user = awatar, dzien/miesiac = podzial dat."""

ETYKIETA_BRAK = "Brak wartości"

# (nazwa pola, etykieta, rodzaj). Kolejnosc = kolejnosc w menu "Grupuj".
POLA: dict[str, tuple[tuple[str, str, str], ...]] = {
	DOCTYPE_SZANSY: (
		("status", "Etap procesu", "status"),
		("custom_rodzaj_umowy", "Rodzaj umowy", "select"),
		("deal_owner", "Doradca", "user"),
		("custom_financing_interest", "Finansowanie", "select"),
		("custom_voivodeship", "Województwo", "data"),
		("custom_zasady_dotacji", "Zasady dotacji", "select"),
		("custom_status_osd", "Status OSD", "select"),
		("custom_status_dotacja", "Status dotacji", "select"),
		("creation", "Miesiąc utworzenia", "miesiac"),
	),
	DOCTYPE_LEADA: (
		("lead_owner", "Przypisany handlowiec", "user"),
		("custom_cc", "Przypisany CC", "user"),
		("status", "Status CC", "status"),
		("custom_status_handlowy", "Status handlowy", "select"),
		("custom_status_zrodla", "Status źródła", "select"),
		("custom_kampania_fb", "Kampania FB", "data"),
		("custom_zasady_dotacji", "Zasady rozliczeń", "select"),
		("custom_voivodeship", "Województwo", "data"),
		("custom_powiat", "Powiat", "data"),
		("custom_termin_spotkania", "Termin spotkania po dniu", "dzien"),
		("custom_kolejny_kontakt", "Kolejny kontakt po dniu", "dzien"),
		("custom_source_channel", "Źródło pozyskania", "select"),
		("custom_import_source", "Źródła importu", "data"),
		("custom_posiadane_produkty", "Obecne produkty", "data"),
		("custom_proby_kontaktu", "Próby kontaktu", "select"),
	),
	DOCTYPE_ZADANIA: (
		("assigned_to", "Osoba odpowiedzialna", "user"),
		("status", "Status", "status"),
		("priority", "Priorytet", "select"),
		("due_date", "Termin wykonania po dniu", "dzien"),
		("start_date", "Data rozpoczęcia", "dzien"),
		("owner", "Autor", "user"),
	),
}
"""Krotka lista pol per doctype (decyzja wlasciciela 2026-11-23). Pole z permlevel > 0
trafia do menu tylko, gdy `crm.api.doc._pola_dozwolone` je zwraca (to samo sito
co filtry): nie trzymamy tu poziomow uprawnien, zeby nie rozjechac sie z Frappe.
Klient (pseudokolumna `_klient` zadan) swiadomie pominiety, patrz raport ops#413."""

ETYKIETY_PUSTYCH: dict[tuple[str, str], str] = {
	(DOCTYPE_LEADA, "lead_owner"): "Bez handlowca",
	(DOCTYPE_LEADA, "custom_cc"): "Bez CC",
	(DOCTYPE_SZANSY, "deal_owner"): "Bez doradcy",
	(DOCTYPE_ZADANIA, "assigned_to"): "Bez osoby odpowiedzialnej",
}

_RE_DZIEN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_MIESIAC = re.compile(r"^\d{4}-\d{2}$")


def lista_pol(doctype: str) -> list[dict]:
	"""Pola dostepne do grupowania na danym doctype (bez sprawdzania uprawnien)."""
	return [{"fieldname": n, "label": e, "kind": r} for n, e, r in POLA.get(doctype, ())]


def pole(doctype: str, nazwa: str | None) -> dict | None:
	"""Opis pola z allowlisty albo None. Jedyne zrodlo prawdy "czy wolno grupowac"."""
	for opis in lista_pol(doctype):
		if opis["fieldname"] == nazwa:
			return opis
	return None


def etykieta_pustej(doctype: str, nazwa: str) -> str:
	return ETYKIETY_PUSTYCH.get((doctype, nazwa), ETYKIETA_BRAK)


def czy_ponad_limit(doctype: str, razem: int) -> bool:
	"""Prog 2000 dotyczy wylacznie leadow (Umowy i Zadania bez progu)."""
	return doctype == DOCTYPE_LEADA and razem > LIMIT_LEADOW


def klucz_wartosci(rodzaj: str, wartosc: object) -> str:
	"""Klucz grupy dla surowej wartosci z bazy. None i "" daja "" (grupa pusta)."""
	if wartosc is None or wartosc == "":
		return ""
	tekst = str(wartosc)
	if rodzaj == "dzien":
		return tekst[:10]
	if rodzaj == "miesiac":
		return tekst[:7]
	return tekst


def zlicz(rodzaj: str, wiersze: list[dict]) -> dict[str, int]:
	"""Scala wiersze `{wartosc, n}` z `group_by` w liczniki per klucz (dla pol dat
	baza grupuje po pelnym znaczniku czasu, tu sklejamy je w dni lub miesiace)."""
	wynik: dict[str, int] = {}
	for w in wiersze:
		k = klucz_wartosci(rodzaj, w.get("wartosc"))
		wynik[k] = wynik.get(k, 0) + int(w.get("n") or 0)
	return wynik


def kolejnosc_etapow() -> tuple[str, ...]:
	"""Etapy procesu: najpierw OZE, potem etapy tylko CP, na koncu "Przegrana"."""
	kolejnosc: list[str] = []
	for etap in (*PIPELINE_OZE, *PIPELINE_CP):
		if etap not in kolejnosc:
			kolejnosc.append(etap)
	return tuple(kolejnosc)


def _klucz_sortowania(doctype: str, nazwa: str, rodzaj: str, opcje: list[str] | None):
	"""Zwraca funkcje (klucz, etykieta) -> klucz sortowania dla niepustych grup."""
	if rodzaj == "status" and doctype == DOCTYPE_SZANSY:
		etapy = kolejnosc_etapow()
		koniec = {t for lista in TERMINALE.values() for t in lista}

		def po_etapie(k: str, e: str):
			if k in etapy:
				return (0, etapy.index(k), "")
			return (2 if k in koniec else 1, 0, e.casefold())

		return po_etapie
	if opcje:

		def po_opcji(k: str, e: str):
			return (0, opcje.index(k), "") if k in opcje else (1, 0, e.casefold())

		return po_opcji
	if rodzaj in ("dzien", "miesiac"):
		return lambda k, e: (0, 0, k)
	return lambda k, e: (0, 0, e.casefold())


def uloz_grupy(
	doctype: str,
	nazwa: str,
	liczniki: dict[str, int],
	opcje: list[str] | None = None,
	pokaz_puste: bool = False,
	etykiety: dict[str, str] | None = None,
) -> list[dict]:
	"""Gotowa lista grup `{klucz, etykieta, licznik, pusta}` w kolejnosci wyswietlania.

	Grupy z licznikiem 0 sa ukryte, chyba ze `pokaz_puste` (wtedy dochodza opcje pola
	Select/status z `opcje`). Grupa pustej wartosci (klucz "") jest zawsze ostatnia i
	tylko gdy ma rekordy. `etykiety` (np. imiona uzytkownikow) nadpisuja klucz jako nazwe.
	"""
	opis = pole(doctype, nazwa)
	if opis is None:
		raise ValueError(f"Pole {nazwa} nie jest dozwolone do grupowania na {doctype}")
	rodzaj = opis["kind"]
	etykiety = etykiety or {}
	klucze = {k: n for k, n in liczniki.items() if k != "" and n > 0}
	if pokaz_puste:
		for o in opcje or []:
			if o:
				klucze.setdefault(o, 0)

	def etykieta(k: str) -> str:
		return etykiety.get(k) or k

	sortuj = _klucz_sortowania(doctype, nazwa, rodzaj, opcje)
	grupy = [
		{"klucz": k, "etykieta": etykieta(k), "licznik": n, "pusta": False}
		for k, n in sorted(klucze.items(), key=lambda p: sortuj(p[0], etykieta(p[0])))
	]
	if liczniki.get("", 0) > 0:
		grupy.append(
			{"klucz": "", "etykieta": etykieta_pustej(doctype, nazwa), "licznik": liczniki[""], "pusta": True}
		)
	return grupy


def filtr_grupy(doctype: str, nazwa: str, klucz: str) -> list:
	"""Warunek `[pole, operator, wartosc]` zawezajacy liste do jednej grupy.

	Pusty klucz to "is not set", dzien/miesiac to `between` (serwer rozszerza zakres
	pol Datetime do konca dnia), reszta to rownosc. ValueError dla pola spoza
	allowlisty albo zlego formatu klucza (adapter zamienia to na blad uzytkownika).
	"""
	opis = pole(doctype, nazwa)
	if opis is None:
		raise ValueError(f"Pole {nazwa} nie jest dozwolone do grupowania na {doctype}")
	if not isinstance(klucz, str):
		raise ValueError("Klucz grupy musi byc tekstem")
	if klucz == "":
		return [nazwa, "is", "not set"]
	rodzaj = opis["kind"]
	if rodzaj == "dzien":
		if not _RE_DZIEN.match(klucz):
			raise ValueError(f"Zly klucz dnia: {klucz}")
		return [nazwa, "between", [klucz, klucz]]
	if rodzaj == "miesiac":
		if not _RE_MIESIAC.match(klucz):
			raise ValueError(f"Zly klucz miesiaca: {klucz}")
		rok, mies = int(klucz[:4]), int(klucz[5:7])
		if not 1 <= mies <= 12:
			raise ValueError(f"Zly klucz miesiaca: {klucz}")
		ostatni = calendar.monthrange(rok, mies)[1]
		return [nazwa, "between", [f"{klucz}-01", f"{klucz}-{ostatni:02d}"]]
	return [nazwa, "=", klucz]
