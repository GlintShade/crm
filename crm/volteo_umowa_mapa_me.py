# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF, wariant
magazyn energii, jedna osoba, z rubryka dodatkowych modulow PV,
`crm/szablony/umowa_me.pdf` (zrodlo: "Umowa ME ProEnergy - 06.10.2026-2.pdf",
16 stron, A4 596x842 pt).

POMIAR: 2026-10-10 (b69, issue ops#245, chunk U2g), OD ZERA na tym pliku
narzedziem `ops/narzedzia/umowa-mapa-pomiar.py` w repo `proenergy-crm-ops` z
deklaracja `ops/narzedzia/deklaracje/umowa_me.py` (kotwice tekstowe i podpisowe
rozwiazywane z `pdftotext -bbox-layout`, pionowe kreski tabeli komparycji z
`pdfminer.six` `LTLine`). Zadna wartosc nie jest przepisana z poprzedniej
(14-stronicowej) wersji wzoru ani z map siostrzanych; poprzednia zawartosc tego
modulu zostala w calosci zastapiona.

UKLAD WSPOLRZEDNYCH: `pdftotext -bbox` liczy y OD GORY, reportlab OD DOLU:
`y = 842 - y_od_gory`. Tekst na kresce: x = xMin(kreski) + 3, y = 842 -
yMax(kreski) + 2.5, maks_szerokosc = szerokosc(kreski) - 6. Kratka: x = srodek
glifu, y = 842 - yMax(glifu) + 3.0; mala kratka (10x10 pt, Zal. 2/3): offset
+2.0 i rozmiar 8.0. Komorka tabeli: x = kreska dzielaca kolumny + 6, y = 842 -
yMax(etykiety), maks_szerokosc = (prawa krawedz - 3) - x. Szczegoly konwencji:
naglowek `crm/volteo_umowa_mapa.py` i docstring narzedzia.

POLITYKA PL (czego NIE drukujemy): Zalacznik nr 5 (pouczenie, str. 9) i wzor
formularza odstapienia (str. 10) wypelnia klient tylko przy faktycznym
odstapieniu; Zalacznik nr 6 (protokol odbioru, str. 11-13) i protokol pomiarow
(str. 14) wypelnia instalator po montazu. Podpis Wykonawcy drukuje sie w umowie
glownej (str. 4) i Zalaczniku 1 (str. 5); w Zal. 2/3, RODO i pelnomocnictwie
jest tylko linia Zamawiajacego.

STRONY BEZ POZYCJI (indeksy 0-based): 8 (pouczenie o odstapieniu), 9 (formularz
odstapienia), 10 do 13 (protokol odbioru i protokol pomiarow), 15 (pusta strona,
tylko stopka). Strony 2 i 6 maja po jednej grupie pozycji (powierzchnia; podpis
Zal. 3), reszta ich tresci to statyczne klauzule.

OSOBLIWOSCI WZORU: jedna osoba (brak kluczy klient2_* i podpis_zamawiajacy_2);
wzor nie ma rubryk paneli PV, montazu dachowego, odgromowej, PPOZ, przekopu ani
kabla, wiec ich klucze kontekstu nie maja pozycji (patrz wyjatki w testach);
nie obsluguje klimy, ladowarki EV ani rozbudowy. Obsluguje WYLACZNIE cechy
`dod_panele`: Zal. 1 ma rubryki "Dodatkowe moduly (ilosc)" i "Dodatkowe moduly
wraz z mikrofalownikiem (ilosc)" (klucze dod_panele_szt, dod_panele_mikro_szt).
Wynagrodzenie netto/brutto stoi na str. 2 (nie 1), opcje finansowania tez na
str. 2 ("Kredyt 100%" / "Kredyt z wkladem" / "Przelew"). Tekst Zalacznika nr 3
przechodzi ze str. 6 na 7, wiec jego podpis lezy na str. 7 (indeks 6), a nie na
tej samej stronie co kratka. Zalacznik nr 4 (RODO) konczy sie na str. 8. Na
str. 5 dwie etykiety "Moc inwertera (kW)" (nowy inwerter i istniejaca instalacja
PV) rozroznione kolejnoscia, nie etykieta.

BEZPIECZNIK: mapa obowiazuje WYLACZNIE dla pliku o SHA-256 `SHA256_SZABLONU_ME`;
generator odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ME: str = "de2d526db3ea8a9f08daf1ecc94198d245c1c4530bb457a9ddbf2346b8ee3cf7"
"""SHA-256 pliku `crm/szablony/umowa_me.pdf` (`shasum -a 256`, 2026-10-10)."""

LICZBA_STRON_ME: int = 16
"""Liczba stron oryginalu, zgodna z `pdfinfo`."""

# Strona 1 (indeks 0): komparycja (numer umowy, data zawarcia, tabela danych
# klienta 5 wierszy x 2 kolumny), §1 ust. 1 adres miejsca montazu (kreska) i
# ust. 2 typ budynku. Komorki tabeli: x = pionowa kreska dzielaca kolumny
# (pdfminer LTLine) + 6 pt, y = dol etykiety wiersza, maks_szerokosc = prawa
# krawedz tabeli - 3 pt - x. Wynagrodzenie stoi dopiero na str. 2.
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 340.34, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 296.49, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 276.66, "kratka", wyrownanie="srodek"),
)

# Strona 2 (indeks 1): §2 ust. 1 wynagrodzenie netto i brutto (dwie kreski) oraz
# ust. 2 opcje finansowania "Kredyt 100%" / "Kredyt z wkladem wlasnym" (z
# kreskami wklad wlasny / kredyt) / "Przelew". Kratki mapuja 1:1:
# fin_kredyt_100, fin_kredyt_wklad, fin_gotowka (zdanie ust. 3 "gotowka/przelew"
# zostaje we wzorze).
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 694.88, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 668.43, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 598.13, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 578.3, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 536.2, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 509.75, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 492.34, "kratka", wyrownanie="srodek"),
)

# Strona 3 (indeks 2): §3 ust. 1 lit. g, powierzchnia uzytkowa budynku (dwie
# kratki w jednej linii i kreska m2).
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 690.7, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 690.7, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 690.19, "tekst", maks_szerokosc=66.27),
)

# Strona 4 (indeks 3): podpisy umowy glownej, jedna linia Zamawiajacego i jedna
# Wykonawcy (osobne kolumny po wspolrzednej x).
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 364.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 364.28, "tekst", maks_szerokosc=155.22),
)

# Strona 5 (indeks 4): Zalacznik nr 1, arkusz ustalen montazowych ME: inwerter,
# bateria (moc, pojemnosci, liczba, gwarancja), internet, moc przylaczeniowa,
# fazy, sekcja istniejacej instalacji PV (dwie etykiety "Moc inwertera (kW)"
# rozroznione kolejnoscia n=0/n=1), OPCJE DODATKOWE (dodatkowe moduly, moduly z
# mikrofalownikiem) oraz podpisy Zamawiajacego i Wykonawcy.
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
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 426.95, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 409.71, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 392.46, "tekst", maks_szerokosc=155.22),
	Pole("dod_panele_szt", 4, 195.0, 331.51, "tekst", maks_szerokosc=57.93),
	Pole("dod_panele_mikro_szt", 4, 306.09, 314.26, "tekst", maks_szerokosc=55.16),
	Pole("podpis_zamawiajacy", 4, 75.0, 191.8, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 191.8, "tekst", maks_szerokosc=155.22),
)

# Strona 6 (indeks 5): Zalacznik nr 2 (zgoda telefon, zgoda promocja) z linia
# Zamawiajacego oraz kratka Zalacznika nr 3 (realizacja przed terminem
# odstapienia). Kratki 10x10 pt (offset +2.0, rozmiar 8). Zal. 3 przechodzi na
# str. 7, gdzie stoi jego podpis.
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 642.2, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 602.53, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 192.59, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 522.97, "tekst", maks_szerokosc=155.22),
)

# Strona 7 (indeks 6): linia podpisu Zamawiajacego pod Zalacznikiem nr 3 (u gory
# strony, ciag dalszy Zal. 3 ze str. 6). Dalej zaczyna sie Zal. 4 (RODO) bez
# pozycji.
_STRONA_7: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 6, 75.0, 734.55, "tekst", maks_szerokosc=155.22),
)

# Strona 8 (indeks 7): koniec Zalacznika nr 4 (klauzula RODO), linia "data i
# podpis" klienta (klucz rodo_data_imie_nazwisko).
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 496.52, "tekst", maks_szerokosc=155.22),
)

# Strona 15 (indeks 14): Zalacznik nr 7, pelnomocnictwo OSD. "udzielone w dniu"
# reuzywa data_zawarcia; podpis Mocodawcy stoi w prawej kolumnie (klucz
# Zamawiajacego), bez Wykonawcy.
_STRONA_15: tuple[Pole, ...] = (
	Pole("data_zawarcia", 14, 292.01, 628.76, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 14, 171.13, 602.31, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 14, 336.75, 602.31, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 14, 110.01, 589.09, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 14, 365.05, 99.81, "tekst", maks_szerokosc=155.22),
)

MAPA_ME: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_7
	+ _STRONA_8
	+ _STRONA_15
)
"""Pelna mapa dla `crm/szablony/umowa_me.pdf`. Jeden klucz kontekstu moze wystapic
na kilku stronach albo kilka razy na jednej (podpisy, data_zawarcia)."""
