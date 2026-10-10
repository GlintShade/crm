# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF, wariant
wylacznie fotowoltaiczny, jedna osoba (bez magazynu energii i bez dodatkow),
`crm/szablony/umowa_pv.pdf` (zrodlo: "Umowa PV ProEnergy - 28.07.2026-2.pdf",
14 stron, A4 596x842 pt).

POMIAR: 2026-10-10 (b69, issue ops#239, chunk U2a), OD ZERA na tym pliku
narzedziem `ops/narzedzia/umowa-mapa-pomiar.py` w repo `proenergy-crm-ops` z
deklaracja `ops/narzedzia/deklaracje/umowa_pv.py` (kotwice tekstowe i podpisowe
rozwiazywane z `pdftotext -bbox-layout`, pionowe kreski tabeli komparycji z
`pdfminer.six` `LTLine`). Zadna wartosc nie jest przepisana z poprzedniej wersji
wzoru ani z map siostrzanych; poprzednia zawartosc tego modulu zostala w calosci
zastapiona.

UKLAD WSPOLRZEDNYCH: `pdftotext -bbox` liczy y OD GORY, reportlab OD DOLU:
`y = 842 - y_od_gory`. Tekst na kresce: x = xMin(kreski) + 3, y = 842 -
yMax(kreski) + 2.5, maks_szerokosc = szerokosc(kreski) - 6. Kratka: x = srodek
glifu, y = 842 - yMax(glifu) + 3.0; mala kratka (10x10 pt, Zal. 2/3): offset
+2.0 i rozmiar 8.0. Komorka tabeli: x = kreska dzielaca kolumny + 6, y = 842 -
yMax(etykiety), maks_szerokosc = (prawa krawedz - 3) - x. Szczegoly konwencji:
naglowek `crm/volteo_umowa_mapa.py` i docstring narzedzia.

POLITYKA PL (czego NIE drukujemy): Zalacznik nr 5 (pouczenie) i wzor formularza
odstapienia (str. 9 i 10) wypelnia klient tylko przy faktycznym odstapieniu;
Zalacznik nr 6 (protokol odbioru, str. 11), lista instalatora (str. 12) i protokol
pomiarow (str. 13) wypelnia instalator po montazu. Podpis Wykonawcy drukuje sie
w umowie glownej (str. 4) i Zalaczniku 1 (str. 5); w Zal. 2/3, RODO i
pelnomocnictwie jest tylko linia Zamawiajacego.

STRONY BEZ POZYCJI (indeksy 0-based): 2 (§3 cd., §4, §5, statyczne klauzule), 6
(poczatek klauzuli RODO), 8 (pouczenie o odstapieniu), 9 (wzor formularza
odstapienia), 10 (protokol odbioru), 11 (lista instalatora), 12 (protokol
pomiarow).

OSOBLIWOSCI WZORU: jedna osoba (brak kluczy klient2_* i podpis_zamawiajacy_2);
wzor nie ma rubryk dodatkow (klima, ladowarka EV, panele dodatkowe, rozbudowa),
wiec ich klucze kontekstu nie maja pozycji (patrz wyjatki w testach). Wynagrodzenie
netto/brutto stoi na str. 1, a opcje finansowania na str. 2 ("Kredyt 100%" /
"Kredyt z wkladem" / "Przelew").

BEZPIECZNIK: mapa obowiazuje WYLACZNIE dla pliku o SHA-256 `SHA256_SZABLONU_PV`;
generator odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PV: str = "1dd2cf9a810d71a6d190fb1afe0e4b37631bbc3cd7b72d9e6efa0bc8e2100f7b"
"""SHA-256 pliku `crm/szablony/umowa_pv.pdf` (`shasum -a 256`, 2026-10-10)."""

LICZBA_STRON_PV: int = 14
"""Liczba stron oryginalu, zgodna z `pdfinfo`."""

# Strona 1 (indeks 0): komparycja (numer umowy, data zawarcia, tabela danych
# klienta 5 wierszy x 2 kolumny, adres montazu, typ budynku) oraz §2 ust. 1
# (wynagrodzenie netto i brutto, dwie kreski na dole strony). Komorki tabeli:
# x = pionowa kreska dzielaca kolumny (pdfminer LTLine) + 6 pt, y = dol etykiety
# wiersza, maks_szerokosc = prawa krawedz tabeli - 3 pt - x.
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 110.25, 353.57, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 289.88, "kratka", wyrownanie="srodek"),
	Pole("wynagrodzenie_netto", 0, 113.78, 102.31, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 0, 113.78, 75.87, "tekst", maks_szerokosc=155.22),
)

# Strona 2 (indeks 1): §2 ust. 2 (opcje finansowania "Kredyt 100%" / "Kredyt z
# wkladem wlasnym" / "Przelew") i §3 ust. 1 lit. f (powierzchnia uzytkowa).
# Kratki mapuja 1:1 na istniejace klucze: fin_kredyt_100 = Kredyt 100%,
# fin_kredyt_wklad = Kredyt z wkladem (z dwiema kreskami wklad wlasny / kredyt),
# fin_gotowka = Przelew (zdanie ust. 3 "gotowka/przelew" zostaje we wzorze).
_STRONA_2: tuple[Pole, ...] = (
	Pole("fin_kredyt_100", 1, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 684.09, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 641.99, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 615.54, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 598.13, "kratka", wyrownanie="srodek"),
	Pole("pow_do_300", 1, 115.5, 168.36, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 1, 242.73, 168.36, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 1, 379.34, 167.85, "tekst", maks_szerokosc=66.27),
)

# Strona 4 (indeks 3): podpisy umowy glownej, jedna linia Zamawiajacego i jedna
# Wykonawcy (osobne kolumny po wspolrzednej x, nie po kolejnosci w strumieniu).
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 681.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 681.66, "tekst", maks_szerokosc=155.22),
)

# Strona 5 (indeks 4): Zalacznik nr 1, arkusz ustalen montazowych PV (jedyny
# arkusz tego wzoru, bez 1a/1b), razem z sekcja istniejacej instalacji PV oraz
# podpisami Zamawiajacego i Wykonawcy pod arkuszem. Dwie etykiety "Moc
# inwertera" rozroznione sekcja (nowa instalacja vs istniejaca), nie etykieta.
_STRONA_5: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 4, 223.9, 708.11, "tekst", maks_szerokosc=55.16),
	Pole("panel_szt", 4, 381.7, 708.11, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 4, 186.09, 690.86, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 4, 280.02, 673.61, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 4, 249.46, 656.36, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 4, 183.31, 621.86, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 4, 174.42, 604.61, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_producent_model", 4, 205.01, 587.37, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 570.12, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 514.19, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 514.19, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 514.19, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 492.5, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 471.07, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 471.07, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 4, 157.28, 445.2, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 4, 213.37, 445.2, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 4, 268.9, 423.5, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 4, 182.29, 402.08, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 4, 228.76, 402.08, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 4, 398.41, 358.95, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 444.89, 358.95, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 4, 165.06, 333.08, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 4, 222.03, 332.57, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 4, 281.0, 333.08, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 4, 161.18, 307.21, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 4, 218.15, 306.7, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 4, 277.12, 307.21, "kratka", wyrownanie="srodek"),
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 255.04, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 237.8, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 220.55, "tekst", maks_szerokosc=158.0),
	Pole("podpis_zamawiajacy", 4, 75.0, 98.08, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 98.08, "tekst", maks_szerokosc=155.22),
)

# Strona 6 (indeks 5): Zalacznik nr 2 (zgoda telefon, zgoda promocja) i
# Zalacznik nr 3 (realizacja przed terminem odstapienia). Kratki 10x10 pt (offset
# +2.0, rozmiar 8). Pod Zal. 2 i Zal. 3 tylko linia Zamawiajacego, bez Wykonawcy.
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# Strona 8 (indeks 7): koniec Zalacznika nr 4 (klauzula RODO), linia "data i
# podpis" klienta (klucz rodo_data_imie_nazwisko).
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 562.64, "tekst", maks_szerokosc=155.22),
)

# Strona 14 (indeks 13): Zalacznik nr 7, pelnomocnictwo OSD. "udzielone w dniu"
# reuzywa data_zawarcia; podpis Mocodawcy stoi w prawej kolumnie (klucz
# Zamawiajacego), bez Wykonawcy.
_STRONA_14: tuple[Pole, ...] = (
	Pole("data_zawarcia", 13, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 13, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 13, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 13, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 13, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PV: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_8
	+ _STRONA_14
)
"""Pelna mapa dla `crm/szablony/umowa_pv.pdf`. Jeden klucz kontekstu moze wystapic
wielokrotnie (na kazdej stronie, gdzie jest drukowany)."""


def pozycje_dla_pv(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_PV` dla danego klucza kontekstu, w kolejnosci mapy."""
	return tuple(pole for pole in MAPA_PV if pole.klucz == klucz)


def klucze_w_mapie_pv() -> frozenset[str]:
	"""Zbior unikalnych kluczy kontekstu obecnych w `MAPA_PV`."""
	return frozenset(pole.klucz for pole in MAPA_PV)
