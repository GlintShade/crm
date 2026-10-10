# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: ME z ładowarką EV (Ł), `crm/szablony/umowa_me_ev.pdf`.

Plik źródłowy wzoru: `Umowa ME + Ł ProEnergy - 06.10.2026.pdf` (ostateczny wzór z
06.10.2026, b69). 19 stron, A4 596x842 pt.

POMIAR: 2026-10-10, od zera, narzędziem `ops/narzedzia/umowa-mapa-pomiar.py` (repo
`proenergy-crm-ops`, issue ops#235) z deklaracją `ops/narzedzia/deklaracje/umowa_me_ev.py`.
Narzędzie czyta `pdftotext -bbox-layout` i `pdfminer.six` tego pliku i drukuje gotowe krotki
`Pole(...)`; żadna wartość nie jest skopiowana z innej mapy ani wyliczona ręcznie.
Konwencje układu współrzędnych i offsetów: nagłówek `crm/volteo_umowa_mapa.py` oraz docstring
`crm/volteo_umowa_mapa_pv2.py` (`y_reportlab = 842 - y_od_gory`; tekst na kresce
`x = xMin + 3`, `y = 842 - yMax + 2.5`; kratka 15x15 `y = 842 - yMax + 3.0`, mała 10x10 `+2.0`
i `rozmiar=8.0`; komórka tabeli `x` = pionowa kreska + 6).

POLITYKA (jak w `crm/volteo_umowa_mapa_pv.py`): podpis Wykonawcy drukuje się w umowie głównej
oraz w Załącznikach 1 i 2; w Załącznikach 3, 4, RODO i pełnomocnictwie jest tylko linia
Zamawiającego. `klient_imie_nazwisko` drukuje się w komparycji i w pełnomocnictwie.

STRONY BEZ POZYCJI (indeksy 0-based) i powód:
- 4: ciąg dalszy spisu załączników (bez rubryk).
- 8: Załącznik 5 (RODO), treść bez rubryk (podpis dopiero na stronie 10, indeks 9).
- 10: Załącznik 6, pouczenie o odstąpieniu (tekst stały).
- 11: formularz odstąpienia, 12-17: protokoły odbioru i pomiarów (magazyn, ładowarka EV)
  oraz listy szkoleń i zdjęć: wypełnia je instalator i klient po montażu, generator
  nie drukuje tam niczego.

KLUCZE KONTEKSTU BEZ RUBRYKI WE WZORZE (wyjątki w testach): `ev_moc_kw` (Załącznik 2 ma tylko
rubrykę typu ładowarki), klucze PV (panele, moc PV, inwerter_szt, montaż, pokrycie, odgromowa,
ppoz, przekop, kabel), `klima_*`, `roz_*` (cechy spoza tego wzoru), klucze drugiego
Zamawiającego (wzór jednoosobowy).

OSOBLIWOŚCI WZORU: opcje finansowania to "Kredyt 100%" / "Kredyt z wkładem własnym" / "Przelew",
mapowane 1:1 na `fin_kredyt_100` / `fin_kredyt_wklad` / `fin_gotowka`. Pierwsza strona ma jedną
tabelę komparycji. Załącznik 1 jest arkuszem magazynu z inwerterem hybrydowym, sekcją istniejącej
instalacji PV (`ist_pv_*`) i rubrykami "Dodatkowe moduły (ilość)" oraz "Dodatkowe moduły wraz z
mikroinwerterem (ilość)" (`dod_panele_szt`, `dod_panele_mikro_szt`). Załącznik 2 ma jedną rubrykę
(typ ładowarki EV). Strona z Załącznikami 3 i 4 ma dwie linie Zamawiającego: `n=0` wyżej,
`n=1` niżej.

BEZPIECZNIK ZMIANY SZABLONU: mapa obowiązuje WYŁĄCZNIE dla pliku o sumie `SHA256_SZABLONU_MEEV`;
generator odmawia renderu przy niezgodności.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_MEEV: str = "b486ac44b9bb9b91e67c44b9ccc3cbaeb7609c51d9a1b735f0002a8bd3d42bec"
"""SHA-256 pliku `crm/szablony/umowa_me_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_MEEV: int = 19
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

# Strona 1: komparycja (jedna tabela Zamawiającego, komórki), numer umowy, data zawarcia, adres montażu, rodzaj budynku. Bez drugiego Zamawiającego (wzór jednoosobowy).
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 646.71, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 622.24, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 597.76, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 573.29, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 548.81, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 715.58, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 320.51, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 276.66, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 256.82, "kratka", wyrownanie="srodek"),
)

# Strona 2: §2 wynagrodzenie netto/brutto i opcje finansowania. Trzecia kratka wzoru to "Przelew" i mapuje się na istniejący klucz `fin_gotowka` (etykieta wzoru, literał bazy bez zmian).
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
)

# Strona 3: §3 ust. 1 lit. g, powierzchnia użytkowa budynku (dwie kratki i metraż).
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 703.93, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 703.42, "tekst", maks_szerokosc=66.27),
)

# Strona 4: podpisy umowy głównej (Zamawiający i Wykonawca).
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 152.7, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 152.7, "tekst", maks_szerokosc=155.22),
)

# Strona 6: Załącznik 1, arkusz ustaleń montażowych magazynu energii (inwerter hybrydowy, bateria, internet, moc przyłączeniowa, fazy, sekcja istniejącej PV, opcje dodatkowe: dodatkowe moduły i moduły z mikroinwerterem), podpisy obu stron.
_STRONA_6: tuple[Pole, ...] = (
	Pole("inwerter_producent_model", 5, 205.01, 708.11, "tekst", maks_szerokosc=244.17),
	Pole("inwerter_moc_kw", 5, 229.43, 690.86, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_gwarancja_lat", 5, 250.57, 673.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_producent_model", 5, 191.13, 639.11, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 5, 153.31, 621.86, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 5, 293.9, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 5, 444.49, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 5, 272.24, 587.37, "tekst", maks_szerokosc=57.93),
	Pole("bateria_gwarancja_lat", 5, 236.69, 570.12, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 5, 118.95, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 5, 173.93, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 5, 251.14, 531.44, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 5, 229.43, 509.75, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 5, 121.72, 488.32, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 5, 157.83, 488.32, "kratka", wyrownanie="srodek"),
	Pole("ist_pv_moc_inwertera_kw", 5, 222.76, 426.95, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 5, 232.76, 409.71, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 5, 170.01, 392.46, "tekst", maks_szerokosc=155.22),
	Pole("dod_panele_szt", 5, 195.0, 331.51, "tekst", maks_szerokosc=57.93),
	Pole("dod_panele_mikro_szt", 5, 303.3, 314.26, "tekst", maks_szerokosc=55.16),
	Pole("podpis_zamawiajacy", 5, 75.0, 191.8, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 191.8, "tekst", maks_szerokosc=155.22),
)

# Strona 7: Załącznik 2, arkusz ustaleń montażowych ładowarki EV: tylko typ ładowarki (moc nie ma rubryki), podpisy obu stron.
_STRONA_7: tuple[Pole, ...] = (
	Pole("ev_nazwa", 6, 157.41, 711.56, "tekst", maks_szerokosc=244.17),
	Pole("podpis_zamawiajacy", 6, 75.0, 635.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 6, 363.0, 635.66, "tekst", maks_szerokosc=155.22),
)

# Strona 8: Załącznik 3 (zgody) i Załącznik 4 (realizacja przed odstąpieniem): trzy kratki 10x10 i dwie linie Zamawiającego (`n=0` wyżej pod Zał. 3, `n=1` niżej pod Zał. 4).
_STRONA_8: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 7, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 7, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 7, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 7, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# Strona 10: koniec Załącznika 5 (RODO), data i podpis.
_STRONA_10: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 9, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

# Strona 19: Załącznik 9, pełnomocnictwo (data, dane mocodawcy, podpis Zamawiającego).
_STRONA_19: tuple[Pole, ...] = (
	Pole("data_zawarcia", 18, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 18, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 18, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 18, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 18, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_MEEV: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_3,
	*_STRONA_4,
	*_STRONA_6,
	*_STRONA_7,
	*_STRONA_8,
	*_STRONA_10,
	*_STRONA_19,
)
"""Pełna mapa wzoru ME_EV (suma stałych `_STRONA_n`), zmierzona od zera 2026-10-10."""
