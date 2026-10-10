# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: PV + ME z ładowarką EV (Ł), `crm/szablony/umowa_pv_me_ev.pdf`.

Plik źródłowy wzoru: `Umowa PV + ME + Ł ProEnergy - 06.10.2026.pdf` (ostateczny wzór z
06.10.2026, b69). 22 strony, A4 596x842 pt.

POMIAR: 2026-10-10, od zera, narzędziem `ops/narzedzia/umowa-mapa-pomiar.py` (repo
`proenergy-crm-ops`, issue ops#235) z deklaracją `ops/narzedzia/deklaracje/umowa_pv_me_ev.py`.
Narzędzie czyta `pdftotext -bbox-layout` i `pdfminer.six` tego pliku i drukuje gotowe krotki
`Pole(...)`; żadna wartość nie jest skopiowana z innej mapy ani wyliczona ręcznie.
Konwencje układu współrzędnych i offsetów: nagłówek `crm/volteo_umowa_mapa.py` oraz docstring
`crm/volteo_umowa_mapa_pv2.py` (`y_reportlab = 842 - y_od_gory`; tekst na kresce
`x = xMin + 3`, `y = 842 - yMax + 2.5`; kratka 15x15 `y = 842 - yMax + 3.0`, mała 10x10 `+2.0`
i `rozmiar=8.0`; komórka tabeli `x` = pionowa kreska + 6).

POLITYKA (jak w `crm/volteo_umowa_mapa_pv.py`): podpis Wykonawcy drukuje się w umowie głównej
oraz w Załącznikach 1a, 1b i 2; w Załącznikach 3, 4, RODO i pełnomocnictwie jest tylko linia
Zamawiającego. `klient_imie_nazwisko` drukuje się w komparycji i w pełnomocnictwie.

STRONY BEZ POZYCJI (indeksy 0-based) i powód:
- 4: spis załączników.
- 9: Załącznik 5 (RODO), treść bez rubryk (podpis dopiero na stronie 10).
- 11: Załącznik 6, pouczenie o odstąpieniu (tekst stały).
- 12: formularz odstąpienia, 13-20: protokoły odbioru i pomiarów (PV, magazyn, ładowarka
  EV) oraz listy szkoleń i zdjęć: wypełnia je instalator i klient po montażu, generator
  nie drukuje tam niczego.

KLUCZE KONTEKSTU BEZ RUBRYKI WE WZORZE (wyjątki w testach): `ev_moc_kw` (Załącznik 2 ma tylko
rubrykę typu ładowarki), `klima_*`, `dod_panele_*`, `roz_*` (cechy spoza tego wzoru), klucze
drugiego Zamawiającego (wzór jednoosobowy).

OSOBLIWOŚCI WZORU: opcje finansowania to "Kredyt 100%" / "Kredyt z wkładem własnym" / "Przelew",
mapowane 1:1 na `fin_kredyt_100` / `fin_kredyt_wklad` / `fin_gotowka`. Pierwsza strona ma jedną
tabelę komparycji. Załącznik 1b zawiera sekcję istniejącej instalacji PV (`ist_pv_*`), a
Załącznik 1a nie ma pól istniejącej instalacji.

BEZPIECZNIK ZMIANY SZABLONU: mapa obowiązuje WYŁĄCZNIE dla pliku o sumie `SHA256_SZABLONU_PVMEEV`;
generator odmawia renderu przy niezgodności.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVMEEV: str = "645bca70bce4046eb185d5d4d3372bc61c29a83e1258d263625d219a00e3c119"
"""SHA-256 pliku `crm/szablony/umowa_pv_me_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PVMEEV: int = 22
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

# Strona 1: komparycja (jedna tabela Zamawiającego, komórki), numer umowy, data zawarcia, adres montażu, rodzaj budynku. Bez drugiego Zamawiającego (wzór jednoosobowy).
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 658.48, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 634.01, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 609.53, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 585.06, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 560.58, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 206.36, 721.51, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 697.43, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 331.4, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 287.55, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 267.72, "kratka", wyrownanie="srodek"),
)

# Strona 2: §2 wynagrodzenie netto/brutto i opcje finansowania. Trzecia kratka wzoru to "Przelew" i mapuje się na istniejący klucz `fin_gotowka` (etykieta wzoru, literał bazy bez zmian).
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 715.33, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 688.88, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 618.58, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 598.75, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 556.64, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 530.2, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 512.79, "kratka", wyrownanie="srodek"),
)

# Strona 3: § 3 ust. 1 lit. g, powierzchnia użytkowa budynku.
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 662.25, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 662.25, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 661.74, "tekst", maks_szerokosc=66.27),
)

# Strona 4: podpisy umowy głównej (Zamawiający i Wykonawca).
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 94.25, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 94.25, "tekst", maks_szerokosc=155.22),
)

# Strona 6: Załącznik 1a (instalacja fotowoltaiczna): moduły, inwerter, warunki instalacyjne, opcje dodatkowe, podpisy Zamawiającego i Wykonawcy.
_STRONA_6: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 5, 223.9, 715.33, "tekst", maks_szerokosc=55.16),
	Pole("panel_szt", 5, 381.7, 715.33, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 5, 186.09, 698.08, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 5, 280.02, 680.83, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 5, 249.46, 663.58, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 5, 183.31, 629.09, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 5, 174.42, 611.84, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_producent_model", 5, 205.01, 594.59, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 5, 250.57, 577.34, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 5, 118.95, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 5, 173.93, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 5, 251.14, 521.42, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 5, 229.43, 499.72, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 5, 121.72, 478.29, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 5, 157.83, 478.29, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 5, 157.28, 452.42, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 5, 213.37, 452.42, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 5, 268.9, 430.73, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 5, 182.29, 409.3, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 5, 228.76, 409.3, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 5, 398.41, 348.93, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 5, 444.89, 348.93, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 5, 165.06, 323.06, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 5, 222.03, 322.55, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 5, 281.0, 323.06, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 5, 161.18, 297.18, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 5, 218.15, 296.67, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 5, 277.12, 297.18, "kratka", wyrownanie="srodek"),
	Pole("podpis_zamawiajacy", 5, 75.0, 170.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 170.28, "tekst", maks_szerokosc=155.22),
)

# Strona 7: Załącznik 1b (magazyn energii): bateria oraz sekcja "w przypadku posiadania instalacji fotowoltaicznej" (klucze `ist_pv_*`), podpisy Zamawiającego i Wykonawcy.
_STRONA_7: tuple[Pole, ...] = (
	Pole("bateria_producent_model", 6, 191.13, 715.33, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 6, 153.31, 698.08, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 6, 293.9, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 6, 444.49, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 6, 272.24, 663.58, "tekst", maks_szerokosc=55.16),
	Pole("bateria_gwarancja_lat", 6, 236.69, 646.33, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_inwertera_kw", 6, 167.2, 572.17, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 6, 232.76, 554.92, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 6, 170.01, 537.67, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 6, 75.0, 446.25, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 6, 363.0, 446.25, "tekst", maks_szerokosc=155.22),
)

# Strona 8: Załącznik 2 (ładowarka EV): jedyna rubryka to "Typ ładowarki EV" (`ev_nazwa`); `ev_moc_kw` nie ma rubryki we wzorze. Podpisy Zamawiającego i Wykonawcy.
_STRONA_8: tuple[Pole, ...] = (
	Pole("ev_nazwa", 7, 157.41, 711.56, "tekst", maks_szerokosc=244.17),
	Pole("podpis_zamawiajacy", 7, 75.0, 635.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 7, 363.0, 635.66, "tekst", maks_szerokosc=155.22),
)

# Strona 9: Załącznik 3 (zgody na kontakt i promocję) i Załącznik 4 (realizacja przed upływem terminu na odstąpienie), każdy z własną linią podpisu samego Zamawiającego.
_STRONA_9: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 8, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 8, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 8, 77.0, 261.35, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 8, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 8, 75.0, 115.68, "tekst", maks_szerokosc=155.22),
)

# Strona 11: koniec Załącznika 5 (RODO), linia "data i podpis" Zamawiającego (`rodo_data_imie_nazwisko`).
_STRONA_11: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 10, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

# Strona 22: Załącznik 10 (pełnomocnictwo OSD). Linia podpisu Mocodawcy (Zamawiającego) w prawej kolumnie, tylko linia Zamawiającego. `data_zawarcia` reużyta w "udzielone w dniu".
_STRONA_22: tuple[Pole, ...] = (
	Pole("data_zawarcia", 21, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 21, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 21, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 21, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 21, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PVMEEV: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_3,
	*_STRONA_4,
	*_STRONA_6,
	*_STRONA_7,
	*_STRONA_8,
	*_STRONA_9,
	*_STRONA_11,
	*_STRONA_22,
)
"""Zmierzona mapa (77 pozycji)."""
