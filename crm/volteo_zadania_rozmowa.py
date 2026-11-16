# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Sekcja "Rozmowa" w oknie zadania (`CRM Task`), frappe-free.

Wpis rozmowy to zwykly `Comment` Frappe (`comment_type = "Comment"`) z
`reference_doctype = "CRM Task"`. `Comment` ma `track_changes = 1`, wiec kazda
edycja tresci tworzy wiersz `Version` (`ref_doctype = "Comment"`, `docname` =
nazwa komentarza, `data` = JSON z kluczem `changed`, np.
`{"changed": [["content", "<p>stara</p>", "<p>nowa</p>"]]}`). Historia zmian
wpisu to wylacznie odczyt tych wierszy -- nic dodatkowego nie jest zapisywane.

Modul celowo nie importuje ``frappe`` (na tej maszynie ``frappe`` nie jest
instalowalne, wiec tylko tak da sie go przetestowac lokalnie). Cala logika
zalezna od frameworka (bramka uprawnien do zadania, odczyt `Comment`/`Version`/
`File`, dodawanie wpisu) mieszka w ``crm.api.zadania_rozmowa``, tu tylko czyste
funkcje.
"""

import json

__all__ = [
	"etykieta_zrodla",
	"liczba_zmian_tresci",
	"zmiany_tresci",
]


def _dane_wersji(dane: object) -> dict | None:
	"""Zawartosc pola `data` wiersza `Version` jako slownik, albo `None`, gdy
	nie da sie jej odczytac. Frappe zwraca `data` jako string JSON (kolumna
	Long Text), ale sondy i testy podaja tez gotowy slownik."""
	if isinstance(dane, dict):
		return dane
	if isinstance(dane, (str, bytes, bytearray)):
		try:
			wynik = json.loads(dane)
		except (ValueError, TypeError):
			return None
		return wynik if isinstance(wynik, dict) else None
	return None


def zmiany_tresci(wersje: list[dict], pole: str = "content") -> list[dict]:
	"""Z wierszy `Version` (pola: `owner`, `creation`, `data` jako string JSON
	albo slownik) wybiera zmiany pola `pole` (domyslnie `content`; `Volteo Notatka` i
	`Volteo Trify Update` trzymaja tresc w `tekst`). Zwraca liste
	`{"kto", "kiedy", "przed", "po"}` w kolejnosci rosnacej po `creation`.

	Wersje bez zmiany `content`, z niepoprawnym JSON albo bez klucza `changed`
	sa pomijane bez wyjatku -- wiersz `Version` dla innego pola (albo
	uszkodzony) nie moze zepsuc calej historii wpisu."""
	wynik: list[dict] = []
	for wersja in wersje or []:
		if not isinstance(wersja, dict):
			continue
		dane = _dane_wersji(wersja.get("data"))
		if not dane:
			continue
		zmiany = dane.get("changed")
		if not isinstance(zmiany, list):
			continue
		for zmiana in zmiany:
			if not isinstance(zmiana, (list, tuple)) or len(zmiana) < 3:
				continue
			if zmiana[0] != pole:
				continue
			wynik.append(
				{
					"kto": wersja.get("owner"),
					"kiedy": wersja.get("creation"),
					"przed": zmiana[1],
					"po": zmiana[2],
				}
			)
	# `creation` bywa datetime (z bazy) albo stringiem ISO (testy, JSON) --
	# `str()` daje w obu przypadkach porownywalna leksykograficznie postac, a
	# sort jest stabilny, wiec rowne chwile zachowuja kolejnosc wejsciowa.
	wynik.sort(key=lambda zmiana: str(zmiana["kiedy"] or ""))
	return wynik


def liczba_zmian_tresci(wersje: list[dict], pole: str = "content") -> int:
	"""Ile razy zmieniono tresc wpisu: `len(zmiany_tresci(wersje))`."""
	return len(zmiany_tresci(wersje, pole))


def etykieta_zrodla(tytul: str | None) -> str:
	"""Etykieta wpisu rozmowy w feedzie "Notatki" szansy: `Zadanie: <tytul>`,
	albo samo `Zadanie`, gdy zadanie nie ma tytulu."""
	tytul_czysty = (tytul or "").strip()
	if not tytul_czysty:
		return "Zadanie"
	return f"Zadanie: {tytul_czysty}"
