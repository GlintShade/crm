# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant PODWÓJNY (dwóch Zamawiających, np. małżonkowie), „ME” (magazyn
energii, sprzedaż i montaż bez fotowoltaiki), `crm/szablony/umowa_me_podwojna.pdf`.

SZKIELET, nie zmierzona mapa. Ten moduł istnieje po to, żeby suma SHA-256 i
liczba stron nowego szablonu miały jedno stabilne miejsce, obok
`crm/volteo_umowa_mapa_me.py` (wariant jednoosobowy), zanim ktokolwiek zmierzy
pojedynczą pozycję. `MAPA_ME2` poniżej jest CELOWO pustą krotką - właściwy
pomiar współrzędnych (`pdftotext -bbox` + w razie potrzeby `pdfminer`/
`pdfplumber`, jak w `crm/volteo_umowa_mapa_me.py`) jest zakresem osobnego
zadania (issue #166), nie tego. Rejestracja tego wariantu w
`crm.volteo_umowa_render.SZABLONY` też NIE jest zakresem tego modułu - to
zakres kolejnego zadania (issue #167), po tym jak mapa zostanie faktycznie
zmierzona.

Źródło: plik dostarczony przez właściciela, nazwa oryginalna
`PODWÓJNA Umowa ME ProEnergy - 28.07.2026.pdf`, skopiowany bajt w bajt (bez
konwersji, bez re-eksportu) do `crm/szablony/umowa_me_podwojna.pdf`. Wyeksportowany
z Google Docs, `pdfinfo` na pliku w repo potwierdza: `Producer: Skia/PDF m156
Google Docs Renderer`, strona A4 596x842 pt, 15 stron. Ten wariant PODWÓJNY
żyje OBOK istniejącego wariantu jednoosobowego (`crm/szablony/umowa_me.pdf`,
`crm/volteo_umowa_mapa_me.py`) jako dodatkowa opcja, nie jego zamiennik -
żaden z trzech dotychczasowych szablonów jednoosobowych ani ich map nie jest
tym zadaniem dotknięty. Plik dostarczony i skopiowany do repo 2026-09-23.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ME2: str = "df88a28fd3a1c68378d02c3bd9d610528779d2d732900b42fc41f77d992fa51d"
"""SHA-256 pliku `PODWÓJNA Umowa ME ProEnergy - 28.07.2026.pdf` (A4, 596x842 pt,
15 stron), policzone `shasum -a 256` na pliku W REPO (`crm/szablony/umowa_me_podwojna.pdf`)
po skopiowaniu, 2026-09-23. Gdy #166 zmierzy `MAPA_ME2`, generator PDF-u ma
sprawdzić tę sumę przed użyciem mapy i przerwać z czytelnym komunikatem przy
niezgodności - dokładnie jak dla trzech dotychczasowych szablonów."""

LICZBA_STRON_ME2: int = 15
"""Liczba stron oryginału, zgodna z `pdfinfo`. Jedna strona więcej niż wariant
jednoosobowy (`LICZBA_STRON_ME` = 14) - dodatkowe dane drugiego Zamawiającego."""

MAPA_ME2: tuple[Pole, ...] = ()
# wypelniane w #166, pusta mapa NIE moze trafic do SZABLONY


def pozycje_dla_me2(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_ME2` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_ME2 if pole.klucz == klucz)


def klucze_w_mapie_me2() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_ME2` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_ME2)
