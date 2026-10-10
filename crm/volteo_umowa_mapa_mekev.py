# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: ME z klimatyzacją i ładowarką EV (K + Ł), `crm/szablony/umowa_me_k_ev.pdf`.

Plik źródłowy wzoru: `Umowa ME + K + Ł ProEnergy - 06.10.2026-2.pdf` (ostateczny wzór z
06.10.2026, b69). 22 strony, A4 596x842 pt.

POMIAR: 2026-10-10, od zera, narzędziem `ops/narzedzia/umowa-mapa-pomiar.py` (repo
`proenergy-crm-ops`, issue ops#235) z deklaracją `ops/narzedzia/deklaracje/umowa_me_k_ev.py`.
Narzędzie czyta `pdftotext -bbox-layout` i `pdfminer.six` tego pliku i drukuje gotowe krotki
`Pole(...)`; żadna wartość nie jest skopiowana z innej mapy ani wyliczona ręcznie.
Konwencje układu współrzędnych i offsetów: nagłówek `crm/volteo_umowa_mapa.py` oraz docstring
`crm/volteo_umowa_mapa_pv2.py` (`y_reportlab = 842 - y_od_gory`; tekst na kresce
`x = xMin + 3`, `y = 842 - yMax + 2.5`; kratka 15x15 `y = 842 - yMax + 3.0`, mała 10x10 `+2.0`
i `rozmiar=8.0`; komórka tabeli `x` = pionowa kreska + 6).

POLITYKA (jak w `crm/volteo_umowa_mapa_pv.py`): podpis Wykonawcy drukuje się w umowie głównej
oraz w Załącznikach 1, 2 i 3 (arkusze montażowe: magazyn, klimatyzacja, ładowarka EV); w
Załącznikach 4, 5, RODO i pełnomocnictwie jest tylko linia Zamawiającego.
`klient_imie_nazwisko` drukuje się w komparycji i w pełnomocnictwie. `data_zawarcia` wraca w
"udzielone w dniu" pełnomocnictwa.

STRONY BEZ POZYCJI (indeksy 0-based) i powód:
- 3: ciąg dalszy treści umowy (klimatyzacja, ładowarka EV, postanowienia końcowe), bez rubryk.
- 9: Załącznik 6 (RODO), treść bez rubryk (podpis dopiero na stronie 10).
- 11: Załącznik 7, pouczenie o odstąpieniu (tekst stały).
- 12: formularz odstąpienia; 13-16: protokół odbioru magazynu energii wraz z listami szkoleń i
  zdjęć oraz protokół pomiarów; 17-18: protokół odbioru klimatyzacji; 19-20: protokół odbioru
  ładowarki EV. Protokoły wypełnia instalator i klient po montażu, generator nie drukuje tam
  niczego (w tym żadnych danych instalatora i klienta).

KLUCZE KONTEKSTU BEZ RUBRYKI WE WZORZE (wyjątki w testach): `klima_model` i `ev_moc_kw`
(Załącznik 2 ma tylko rodzaj i moc klimatyzacji, Załącznik 3 tylko typ ładowarki), klucze PV
(panele, inwerter PV, montaż dachowy, odgromowa, ppoż, przekop, dodatkowy kabel), `roz_*`
(cecha spoza tego wzoru), klucze drugiego Zamawiającego (wzór jednoosobowy).

OSOBLIWOŚCI WZORU: opcje finansowania to "Kredyt 100%" / "Kredyt z wkładem własnym" / "Przelew",
mapowane 1:1 na `fin_kredyt_100` / `fin_kredyt_wklad` / `fin_gotowka`. Pierwsza strona ma jedną
tabelę komparycji. Podpisy załączników są na `n=-1` (jedna para linii na stronie), a na stronie
zgód (Zał. 4 i 5) dwie linie Zamawiającego: `n=0` wyżej, `n=1` niżej. Załącznik 1 niesie
sekcję istniejącej instalacji PV (`ist_pv_*`) oraz opcje dodatkowe (`dod_panele_szt`,
`dod_panele_mikro_szt`).

BEZPIECZNIK ZMIANY SZABLONU: mapa obowiązuje WYŁĄCZNIE dla pliku o sumie `SHA256_SZABLONU_MEKEV`;
generator odmawia renderu przy niezgodności.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_MEKEV: str = "0a5d5fe8cd19119d8320fd5079d6994d62b7306f0da324cef2364efbc1a7a1eb"
"""SHA-256 pliku `crm/szablony/umowa_me_k_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_MEKEV: int = 22
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
	Pole("wynagrodzenie_netto", 1, 113.78, 721.33, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 694.88, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 624.58, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 604.75, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 562.64, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 536.2, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 518.79, "kratka", wyrownanie="srodek"),
)

# Strona 3: §3 powierzchnia budynku (kratki do/ponad 300 m2 i wartość).
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 717.15, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 717.15, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 716.64, "tekst", maks_szerokosc=66.27),
)

# Strona 5: podpisy umowy głównej (Zamawiający i Wykonawca).
_STRONA_5: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 4, 75.0, 641.99, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 641.99, "tekst", maks_szerokosc=155.22),
)

# Strona 6: Załącznik 1 (arkusz magazynu energii): inwerter hybrydowy, bateria, internet, moc przyłączeniowa, fazy, istniejąca instalacja PV, opcje dodatkowe (moduły dodatkowe i z mikroinwerterem), podpisy obu stron.
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

# Strona 7: Załącznik 2 (klimatyzacja): rodzaj i moc, podpisy obu stron. Wzór nie ma rubryki modelu klimatyzacji.
_STRONA_7: tuple[Pole, ...] = (
	Pole("klima_rodzaj", 6, 165.55, 711.56, "tekst", maks_szerokosc=227.5),
	Pole("klima_moc_kw", 6, 177.18, 687.41, "tekst", maks_szerokosc=227.5),
	Pole("podpis_zamawiajacy", 6, 75.0, 624.16, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 6, 363.0, 624.16, "tekst", maks_szerokosc=155.22),
)

# Strona 8: Załącznik 3 (ładowarka EV): tylko typ ładowarki (moc nie ma rubryki), podpisy obu stron.
_STRONA_8: tuple[Pole, ...] = (
	Pole("ev_nazwa", 7, 157.41, 711.56, "tekst", maks_szerokosc=244.17),
	Pole("podpis_zamawiajacy", 7, 75.0, 635.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 7, 363.0, 635.66, "tekst", maks_szerokosc=155.22),
)

# Strona 9: Załącznik 4 (zgody, dwie kratki, linia podpisu Zamawiającego wyżej) i Załącznik 5 (realizacja przed odstąpieniem, kratka, druga linia podpisu Zamawiającego niżej). Tylko Zamawiający.
_STRONA_9: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 8, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 8, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 8, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 8, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 8, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# Strona 11: koniec Załącznika 6 (RODO): data i podpis Zamawiającego (klucz `rodo_data_imie_nazwisko`).
_STRONA_11: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 10, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

# Strona 22: Załącznik 11 (pełnomocnictwo): data udzielenia, dane Mocodawcy, podpis Zamawiającego (bez Wykonawcy).
_STRONA_22: tuple[Pole, ...] = (
	Pole("data_zawarcia", 21, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 21, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 21, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 21, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 21, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_MEKEV: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_3,
	*_STRONA_5,
	*_STRONA_6,
	*_STRONA_7,
	*_STRONA_8,
	*_STRONA_9,
	*_STRONA_11,
	*_STRONA_22,
)
