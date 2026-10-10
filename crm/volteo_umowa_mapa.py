# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych wzoru PVME (umowa PV + magazyn energii, jednoosobowa, bez dodatków)
do nakładania danych umowy na oryginalny plik PDF `crm/szablony/umowa_pv_me.pdf`.

Moduł celowo nie importuje ``frappe`` ani ``reportlab``: to czysta struktura danych
(plus proste funkcje pomocnicze), w pełni testowalna lokalnie
(`crm/test_volteo_umowa_mapa.py`). Moduł definiuje też klasę `Pole` importowaną przez
wszystkie pozostałe mapy.

UKŁAD WSPÓŁRZĘDNYCH (przeczytaj dwa razy przed edycją mapy): ``pdftotext -bbox``
podaje ``yMin``/``yMax`` liczone OD GÓRY strony, ``reportlab`` rysuje w układzie liczonym
OD DOŁU. Każda wartość ``y`` w tym pliku jest już PRZELICZONA: ``y_reportlab = 842 -
y_od_gory``. Strona ma 596x842 pt (A4). Tekst rysuje się od linii bazowej. Dla pól z
podkreśleniem (``______``) ``x = xMin(kreski) + 3``, ``y = 842 - yMax(kreski) + 2.5``,
``maks_szerokosc = szerokość(kreski) - 6``. Dla kratek ``x`` = środek glifu, ``y = 842 -
yMax(glifu) + 3.0`` (małe kratki zgód, glif węższy niż 12 pt: ``+ 2.0`` i ``rozmiar=8.0``).
Dla komórek tabeli danych klienta ``x`` = zmierzona wektorowo pionowa kreska dzieląca
kolumny + 6 pt, ``y = 842 - yMax(etykiety)``, ``maks_szerokosc`` = prawa krawędź tabeli
- 3 - ``x``.

POCHODZENIE WSPÓŁRZĘDNYCH: pomiar OD ZERA, 2026-10-10 (b69, chunk U2c, issue ops#241),
narzędziem `ops/narzedzia/umowa-mapa-pomiar.py` z repo `proenergy-crm-ops`
(deklaracja pól `ops/narzedzia/deklaracje/umowa_pv_me.py`) na pliku o SHA-256 poniżej.
Żadna wartość nie pochodzi z map siostrzanych ani ze starej wersji tego wzoru
(reeksport z Google Docs przesuwa nawet niezmienione strony). Wynik przejrzany
wzrokowo na renderze `--sprawdz` (pdftoppm -r 110) strona po stronie.

Plik źródłowy: `Umowa PV + ME ProEnergy - 28.07.2026-6.pdf` (wzór Leszka, stan
2026-10-09), Skia/PDF Google Docs Renderer, A4, 18 stron, bez pól formularza.

POLITYKA (które klucze idą na które strony):
- strona 1 (idx 0): komparycja, adres montażu, rodzaj budynku;
- strona 2 (idx 1): §2, nowe brzmienie opcji: "Kredyt 100%" / "Kredyt z wkładem własnym" /
  "Przelew" mapowane 1:1 na `fin_kredyt_100` / `fin_kredyt_wklad` / `fin_gotowka`
  (literały wartości w bazie bez zmian);
- strona 3 (idx 2): powierzchnia budynku (§3 ust. 1 lit. g);
- podpisy: Zamawiający i Wykonawca w umowie głównej (idx 3) oraz w Załącznikach 1a (idx 4)
  i 1b (idx 5); w Zał. 2, 3, RODO i pełnomocnictwie tylko linia Zamawiającego;
- Zał. 1a (PV) i Zał. 1b (magazyn) to OSOBNE strony, obie z blokiem podpisów;
- `data_zawarcia` jest reużywana w "udzielone w dniu" pełnomocnictwa, `klient_imie_nazwisko`
  występuje w komparycji i w pełnomocnictwie;
- BEZ pozycji (celowo): idx 7 (RODO część 1), idx 9 (pouczenie o odstąpieniu), idx 10
  (formularz odstąpienia), idx 11 do 16 (protokoły odbioru PV i magazynu, listy
  szkoleniowe, protokoły pomiarów): wypełnia je instalator albo klient po montażu, nasz
  podpis poświadczałby coś, co się jeszcze nie wydarzyło;
- wzór nie ma rubryk drugiego Zamawiającego ani dodatków (klimatyzacja, EV, panele
  dodatkowe, rozbudowa): te klucze kontekstu są jawnymi wyjątkami w testach.

BEZPIECZNIK ZMIANY SZABLONU: mapa obowiązuje WYŁĄCZNIE dla dokładnie tej wersji pliku;
generator sprawdza SHA-256 pliku względem ``SHA256_SZABLONU`` i odmawia renderu przy
niezgodności.
"""

from dataclasses import dataclass

LICZBA_STRON_PVME: int = 18
"""Liczba stron `crm/szablony/umowa_pv_me.pdf`, zweryfikowana `pdfinfo` (b69, chunk U1)."""

SHA256_SZABLONU: str = "e2fcd4503cc44575f6a4bf2321fbd9cc17513633bc2cc272db64e689b0046a21"
"""SHA-256 pliku `crm/szablony/umowa_pv_me.pdf` (wzór `Umowa PV + ME ProEnergy -
28.07.2026-6.pdf`, A4 596x842 pt, 18 stron). Mapa `MAPA` jest skalibrowana WYŁĄCZNIE dla
tego dokładnego pliku, każda zmiana (nawet kosmetyczna) unieważnia współrzędne."""

SZEROKOSC_STRONY_PT: float = 596.0
WYSOKOSC_STRONY_PT: float = 842.0
"""Wymiary strony A4 w punktach, zgodne z `pdfinfo` oryginału. Używane przez testy
do sprawdzenia, że każda współrzędna mieści się na stronie."""

_RODZAJE: frozenset[str] = frozenset({"tekst", "kratka"})
_WYROWNANIA: frozenset[str] = frozenset({"lewo", "srodek", "prawo"})


@dataclass(frozen=True)
class Pole:
	"""Jedna pozycja na jednej stronie, w którą generator ma wpisać wartość klucza.

	Ten sam ``klucz`` może (i często musi) wystąpić w wielu instancjach `Pole`
	— raz na każdej stronie, na której szablon rzeczywiście drukuje tę wartość
	(np. imię i nazwisko klienta pojawia się w komparycji, w pełnomocnictwie
	i w obu protokołach odbioru).
	"""

	klucz: str
	"""Klucz kontekstu zwracanego przez `crm.volteo_umowa_pdf.zbuduj_kontekst`."""

	strona: int
	"""Numer strony, 0-indeksowany (strona 1 dokumentu = 0)."""

	x: float
	"""Współrzędna pozioma w punktach, liczona od LEWEJ krawędzi strony."""

	y: float
	"""Współrzędna pionowa w punktach, liczona od DOLNEJ krawędzi strony
	(układ reportlab — zob. docstring modułu). To linia bazowa tekstu."""

	rodzaj: str
	"""``"tekst"`` — wpisanie wartości stringowej: ``"kratka"`` — narysowanie
	„X" w środku kratki, gdy wartość logiczna jest `True`."""

	wyrownanie: str = "lewo"
	"""``"lewo"`` | ``"srodek"`` | ``"prawo"`` — sposób wyrównania tekstu/znaku
	względem punktu (x, y). Kratki używają `"srodek"` (x = środek kratki)."""

	maks_szerokosc: float | None = None
	"""Maksymalna szerokość w punktach dostępna na wpisanie wartości (do
	przycięcia/zawinięcia długich wartości przez generator). `None`, gdy nie
	zmierzono ograniczenia (np. kratki, gdzie nie ma zastosowania)."""

	rozmiar: float = 10.0
	"""Rozmiar fontu w punktach."""


# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja, §1 Przedmiot umowy
# Jedna tabela danych klienta (5 wierszy), numer umowy i data na kreskach, adres montażu
# (trzecia kreska strony, bez etykiety w linii), dwie kratki rodzaju budynku.
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("umowa_nr", 0, 206.36, 721.51, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 697.43, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 0, 177.5, 658.48, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 634.01, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 609.53, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 585.06, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 560.58, "tekst", maks_szerokosc=342.0),
	Pole("adres_montazu", 0, 111.0, 331.4, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 274.33, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 254.49, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie i opcja finansowania
# Kwoty netto/brutto na kreskach; kratki "Kredyt 100%", "Kredyt z wkładem własnym",
# "Przelew" (klucze `fin_*`), wkład własny i kwota kredytu na kreskach pod drugą opcją.
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 715.33, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 688.88, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 618.58, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 598.75, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 556.64, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 530.2, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 512.79, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. g, powierzchnia użytkowa budynku
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 662.25, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 662.25, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 661.74, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe, blok podpisów umowy głównej
# Autenti dokleja jedno zbiorcze poświadczenie na końcu pliku; te pozycje wpisują
# DRUKOWANYMI literami oznaczenie strony (Zamawiający lewa kolumna, Wykonawca prawa),
# kolumna wybrana po współrzędnej x kreski, nie po kolejności w strumieniu.
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 346.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 346.28, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik 1a, arkusz ustaleń montażowych, instalacja PV
# Pola nowej instalacji, warunki instalacyjne, opcje dodatkowe (p.poż, przekop,
# kabel) i blok podpisów obu stron. Sekcji istniejącej PV nie ma na tej stronie (jest
# w Zał. 1b).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 4, 223.9, 715.33, "tekst", maks_szerokosc=55.16),
	Pole("panel_szt", 4, 381.7, 715.33, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 4, 186.09, 698.08, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 4, 280.02, 680.83, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 4, 249.46, 663.58, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 4, 183.31, 629.09, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 4, 174.42, 611.84, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_producent_model", 4, 205.01, 594.59, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 577.34, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 521.42, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 499.72, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 478.29, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 478.29, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 4, 157.28, 452.42, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 4, 213.37, 452.42, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 4, 268.9, 430.73, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 4, 182.29, 409.3, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 4, 228.76, 409.3, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 4, 398.41, 348.93, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 444.89, 348.93, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 4, 165.06, 323.06, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 4, 222.03, 322.55, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 4, 281.0, 323.06, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 4, 161.18, 297.18, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 4, 218.15, 296.67, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 4, 277.12, 297.18, "kratka", wyrownanie="srodek"),
	Pole("podpis_zamawiajacy", 4, 75.0, 170.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 170.28, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik 1b, arkusz ustaleń montażowych, magazyn energii
# Dane baterii, sekcja "w przypadku posiadania instalacji fotowoltaicznej" (istniejąca
# PV) i blok podpisów obu stron.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("bateria_producent_model", 5, 191.13, 715.33, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 5, 153.31, 698.08, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 5, 293.9, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 5, 444.49, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 5, 272.24, 663.58, "tekst", maks_szerokosc=55.16),
	Pole("bateria_gwarancja_lat", 5, 236.69, 646.33, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_inwertera_kw", 5, 167.2, 572.17, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 5, 232.76, 554.92, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 5, 170.01, 537.67, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 446.25, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 446.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 7 (indeks 6): Załącznik 2 (zgody) i Załącznik 3 (realizacja przed terminem)
# Małe kratki 10x10 pt (offset 2,0, rozmiar 8) i dwie osobne linie podpisu WYŁĄCZNIE
# Zamawiającego (po jednej pod każdym załącznikiem), bez Wykonawcy.
# ---------------------------------------------------------------------------
_STRONA_7: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 6, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 6, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 6, 77.0, 261.35, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 6, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 6, 75.0, 115.68, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 9 (indeks 8): Załącznik 4, koniec klauzuli RODO, linia podpisu klienta
# ---------------------------------------------------------------------------
_STRONA_9: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 8, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 18 (indeks 17): Załącznik 8, Pełnomocnictwo OSD
# `data_zawarcia` reużyta w "udzielone w dniu". Jedna linia podpisu, Mocodawcy (klient,
# prawa kolumna), bez Wykonawcy: pełnomocnictwo jest jednostronnym oświadczeniem klienta.
# ---------------------------------------------------------------------------
_STRONA_18: tuple[Pole, ...] = (
	Pole("data_zawarcia", 17, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 17, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 17, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 17, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 17, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_7
	+ _STRONA_9
	+ _STRONA_18
)
"""Pełna mapa: krotka wszystkich `Pole` na wszystkich stronach. Jeden klucz kontekstu może
wystąpić wielokrotnie (raz na każdej stronie, gdzie jest drukowany), generator rysuje
wartość we WSZYSTKICH pozycjach danego klucza."""

# Strony bez pozycji (indeksy 7, 9, 10, 11, 12, 13, 14, 15, 16): RODO część 1, pouczenie
# o odstąpieniu, formularz odstąpienia, protokoły odbioru PV i magazynu, listy szkoleniowe
# i zdjęć oraz protokoły pomiarów. Wypełniają je ręcznie instalator lub klient po montażu,
# żadna z tych wartości nie pochodzi z `Volteo Umowa`/`CRM Deal` w chwili generowania PDF-u.


def pozycje_dla(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA if pole.klucz == klucz)


def klucze_w_mapie() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA)
