# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant PODWÓJNY, PV + ME (fotowoltaika + magazyn energii razem),
`crm/szablony/umowa_pv_me_podwojna.pdf`.

SZKIELET (issue #165): ten moduł na razie NIE zawiera żadnej zmierzonej
pozycji. Zadaniem #165 jest wyłącznie skopiowanie trzech nowych szablonów
PDF od właściciela i przygotowanie skorupy modułu każdej z trzech map -
faktyczny pomiar współrzędnych (`pdftotext -bbox`, ewentualnie `pdfminer`/
`pdfplumber` tam, gdzie bbox scala kreskę podkreślenia z sąsiednim znakiem,
dokładnie jak w `crm/volteo_umowa_mapa.py`) jest przedmiotem OSOBNEGO,
późniejszego zadania (issue #166). Do tego czasu `MAPA_PVME2` poniżej jest
CELOWO pustą krotką - patrz komentarz przy niej.

ŹRÓDŁO: plik `PODWÓJNA Umowa PV + ME ProEnergy - 28.07.2026.docx.pdf`,
dostarczony przez właściciela projektu 2026-09-23. Eksport: „Skia/PDF m156
Google Docs Renderer" (odczytane z `pdfinfo`), A4 596x842 pt, 20 stron.

WARIANT PODWÓJNY: ten szablon, w odróżnieniu od `crm/volteo_umowa_mapa.py`
(wariant PV+ME z JEDNYM Zamawiającym), obsługuje DWÓCH Zamawiających (np.
małżonków) na jednej umowie - komparycja, dane klienta i bloki podpisów mają
miejsce na dwie osoby zamiast jednej. Jest to szablon DODATKOWY, obok
istniejącego wariantu pojedynczego, nie jego zastąpienie: `crm/szablony/
umowa_pv_me.pdf` i `crm/volteo_umowa_mapa.py` (`MAPA`, jeden Zamawiający)
zostają bez zmian i nadal obowiązują tam, gdzie umowę zawiera jedna osoba.

ZNANA USTERKA ŹRÓDŁA (do korekty, nie naprawiane w tym zadaniu): w
odróżnieniu od podwójnych szablonów PV i ME osobno (gdzie oba pełnomocnictwa
są numerowane spójnie jako „Załącznik nr 7" i „nr 7.1"), ten podwójny
szablon PV+ME numeruje swoje dwa pełnomocnictwa NIESPÓJNIE: „Załącznik nr 8"
i „nr 7.1" (nie „nr 7" i „nr 7.1", jak w PV i ME osobno). To usterka
źródłowego pliku, nie błąd tego modułu - świadomie tu zapisana, żeby nie
zgubić się przy pomiarze w #166. Oczekuje na korektę właściciela. Jeżeli
kiedyś zostanie dostarczona poprawiona wersja tego pliku, będzie trzeba
przeliczyć od nowa zarówno `SHA256_SZABLONU_PVME2` poniżej, jak i późniejszy
pomiar współrzędnych z #166 - dla TEGO JEDNEGO wariantu (PV i ME osobno nie
są tą usterką dotknięte, ich pomiar zostaje bez zmian).

BEZPIECZNIK ZMIANY SZABLONU: mapa `MAPA_PVME2` (gdy zostanie wypełniona w
#166) będzie obowiązywać WYŁĄCZNIE dla dokładnie tej wersji oryginału.
Generator PDF-u ma sprawdzić sumę SHA-256 pliku wejściowego względem
`SHA256_SZABLONU_PVME2` przed użyciem tej mapy i przerwać z czytelnym
komunikatem przy niezgodności - identycznie jak dla `SHA256_SZABLONU` w
wariancie pojedynczym.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVME2: str = "e4be94cbf1a6fe6aeca16257f2f0d0e628b77037f2dad00b6023f07000dd16ab"
"""SHA-256 pliku `crm/szablony/umowa_pv_me_podwojna.pdf` (A4, 596x842 pt,
20 stron, Producer "Skia/PDF m156 Google Docs Renderer"), policzone
`shasum -a 256` na pliku dostarczonym do tego zadania (2026-09-23) i
zweryfikowane ponownie po skopiowaniu do `crm/szablony/umowa_pv_me_podwojna.pdf`.
Gdy mapa `MAPA_PVME2` zostanie wypełniona (issue #166), przyszły generator
PDF-u ma sprawdzić tę sumę przed użyciem mapy i przerwać z czytelnym
komunikatem przy niezgodności - ten sam bezpiecznik, co `SHA256_SZABLONU` w
wariancie pojedynczym. Jeżeli kiedyś zostanie dostarczona poprawiona wersja
pliku (patrz akapit o usterce numeracji załączników w docstringu modułu
powyżej), ta stała musi zostać przeliczona od nowa."""

LICZBA_STRON_PVME2: int = 20
"""Liczba stron oryginału, zgodna z `pdfinfo`. Ma być używana przez przyszłe
testy/generator (issue #166/#167) do sprawdzenia, że żadna pozycja w mapie
nie wskazuje strony poza dokumentem."""

MAPA_PVME2: tuple[Pole, ...] = ()
# wypelniane w #166, pusta mapa NIE moze trafic do SZABLONY
"""Mapa współrzędnych dla `crm/szablony/umowa_pv_me_podwojna.pdf`. CELOWO
pusta w tym zadaniu (#165) - faktyczny pomiar pozycji (`Pole` po `Pole`,
strona po stronie, wg konwencji z `crm/volteo_umowa_mapa.py`) jest
przedmiotem issue #166. Ten moduł NIE jest zarejestrowany w
`crm.volteo_umowa_render.SZABLONY` i nie wolno go tam dodać, dopóki
`MAPA_PVME2` nie zawiera realnych pozycji - pusta mapa zarejestrowana w
`SZABLONY` pozwoliłaby wygenerować umowę podwójną PV+ME bez naniesienia
jakichkolwiek danych, czyli po cichu wyprodukować pusty dokument prawny."""


def pozycje_dla_pvme2(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_PVME2` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_PVME2 if pole.klucz == klucz)


def klucze_w_mapie_pvme2() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_PVME2` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_PVME2)
