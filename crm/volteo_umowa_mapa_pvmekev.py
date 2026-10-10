# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: PV + ME z klimatyzacją i ładowarką EV (K + Ł), `crm/szablony/umowa_pv_me_k_ev.pdf`.

Plik źródłowy wzoru: `Umowa PV + ME + K + Ł ProEnergy - 06.10.2026.pdf` (ostateczny
wzór z 06.10.2026, b69, issue ops#244). SHA-256 pliku: `SHA256_SZABLONU_PVMEKEV`.

ORYGINALNOŚĆ POMIARU: wszystkie współrzędne zmierzono OD ZERA z tego jednego pliku
narzędziem `proenergy-crm-ops/ops/narzedzia/umowa-mapa-pomiar.py` (deklaracja
pól: `ops/narzedzia/deklaracje/umowa_pv_me_k_ev.py`), dnia 2026-10-10. Żadna wartość
nie jest przepisana z map siostrzanych ani ze starej wersji wzoru (reeksport z
Google Docs przesuwa nawet niezmienione strony, lekcja b62). Konwencje (układ
`y_reportlab = 842 - y_od_gory`, offsety tekstu na kresce, kratek, komórek tabeli)
opisano w nagłówku `crm/volteo_umowa_mapa.py` i w docstringu narzędzia.

POLITYKA (jak w mapie PV): podpis Wykonawcy drukuje się w umowie głównej i w
Załącznikach 1a, 1b, 2 i 3 (klimatyzacja i ładowarka EV mają własne bloki podpisów
obu stron); w Załącznikach 4/5 (zgody), w klauzuli RODO i w pełnomocnictwie tylko
linia Zamawiającego; `data_zawarcia` jest reużywana w "udzielone w dniu"
pełnomocnictwa; imię i nazwisko klienta drukuje się w komparycji i w pełnomocnictwie.

STRONY BEZ POZYCJI (indeksy 0-based, celowo): 3 (treść paragrafów: koniec §6, §7
klimatyzacja, §8 ładowarka EV, początek §9), 10 (treść klauzuli RODO), 12
(pouczenie o odstąpieniu), 13 (formularz odstąpienia), 14-23 (protokoły odbioru i
pomiarów PV, magazynu, klimatyzacji i ładowarki EV: wypełnia je instalator i klient
po montażu, generator nie drukuje nic z góry).

KLUCZE BEZ RUBRYKI W TYM WZORZE (wyjątki w testach): `klima_model` i `ev_moc_kw`
(wzór ma tylko rodzaj i moc klimatyzacji oraz sam typ ładowarki EV), klucze
paneli dodatkowych, rozbudowy (`roz_*`) oraz drugiego Zamawiającego (wzór
jednoosobowy).
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVMEKEV: str = "4bad7ce370d8398a581690ab1d7d2865a4cc3645705355e8fb8ff35bec3a91e1"
"""SHA-256 pliku `crm/szablony/umowa_pv_me_k_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PVMEKEV: int = 25
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

# ---------------------------------------------------------------------------
# Strona 1: komparycja. Tabela danych klienta (jedna, 5 wierszy; komórki: x z
# pionowej kreski dzielącej kolumny), numer umowy i data zawarcia (kreski przy
# etykietach), adres miejsca montażu (trzecia kreska strony), rodzaj budynku
# (dwie kratki).
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Strona 2: §2 Wynagrodzenie netto/brutto, trzy kratki płatności (Kredyt 100%
# / Kredyt z wkładem własnym / Przelew), wkład własny i kwota kredytu. Trzecia
# kratka "Przelew" niesie klucz `fin_gotowka` (literał bazy `Gotówka 100%`,
# etykieta wzoru to przelew).
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
# Strona 3: §3 ust. 1 lit. g, powierzchnia użytkowa budynku (dwie kratki: do 300
# m2 / powyżej 300 m2, oraz kreska z wartością powierzchni).
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 662.25, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 240.5, 662.25, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 377.66, 661.74, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 5: podpisy umowy głównej (lewa kolumna Zamawiający, prawa Wykonawca).
# Kreski podpisów to jedyne kreski pod blokiem "Zamawiający / Wykonawca".
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 4, 75.0, 585.09, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 585.09, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6: Załącznik 1a, arkusz ustaleń montażowych: instalacja fotowoltaiczna
# (moduły, inwerter, warunki instalacyjne, opcje dodatkowe) i podpisy obu stron.
# Podpisy wymagają n=-1: pierwsze kreski strony to rubryki, nie podpisy.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Strona 7: Załącznik 1b, arkusz ustaleń montażowych: magazyn energii (bateria,
# pojemności) oraz dane istniejącej instalacji PV, i podpisy obu stron.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Strona 8: Załącznik 2, arkusz ustaleń montażowych: klimatyzacja (rodzaj i moc;
# wzór nie ma rubryki modelu) i podpisy obu stron.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("klima_rodzaj", 7, 165.55, 697.01, "tekst", maks_szerokosc=244.17),
	Pole("klima_moc_kw", 7, 177.18, 672.86, "tekst", maks_szerokosc=244.17),
	Pole("podpis_zamawiajacy", 7, 75.0, 611.92, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 7, 363.0, 611.92, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 9: Załącznik 3, arkusz ustaleń montażowych: ładowarka EV (tylko typ,
# wzór nie ma rubryki mocy) i podpisy obu stron.
# ---------------------------------------------------------------------------
_STRONA_9: tuple[Pole, ...] = (
	Pole("ev_nazwa", 8, 157.41, 711.56, "tekst", maks_szerokosc=244.17),
	Pole("podpis_zamawiajacy", 8, 75.0, 635.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 8, 363.0, 635.66, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 10: Załącznik 4 (zgody: kontakt telefoniczny, działania promocyjne) i
# Załącznik 5 (realizacja przed upływem terminu odstąpienia) na jednej stronie;
# małe kratki 10x10 pt. Dwa podpisy samego Zamawiającego: n=0 pod Zał. 4
# (wyżej), n=1 pod Zał. 5 (niżej).
# ---------------------------------------------------------------------------
_STRONA_10: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 9, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 9, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 9, 77.0, 261.35, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 9, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 9, 75.0, 115.68, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 12: koniec Załącznika 6 (klauzula RODO): data i podpis Zamawiającego
# (linia "data i podpis").
# ---------------------------------------------------------------------------
_STRONA_12: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 11, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 25: Załącznik 12 (pełnomocnictwo OSD): data udzielenia, dane
# Mocodawcy i jego podpis (prawa kolumna; tylko linia Zamawiającego).
# ---------------------------------------------------------------------------
_STRONA_25: tuple[Pole, ...] = (
	Pole("data_zawarcia", 24, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 24, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 24, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 24, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 24, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PVMEKEV: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_3,
	*_STRONA_5,
	*_STRONA_6,
	*_STRONA_7,
	*_STRONA_8,
	*_STRONA_9,
	*_STRONA_10,
	*_STRONA_12,
	*_STRONA_25,
)
"""Wszystkie pozycje mapy wzoru PVME_K_EV, strona po stronie."""
