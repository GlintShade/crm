# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy obsługi dotacji Czyste Powietrze
na oryginalny plik PDF.

Odpowiednik `crm/volteo_umowa_mapa.py`/`crm/volteo_kredyt_mapa.py` dla piątego
dokumentu (issue ops#212): „Umowa o świadczenie usług obsługi dofinansowania w
ramach Programu Czyste Powietrze" (`crm/szablony/umowa_cp_obsluga_dotacji.pdf`,
6 stron). Moduł celowo nie importuje ``frappe`` ani ``reportlab`` — czysta
struktura danych, w pełni testowalna lokalnie (`crm/test_volteo_umowa_mapa_cp.py`).
`Pole` jest importowany z `crm.volteo_umowa_mapa` — NIE definiować go tu ponownie,
zgodnie z konwencją `volteo_umowa_mapa_pv.py`/`volteo_kredyt_mapa.py`.

UKŁAD WSPÓŁRZĘDNYCH (identyczny jak w `volteo_umowa_mapa.py` — przeczytaj tamten
docstring, jeśli edytujesz tę mapę): ``pdftotext -bbox`` podaje ``yMin``/``yMax``
liczone OD GÓRY strony. ``reportlab`` (generator) rysuje w układzie liczonym OD
DOŁU strony. Każda wartość ``y`` zapisana w tym pliku jest już PRZELICZONA:
``y_reportlab = 842 - y_od_gory``. Strona ma wymiary 596x842 pt (A4). Strony
numerowane 0-indeksowo (strona 1 dokumentu = 0).

WSZYSTKIE współrzędne poniżej zostały zmierzone SKRYPTEM na oryginalnym pliku:
``pdftotext -bbox crm/szablony/umowa_cp_obsluga_dotacji.pdf`` dla tekstu,
podkreśleń (ciągów ``_____``) i glifów kratek ``☐``; ``pdfminer.six``
(`LTLine`) dla wektorowej siatki tabeli danych klienta na str. 1 (żadnego
glifu do zmierzenia tam nie ma — same linie). Żadna wartość nie jest
przepisana ręcznie ani zgadnięta.

Trzy rodzaje pozycji, dokładnie tak samo policzone jak w `volteo_umowa_mapa.py`
i `volteo_kredyt_mapa.py`:

1. **Podkreślenie** (``______``, komparycja str. 1, kwoty §4 str. 2, linie
   podpisu str. 4/5/6): ``x = xMin(linii) + 3``, ``y = 842 - yMax(linii) +
   2,5``, ``maks_szerokosc = szerokość(linii) - 6`` (zapas 3 pt z każdej
   strony linii, identyczna formuła co `_STRONA_4` w `volteo_umowa_mapa.py`
   i pole 2 „Pole z kropkowaną linią" w `volteo_kredyt_mapa.py`).

2. **Komórka tabeli** (dane Zamawiającego, str. 1: Imię i nazwisko / Adres /
   PESEL / Telefon / Adres e-mail): ``x`` = zmierzona WEKTOROWO (`pdfminer`
   `LTLine`, kreska dzieląca kolumnę etykiet od kolumny wartości, x=171.5)
   plus 6 pt wcięcia = 177.5; ``y = 842 - yMax(etykiety)`` — bez korekty
   2,5 pt, bo w tabeli nie ma osobnej kreski do podkreślenia, wartość ma po
   prostu stanąć w tej samej linii co etykieta wiersza (identyczna konwencja
   jak w `MAPA`/`MAPA_KREDYT` dla tabel danych klienta); ``maks_szerokosc`` =
   prawa krawędź tabeli (też zmierzona wektorowo, x=522.5) minus ``x`` = 345.0.
   Zweryfikowane: każde policzone ``y`` mieści się w granicach swojego wiersza
   z siatki `pdfminer` (linie poziome przy y_top 664.5/639.5/615.5/590.5/
   566.5/541.5, pięć wierszy 24-25 pt).

3. **Kratka mała** (``☐``, Załącznik nr 1 - zgody, str. 5): rozmiar
   ``8.0`` pt (konwencja „8-punktowych kratek na stronie zgód" z
   `volteo_umowa_mapa.py`, nie elaborate connected-component method
   z `volteo_kredyt_mapa.py`, zgodnie z briefem zadania). ``x`` = środek
   poziomy zmierzonego glifu (``(xMin+xMax)/2``), ``y = 842 - yMax(glifu) +
   2,0`` (2,0 pt nad dolną krawędzią glifu, jak w komentarzu przy `_STRONA_7`
   w `volteo_umowa_mapa.py`).

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u (`crm/volteo_umowa_render_cp.py`)
sprawdza sumę SHA-256 pliku wejściowego względem ``SHA256_SZABLONU_CP`` przed
użyciem tej mapy i przerywa z czytelnym komunikatem przy niezgodności —
nigdy nie wpisywać danych w oparciu o niepewne współrzędne.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_CP: str = "a402e988107a036836793aa88b856afd453ba972959593e75201aa85ae50d467"
"""SHA-256 pliku `Umowa - Obsługa dotacji.pdf` (A4, 596x842 pt, 6 stron, bez pól
formularza, Skia/PDF m156 Google Docs Renderer — sam producer co szablon umowy
PV+ME od b64/ops#196, spójne z tym, że oba dokumenty wyszły z tego samego
firmowego szablonu Google Docs), policzone `shasum -a 256` na oryginale
dostarczonym do tego zadania (issue ops#212) i zweryfikowane ponownie po
skopiowaniu do `crm/szablony/umowa_cp_obsluga_dotacji.pdf`. Mapa `MAPA_CP`
poniżej jest skalibrowana WYŁĄCZNIE dla tego dokładnego pliku — każda zmiana
szablonu (nawet kosmetyczna) unieważnia współrzędne."""

LICZBA_STRON_CP: int = 6
"""Liczba stron oryginału, zgodna z `pdfinfo`. Używana przez generator/testy do
sprawdzenia, że żadna pozycja w mapie nie wskazuje strony poza dokumentem."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja (nr umowy, data zawarcia, dane Zamawiającego)
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	# "nr ________________________" (pdftotext -bbox: xMin=207.11/xMax=407.33/
	# yMax=128.92).
	Pole("umowa_nr", 0, 210.11, 715.58, "tekst", maks_szerokosc=194.22),
	# "Zawarta dnia _________________" (xMin=132.56/xMax=227.07/yMax=162.84).
	Pole("data_zawarcia", 0, 135.56, 681.66, "tekst", maks_szerokosc=88.51),
	# Tabela danych Zamawiającego: kreska dzieląca kolumny x=171.5 (zmierzona
	# wektorowo `pdfminer` LTLine), prawa krawędź tabeli x=522.5 (też LTLine).
	# Pięć wierszy, każdy zweryfikowany w granicach siatki (patrz docstring
	# modułu, pkt 2).
	Pole("klient_imie_nazwisko", 0, 177.5, 646.71, "tekst", maks_szerokosc=345.0),
	Pole("klient_adres", 0, 177.5, 622.24, "tekst", maks_szerokosc=345.0),
	Pole("klient_pesel", 0, 177.5, 597.76, "tekst", maks_szerokosc=345.0),
	Pole("klient_telefon", 0, 177.5, 573.29, "tekst", maks_szerokosc=345.0),
	Pole("klient_email", 0, 177.5, 548.81, "tekst", maks_szerokosc=345.0),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §4 Wynagrodzenie
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	# "_____________________________ zł netto" (xMin=110.78/xMax=272.00/
	# yMax=625.68).
	Pole("wynagrodzenie_netto", 1, 113.78, 218.82, "tekst", maks_szerokosc=155.22),
	# "_____________________________ zł brutto" (xMin=110.78/xMax=272.00/
	# yMax=652.13).
	Pole("wynagrodzenie_brutto", 1, 113.78, 192.37, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §5-§9 (obowiązki, odpowiedzialność, odstąpienie) —
# czysty tekst prawny, bez pól formularza (zweryfikowane: brak jakiegokolwiek
# glifu kratki/podkreślenia/podpisu na tej stronie).
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = ()

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §10 Postanowienia końcowe — blok podpisów umowy
# głównej (Zamawiający + Wykonawca, jedna linia każdy).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	# Kreska podpisu (pdftotext -bbox): Zamawiający xMin=72.0/xMax=236.0/
	# yMax=361.20, Wykonawca xMin=360.0/xMax=521.22/yMax=361.20 (ta sama linia
	# pozioma).
	Pole("podpis_zamawiajacy", 3, 75.0, 483.3, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 483.3, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik nr 1 — Oświadczenie w sprawie wyrażenia zgody
# na przetwarzanie danych osobowych (trzy zgody + linia podpisu, WYŁĄCZNIE
# Zamawiający, bez Wykonawcy — jednostronne oświadczenie klienta, jak
# Załącznik 18 w `volteo_umowa_mapa.py`).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	# Trzy glify "☐" (pdftotext -bbox, wszystkie xMin=72.00/xMax=82.00):
	# zgoda 1 yMax=162.13, zgoda 2 yMax=201.80, zgoda 3 yMax=241.47.
	Pole("zgoda_przetwarzanie_danych", 4, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_telefon", 4, 77.0, 642.2, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 4, 77.0, 602.53, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Kreska podpisu (pdftotext -bbox): xMin=72.0/xMax=233.22/yMax=321.53.
	Pole("podpis_zamawiajacy", 4, 75.0, 522.97, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 2 — Klauzula informacyjna RODO, jedna
# wspólna linia "(data i podpis)" pod tekstem, WYŁĄCZNIE Zamawiający.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	# Kreska podpisu (pdftotext -bbox): xMin=72.0/xMax=233.22/yMax=718.25.
	Pole("data_i_podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

MAPA_CP: tuple[Pole, ...] = _STRONA_1 + _STRONA_2 + _STRONA_3 + _STRONA_4 + _STRONA_5 + _STRONA_6
"""Pełna mapa współrzędnych umowy obsługi dotacji CP: 7 pozycji na str. 1
(indeks 0), 2 na str. 2 (indeks 1), 0 na str. 3 (indeks 2), 2 na str. 4
(indeks 3, oba podpisy), 4 na str. 5 (indeks 4, trzy zgody + podpis), 1 na
str. 6 (indeks 5, data i podpis), razem 16. Jeden klucz kontekstu (`podpis_
zamawiajacy`) występuje na dwóch stronach (4 i 5) — generator ma narysować
wartość we WSZYSTKICH pozycjach danego klucza, nie tylko w pierwszej."""


def pozycje_dla_cp(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_CP` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_CP if pole.klucz == klucz)


def klucze_w_mapie_cp() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_CP` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_CP)
