# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Powiadomienia dla AUTORA zadania `CRM Task` o zmianach dokonanych przez kogos
innego (ops#360). Czysta logika, bez `import frappe`: wybor zdarzen z porownania
stanu przed i po, wybor odbiorcy i tekst. Warstwe frappe-owa (odczyt znacznika,
wstawienie `CRM Notification`) niesie adapter w `crm/fcrm/doctype/crm_task/crm_task.py`
i `crm/api/zadania_rozmowa.py`.

Decyzje wlasciciela 2026-11-16: powiadomienia dotycza WYLACZNIE zadan zalozonych
recznie (zadania automatyczne z `dispatch_task` nigdy nie powiadamiaja swojego
"autora"), jeden dzwonek na zdarzenie, bez maila i SMS, nigdy dla osoby
dokonujacej zmiany, wzmianka we wpisie wygrywa z powiadomieniem autora.
"""

import re
from html import escape

ZNACZNIK_ZADANIA_AUTOMATYCZNEGO = "[volteo:zadanie-auto]"
"""Tresc wiersza `Comment` typu `Info` na zadaniu automatycznym."""

PREFIKSY_TYTULU_AUDYTU: tuple[str, ...] = ("Audyt OZE: ", "Audyt CP: ")
"""Tytuly zadan audytu sprzed wdrozenia znacznika (uznawane za automatyczne)."""

ZDARZENIA: tuple[str, ...] = ("wpis", "status", "termin", "wykonawca", "dw")
"""`dw` (ops#411): osoba dodana do "Do wiadomosci"; dostaje ja tylko nowo dodana."""

_MENTION_RE = re.compile(r"<span[^>]*data-type=[\"']mention[\"'][^>]*>", re.IGNORECASE)
_DATA_ID_RE = re.compile(r"data-id=[\"']([^\"']*)[\"']", re.IGNORECASE)

_ETYKIETY_STATUSU: dict[str, str] = {
	"Todo": "Do zrobienia",
	"In Progress": "W toku",
	"Done": "Wykonane",
	"Canceled": "Anulowane",
}


def czy_zadanie_automatyczne(ma_znacznik: bool, tytul: str | None, reference_doctype: str | None) -> bool:
	"""Zadanie automatyczne: ma znacznik albo (zadanie audytu sprzed znacznika)
	tytul zaczyna sie od "Audyt OZE: " / "Audyt CP: " i wisi na szansie."""
	if ma_znacznik:
		return True
	return reference_doctype == "CRM Deal" and (tytul or "").startswith(PREFIKSY_TYTULU_AUDYTU)


def _norm(wartosc: object) -> str:
	"""Termin porownywany do minuty, reszta jako tekst; None i "" rowne sobie."""
	if wartosc is None:
		return ""
	return str(wartosc).strip()[:16]


def wykryj_zdarzenia(przed: dict, po: dict) -> list[str]:
	"""Zdarzenia zmiany pol zadania (`status`, `termin`, `wykonawca`) z
	porownania slownikow `{status, due_date, assigned_to}` przed i po zapisie.
	Wpis rozmowy (`wpis`) nie jest zmiana pola, zglasza go `dodaj`."""
	zdarzenia: list[str] = []
	if (przed.get("status") or "") != (po.get("status") or ""):
		zdarzenia.append("status")
	if _norm(przed.get("due_date")) != _norm(po.get("due_date")):
		zdarzenia.append("termin")
	if (przed.get("assigned_to") or "") != (po.get("assigned_to") or ""):
		zdarzenia.append("wykonawca")
	return zdarzenia


def wybierz_odbiorce(
	autor: str | None,
	aktor: str | None,
	autor_aktywny: bool,
	automatyczne: bool,
) -> str | None:
	"""Autor zadania, jesli ma dostac dzwonek, w przeciwnym razie None.

	Nikt nie dostaje powiadomienia o wlasnej zmianie, konto wylaczone, brak autora
	i zadanie automatyczne nie dostaja nic."""
	if automatyczne or not autor or autor in ("Guest",) or not autor_aktywny:
		return None
	if autor == aktor:
		return None
	return autor


def wybierz_odbiorcow(
	autor: str | None,
	wykonawcy: list[str | None],
	aktor: str | None,
	aktywni: set[str] | frozenset[str],
	automatyczne: bool,
	pomin: set[str] | None = None,
	do_wiadomosci: list[str | None] | None = None,
) -> list[str]:
	"""Odbiorcy dzwonka o zdarzeniu na zadaniu (ops#360): autor (tylko zadanie
	reczne) oraz wykonawcy (pole `assigned_to` i osoby z otwartym ToDo; takze przy
	zadaniu automatycznym). Kazdy raz (bez duplikatow, kolejnosc: autor, wykonawcy),
	nigdy aktor, tylko konta z `aktywni`, nikt z `pomin` (np. nowy wykonawca przy
	zmianie wykonawcy, ktory dostaje juz dzwonek przypisania). Trzecia grupa
	(ops#411): osoby "Do wiadomosci" (`do_wiadomosci`), traktowane jak wykonawcy,
	takze przy zadaniu automatycznym."""
	pomin = pomin or set()
	kandydaci: list[str | None] = [None if automatyczne else autor, *wykonawcy, *(do_wiadomosci or [])]
	wynik: list[str] = []
	for kandydat in kandydaci:
		if (
			not kandydat
			or kandydat in ("Guest",)
			or kandydat == aktor
			or kandydat in pomin
			or kandydat not in aktywni
			or kandydat in wynik
		):
			continue
		wynik.append(kandydat)
	return wynik


def wyczysc_do_wiadomosci(osoby: list[str | None] | None, wykonawca: str | None) -> list[str]:
	"""Lista "Do wiadomosci" po zapisie (ops#411): bez pustych wpisow, bez
	duplikatow (kolejnosc pierwszego wystapienia) i bez osoby odpowiedzialnej
	(`assigned_to`), ktora nie moze byc w obu rolach naraz. Zwraca nowa liste."""
	wynik: list[str] = []
	for osoba in osoby or []:
		osoba = (osoba or "").strip()
		if osoba and osoba != (wykonawca or "") and osoba not in wynik:
			wynik.append(osoba)
	return wynik


def nowo_dodani(przed: list[str | None] | None, po: list[str | None] | None) -> list[str]:
	"""Osoby z listy `po`, ktorych nie bylo na liscie `przed` (ops#411)."""
	byli = set(przed or [])
	return [osoba for osoba in dict.fromkeys(po or []) if osoba and osoba not in byli]


def autor_wzmiankowany(tresc: str | None, uzytkownik: str | None) -> bool:
	"""Czy HTML wpisu zawiera wzmianke (`span data-type="mention"`) uzytkownika."""
	if not tresc or not uzytkownik:
		return False
	for znacznik in _MENTION_RE.findall(tresc):
		trafienie = _DATA_ID_RE.search(znacznik)
		if trafienie and trafienie.group(1).strip().lower() == uzytkownik.strip().lower():
			return True
	return False


def etykieta_statusu(status: str | None) -> str:
	return _ETYKIETY_STATUSU.get(status or "", status or "")


def tekst_powiadomienia(
	zdarzenie: str,
	aktor: str,
	tytul: str | None,
	nowa_wartosc: str | None = None,
) -> str:
	"""HTML tekstu dzwonka (uklad jak `_notify_mention`): aktor, czynnosc, tytul
	zadania. `nowa_wartosc` (status, termin, wykonawca) dopisywana, gdy jest.
	Wszystkie teksty uzytkownika escapowane."""
	if zdarzenie not in ZDARZENIA:
		raise ValueError(f"Nieznane zdarzenie: {zdarzenie!r}")
	czynnosc = {
		"wpis": "dodał(a) wpis w zadaniu",
		"status": "zmienił(a) status zadania",
		"termin": "zmienił(a) termin zadania",
		"wykonawca": "zmienił(a) osobę przypisaną do zadania",
		"dw": "dodał(a) Cię do wiadomości w zadaniu",
	}[zdarzenie]
	dopisek = ""
	if nowa_wartosc:
		dopisek = f' <span class="text-ink-gray-5">({escape(nowa_wartosc)})</span>'
	return (
		'<div class="mb-2 leading-5 text-ink-gray-5">'
		f'<span class="font-medium text-ink-gray-9">{escape(aktor or "")}</span> '
		f"<span>{czynnosc}</span> "
		f'<span class="font-medium text-ink-gray-9">{escape(tytul or "")}</span>{dopisek}'
		"</div>"
	)
