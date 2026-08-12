# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF —
wariant „ME" (magazyn energii, sprzedaż i montaż bez fotowoltaiki).

Ten moduł jest odpowiednikiem `crm/volteo_umowa_mapa.py` (mapa dla szablonu
PV+ME) dla NOWEGO, osobnego szablonu jednoproduktowego. Reużywa stamtąd samą
klasę `Pole` (identyczny kontrakt danych — patrz jej docstring), ale definiuje
WŁASNĄ krotkę `MAPA_ME`, własną sumę kontrolną i własną liczbę stron: te dwa
szablony PDF nie mają ze sobą nic wspólnego pod względem układu strony (mimo
że jeden dokument bywa podzbiorem tekstu drugiego), więc mapy nie da się i nie
wolno mieszać.

POMIAR: 2026-08-12, `pdftotext -bbox crm/szablony/umowa_me.pdf` (surowe
`xMin`/`xMax`/`yMin`/`yMax` liczone OD GÓRY strony) plus, tam gdzie słowo w
bbox sklejało kreskę podkreślenia z sąsiadującym znakiem interpunkcyjnym bez
spacji (Załącznik nr 7: „_________________," i „_________________​,"),
dodatkowo `pdfplumber` na poziomie pojedynczych znaków (`page.chars`), żeby
wyciąć dokładną granicę samej kreski bez doklejonego przecinka. WSZYSTKIE
wartości poniżej są wyjściem skryptu (`compute.py` w scratchpadzie zadania),
nie arytmetyką „w pamięci" — zgodnie z tą samą zasadą, którą ustanowił
`crm/volteo_umowa_mapa.py` po incydencie z sześcioma błędami z ręcznego
liczenia (patrz jego docstring).

UKŁAD WSPÓŁRZĘDNYCH — identyczny jak w `crm/volteo_umowa_mapa.py`, nie
powtarzany tu w pełni; kluczowe punkty:
- `y_reportlab = 842 - y_od_gory` (pdftotext liczy od góry, reportlab od dołu).
- Podkreślenia („______"): `x = xMin + 3`, `y = 842 - yMax + 2.5`,
  `maks_szerokosc = szerokość_kreski - 6`.
- Kratki (`rodzaj="kratka"`, `wyrownanie="srodek"`): `x` = środek glifu w
  poziomie, `y = 842 - yMax_glifu + offset`. Offset `3.0 pt` dla kratek
  standardowych (15x15 pt — cała ta mapa poza Załącznikiem nr 2/3), `2.0 pt` i
  `rozmiar=8.0` dla mniejszych kratek 10x10 pt na stronie zgód (Załącznik
  nr 2/3) — DOKŁADNIE jak w PVME. Inaczej niż w PVME (gdzie `pdftotext`
  wymagał sięgnięcia po strumień treści PDF dla tych glifów — offset
  (+5.00, +0.59) opisany przy `_STRONA_7` tamtej mapy), w tym szablonie
  `pdftotext -bbox` poprawnie zwrócił bounding boxy „☐" o rozmiarze 10x10 pt
  jako zwykłe słowa — nie było potrzeby sięgać po strumień treści.
- Pola w tabeli (dane klienta w komparycji): `x` = zmierzony pikselowo środek
  pionowej kreski dzielącej kolumnę etykiet od kolumny wartości + 6 pt
  wcięcia (kreska zmierzona przez `pdfplumber` — `page.lines`, bo `pdftotext`
  nie raportuje grafiki wektorowej); `y = 842 - yMax(etykiety)`, bez korekty.
- Domyślny `rozmiar` 10.0 (nie nadpisywany poza kratkami zgód).

BEZPIECZNIK ZMIANY SZABLONU: `MAPA_ME` obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji `crm/szablony/umowa_me.pdf`, której suma SHA-256 jest zapisana w
`SHA256_SZABLONU_ME`. Generator PDF-u (analogicznie do `zloz_umowe()` w
`crm/volteo_umowa_render.py` dla PVME) MA sprawdzić tę sumę przed użyciem tej
mapy i przerwać z czytelnym komunikatem przy niezgodności.

CROSS-CHECK wobec PVME (`crm/volteo_umowa_mapa.py`), zanotowany podczas
kalibracji, dla przyszłych czytelników: Załącznik nr 4 (RODO, linia podpisu)
i Załącznik nr 7 (Pełnomocnictwo OSD) mają w obu szablonach IDENTYCZNĄ
geometrię co do 0,01 pt (`xMin`/`xMax`/`yMax` linii identyczne) — to ten sam
tekst prawniczy wklejony w oba dokumenty bez zmian. Załącznik nr 2/3 (zgody)
zgadza się co do pierwszych dwóch kratek (Załącznik 2) niemal idealnie, ale
kratka Załącznika nr 3 różni się o ok. 10,6 pt w `y` względem PVME — obie
wartości zmierzone tu niezależnie skryptem, różnica ma oczywistą przyczynę
(różna długość akapitów nad nią w każdym szablonie), nie jest błędem pomiaru.
Strona komparycji (dane klienta) i §2/§3 NIE są współdzielone między
szablonami (inne nagłówki, inna treść) — tam `x`/`y` różnią się od PVME
zauważalnie (do ok. 4 pt na `x` w `umowa_nr`, kilkanaście pt na `y` wszędzie)
i jest to oczekiwane, nie błąd."""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ME: str = "75283b8b52b568e545ec73bdd3b64569bab034b296f0e10499d2fa6cc1b458cf"
"""SHA-256 pliku `crm/szablony/umowa_me.pdf` (A4, 596x842 pt, 14 stron, Producer
"Skia/PDF m153 Google Docs Renderer"), zweryfikowane `shasum -a 256` na pliku
dostarczonym do tego zadania (2026-08-12). `MAPA_ME` poniżej jest skalibrowana
WYŁĄCZNIE dla dokładnie tego pliku — każda zmiana szablonu (nawet kosmetyczna,
np. przesunięcie akapitu) unieważnia wszystkie współrzędne poniżej."""

LICZBA_STRON_ME: int = 14
"""Liczba stron `crm/szablony/umowa_me.pdf`, zweryfikowana `pdfinfo`."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja, §1 Przedmiot umowy
#
# Tabela danych klienta: pionowa kreska dzieląca kolumny (zmierzona
# `pdfplumber`, `page.lines`) leży na x=171.500004, prawa krawędź tabeli na
# x=522.5000175 — stąd `x` pól = 171.500004 + 6 = 177.5, `maks_szerokosc` =
# (522.5000175 - 3) - 177.5 = 342.0 (3 pt zapasu od prawej krawędzi tabeli,
# symetrycznie do 3 pt wcięcia od lewej kreski).
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("adres_montazu", 0, 111.0, 353.57, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 289.88, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. g — powierzchnia budynku
#
# `x`/`maks_szerokosc` tego bloku zgadzają się z PVME (`_STRONA_3` tamtej
# mapy) co do ok. 0,01 pt — identyczny akapit, po prostu inaczej położony w
# pionie (inna treść nad nim w każdym szablonie).
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 703.93, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 703.42, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe — blok podpisów umowy głównej
#
# Jak w PVME (zob. uzasadnienie przy `_STRONA_4` w `crm/volteo_umowa_mapa.py`):
# Autenti dokleja jedno zbiorcze poświadczenie na końcu pliku, więc te pozycje
# wypełniają miejsce na podpis DRUKOWANYMI literami jako oznaczenie strony, nie
# jako podpis w rozumieniu prawa. Kreska podpisu (pdftotext -bbox): Zamawiający
# xMin=72.0/xMax=235.999663, Wykonawca xMin=360.0/xMax=521.223511, oba
# yMax=480.215334 — `xMin`/`xMax` identyczne co do 0,000001 pt z PVME (ten sam
# blok podpisów wklejony w oba szablony), `yMax` różni się (inna treść nad
# blokiem w każdym szablonie).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 364.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 364.28, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik nr 1 — Arkusz ustaleń montażowych
#
# W tym szablonie (inaczej niż w PVME, gdzie Załącznik 1a/1b są DWIEMA
# osobnymi stronami — panele+falownik / bateria) wszystkie dane techniczne
# mieszczą się na JEDNEJ stronie: falownik, bateria, internet/moc
# przyłączeniowa/fazy, a potem sekcja „W PRZYPADKU POSIADANIA INSTALACJI
# FOTOWOLTAICZNEJ" (existing-PV). Świadomie BRAK pozycji `inwerter_szt` —
# ten szablon nie ma pola „Ilość inwerterów" (magazyn energii montowany jest
# zawsze z jednym falownikiem/hybrydą, więc pole jest zbędne i faktycznie
# nieobecne w treści). Etykieta „Moc inwertera (kW)" i „Producent inwertera"
# WYSTĘPUJĄ NA TEJ STRONIE DWUKROTNIE — raz dla nowego falownika magazynu
# (góra strony, `inwerter_moc_kw`), raz w sekcji existing-PV (dół strony,
# `ist_pv_moc_inwertera_kw`/`ist_pv_producent_inwertera`) — rozróżnione tu po
# pozycji pionowej (yMax 153.6 vs. 417.5), zgodnie z etykietą sekcji.
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("inwerter_producent_model", 4, 205.01, 708.11, "tekst", maks_szerokosc=244.17),
	Pole("inwerter_moc_kw", 4, 167.2, 690.86, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 673.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_producent_model", 4, 191.13, 639.11, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 4, 153.31, 621.86, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 4, 293.9, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 4, 444.49, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 4, 272.24, 587.37, "tekst", maks_szerokosc=57.93),
	Pole("bateria_gwarancja_lat", 4, 236.69, 570.12, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 531.44, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 509.75, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 488.32, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 488.32, "kratka", wyrownanie="srodek"),
	# Sekcja "W PRZYPADKU POSIADANIA INSTALACJI FOTOWOLTAICZNEJ" (existing-PV) —
	# druga instancja etykiet "Moc inwertera (kW)" / "Producent inwertera".
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 426.95, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 409.71, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 392.46, "tekst", maks_szerokosc=155.22),
	# Blok podpisów Załącznika 1 — patrz uzasadnienie przy `_STRONA_4` powyżej.
	# Kreska podpisu (pdftotext -bbox): Zamawiający xMin=72.0/xMax=235.999663,
	# Wykonawca xMin=360.0/xMax=521.223511, oba yMax=574.507324.
	Pole("podpis_zamawiajacy", 4, 75.0, 269.99, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 269.99, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 2 (zgody) i Załącznik nr 3 (oświadczenie
# o realizacji przed terminem odstąpienia) — oba na TEJ SAMEJ stronie, tak
# jak w PVME.
#
# Kratki na tej stronie są mniejsze (10x10 pt, nie 15x15 jak gdzie indziej w
# tej mapie), stąd inny offset (2,0 pt) i mniejszy `rozmiar` (8 pt), zgodnie
# z konwencją PVME. Inaczej niż tam, `pdftotext -bbox` zwrócił tu poprawne
# bounding boxy glifu „☐" wprost jako słowa (xMin/xMax/yMin/yMax, rozmiar
# dokładnie 10x10 pt) — NIE trzeba było sięgać po strumień treści PDF.
# `zgoda_telefon`/`zgoda_promocja` (Załącznik 2, `y`=721,54/681,87) zgadzają
# się z PVME (`_STRONA_7` tamtej mapy: 721,54/681,87) co do 0,01 pt — ten sam
# akapit wklejony w oba szablony. `zgoda_wczesniejsza_realizacja` (Załącznik
# 3) różni się od PVME o ok. 10,6 pt w `y` (271,93 tu vs. 261,35 tam) —
# oczywista przyczyna: inna długość treści między Załącznikiem 2 a 3 w każdym
# szablonie (tu obie kratki bliżej siebie), zmierzone tu niezależnie, nie
# błąd pomiaru.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Blok podpisów Załącznika 2 — WYŁĄCZNIE linia Zamawiającego, bez
	# Wykonawcy (zgodnie z renderem strony — oba oświadczenia jednostronne).
	# Kreska (pdftotext -bbox): xMin=72.0/xMax=233.223511/yMax=242.185544.
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Blok podpisów Załącznika 3 (osobno, niżej na tej samej stronie).
	# Kreska (pdftotext -bbox): xMin=72.0/xMax=233.223511/yMax=718.245114.
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8 (indeks 7): Załącznik nr 4 — klauzula RODO, linia podpisu klienta
# ("Zamawiający" nad kreską, "data i podpis" pod nią). Kreska (pdftotext
# -bbox): xMin=72.0/xMax=233.223511/yMax=268.633304 — IDENTYCZNA co do
# 0,000001 pt z odpowiadającą pozycją w PVME (`_STRONA_9` tamtej mapy,
# indeks 8): ten sam blok RODO wklejony bez zmian w oba szablony, więc
# `rodo_data_imie_nazwisko` ma tu dokładnie te same `x`/`y`/`maks_szerokosc`.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 14 (indeks 13): Załącznik nr 7 — Pełnomocnictwo OSD
#
# Cały ten blok (dane klienta + linia podpisu Mocodawcy) jest w PVME
# (`_STRONA_18` tamtej mapy, indeks 17) IDENTYCZNY co do 0,01 pt na każdym
# polu — ten sam tekst pełnomocnictwa wklejony bez zmian w oba szablony.
# ---------------------------------------------------------------------------
_STRONA_14: tuple[Pole, ...] = (
	# "udzielone w dniu ___" — jak w PVME, brak osobnego klucza w kontekście
	# na datę udzielenia pełnomocnictwa (podpisywane tego samego dnia co
	# umowa); świadomie reużyty `data_zawarcia`.
	Pole("data_zawarcia", 13, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 13, 171.13, 681.66, "tekst", maks_szerokosc=88.52),
	Pole("klient_adres", 13, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 13, 110.01, 668.43, "tekst", maks_szerokosc=116.3),
	# Jedna linia podpisu — "Mocodawcy" (klient), BEZ Wykonawcy, jak w PVME.
	# Kreska podpisu (pdftotext -bbox, poprawiona o doklejony bez spacji
	# przecinek innych linii tej strony zmierzonych `pdfplumber` na poziomie
	# znaków — ta linia sama nie miała takiego problemu): xMin=362.054235/
	# xMax=523.277746/yMax=665.349614.
	Pole("podpis_zamawiajacy", 13, 365.05, 179.15, "tekst", maks_szerokosc=155.23),
)

MAPA_ME: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_8
	+ _STRONA_14
)
"""Pełna mapa dla szablonu ME: krotka wszystkich `Pole` na wszystkich stronach.
Jeden klucz kontekstu może wystąpić wielokrotnie (raz na każdej stronie, gdzie
faktycznie jest drukowany) — generator ma narysować wartość we WSZYSTKICH
pozycjach danego klucza, nie tylko w pierwszej."""

# Strony bez pozycji (indeksy 6, 8, 9, 10, 11, 12) — a konkretnie: strona 7 (indeks 6,
# Załącznik 4 RODO, PIERWSZA strona tego załącznika — administrator danych,
# cele przetwarzania), strona 9 (indeks 8, Załącznik 5 — pouczenie o prawie do
# odstąpienia), strona 10 (indeks 9, Załącznik 5 — formularz odstąpienia,
# pusty formularz do ewentualnego wypełnienia przez klienta w przyszłości —
# świadomie bez żadnego pola z kontekstu, tak jak w PVME), strona 11 (indeks
# 10, Załącznik 6 — Protokół odbioru magazynu energii, str. 1: dane
# klienta/instalatora/techniczne magazynu — decyzja produktowa 2026-08-12,
# spójna z PVME b44: protokół odbioru ma być CAŁKOWICIE pusty, wypełnia go
# ręcznie instalator dopiero po montażu), strona 12 (indeks 11, Załącznik 6 —
# protokół odbioru str. 2: listy szkoleniowe/zdjęć + linie podpisu
# klienta/instalatora — również ręcznie wypełniane przy montażu, świadomie
# bez podpisu wydrukowanego z naszej strony, z tego samego powodu co
# protokoły odbioru w PVME), strona 13 (indeks 12, protokół pomiarów
# magazynu energii — wypełniany przez instalatora) — NIE zawierają żadnej
# pozycji z kontekstu `zbuduj_kontekst`.


def pozycje_dla_me(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_ME` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_ME if pole.klucz == klucz)


def klucze_w_mapie_me() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_ME` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_ME)
