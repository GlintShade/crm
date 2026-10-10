# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: PV z klimatyzacja (K), `crm/szablony/umowa_pv_k.pdf`.

Plik zrodlowy wzoru: `Umowa PV + K ProEnergy - 06.10.2026-2.pdf` (ostateczny wzor
z 06.10.2026, b69), 17 stron A4 (596x842 pt), SHA-256 w `SHA256_SZABLONU_PVK`.

POMIAR OD ZERA, 2026-10-10 (chunk U2b, issue ops#240): kazda wartosc `MAPA_PVK`
pochodzi z narzedzia `ops/narzedzia/umowa-mapa-pomiar.py` (repo
`proenergy-crm-ops`) uruchomionego na TYM pliku z deklaracja
`ops/narzedzia/deklaracje/umowa_pv_k.py`: tekst i kreski z `pdftotext -bbox`,
pionowe kreski tabeli klienta i granulacja znakowa z `pdfminer.six`. Zadna
wspolrzedna nie jest przepisana z map siostrzanych ani ze starej mapy (reeksport
z Google Docs przesuwa nawet niezmienione strony). Konwencje: nagl. `volteo_umowa_mapa.py`
i docstring `volteo_umowa_mapa_pv2.py`: `y_reportlab = 842 - y_od_gory`; tekst na
kresce x = xMin + 3, y = 842 - yMax + 2.5, maks_szerokosc = szer. kreski - 6;
kratka x = srodek glifu, y = 842 - yMax + 3.0 (mala 10x10 pt: +2.0, rozmiar 8);
komorka tabeli x = pionowa kreska + 6; podpis: kolumna wg wspolrzednej x.

Strony BEZ pozycji (celowo, z powodu): idx 7 (RODO tresc), idx 9 (pouczenie o
odstapieniu), idx 10 (formularz odstapienia), idx 11-15 (protokol odbioru PV,
protokol pomiarow, protokol odbioru klimatyzacji): wypelnia je klient/instalator
po montazu, nie generator z gory. Podpis Wykonawcy drukuje sie w umowie glownej
i Zalacznikach 1 i 2, w Zal. 3/4, RODO i pelnomocnictwie tylko linia Zamawiajacego.

Osobliwosci wzoru: brak Zalacznikow 1a/1b (panele/bateria dodatkowe) i bloku
drugiego Zamawiajacego; Zalacznik 2 to klimatyzacja z DWIEMA rubrykami (rodzaj,
moc), bez modelu (klucz klima_model nie ma rubryki, patrz wyjatki w testach);
strony protokolow sa dwie dluzsze niz w PV (osobny protokol klimatyzacji).
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVK: str = "7b1dfbef6b78f61eb1d4e2502bdf09cedea3d8a98c7f816acaee3cfbe32e2e58"
"""SHA-256 pliku `crm/szablony/umowa_pv_k.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PVK: int = 17
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

_STRONA_1: tuple[Pole, ...] = (
	# Strona 1 (idx 0): komparycja (jedna tabela danych klienta), numer i data umowy, adres montazu (§1 ust. 1), typ budynku (§1 ust. 2) oraz kwota netto (§2 ust. 1, ostatnia tresc przed stopka). Kwota brutto spada na nastepna strone.
	Pole("klient_imie_nazwisko", 0, 177.5, 646.71, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 622.24, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 597.76, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 573.29, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 548.81, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 715.58, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 110.25, 373.4, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 329.55, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("wynagrodzenie_netto", 0, 113.78, 82.48, "tekst", maks_szerokosc=155.22),
)

_STRONA_2: tuple[Pole, ...] = (
	# Strona 2 (idx 1): kwota brutto, §2 ust. 2 opcje finansowania. Wzor drukuje kratki "Kredyt 100%" / "Kredyt z wkladem" / "Przelew", mapowane 1:1 na fin_kredyt_100 / fin_kredyt_wklad / fin_gotowka (kratka Przelew = literal bazy 'Gotowka 100%'). Zdanie o gotowce/przelewie jest stalym tekstem.
	Pole("wynagrodzenie_brutto", 1, 113.78, 747.78, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 677.48, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 657.64, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 615.54, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 589.09, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 571.69, "kratka", wyrownanie="srodek"),
)

_STRONA_3: tuple[Pole, ...] = (
	# Strona 3 (idx 2): §3 ust. 1 lit. g, powierzchnia uzytkowa budynku (do 300 m2 / ponad 300 m2 i ile). Lit. d (prawdziwosc danych), lit. f (sprawnosc istniejacej instalacji) i lokalizacja urzadzen przez Wykonawce (§1 ust. 3) to staly tekst bez rubryk.
	Pole("pow_do_300", 2, 115.5, 743.6, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 240.5, 743.6, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 377.66, 743.09, "tekst", maks_szerokosc=66.27),
)

_STRONA_4: tuple[Pole, ...] = (
	# Strona 4 (idx 3): podpisy umowy glownej, obie strony (Zamawiajacy lewa kolumna, Wykonawca prawa).
	Pole("podpis_zamawiajacy", 3, 75.0, 364.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 364.28, "tekst", maks_szerokosc=155.22),
)

_STRONA_5: tuple[Pole, ...] = (
	# Strona 5 (idx 4): Zalacznik 1, arkusz ustalen montazowych instalacji PV (dane modulow, inwertera, warunki instalacyjne, opcje dodatkowe, istniejaca instalacja PV) i podpisy obu stron.
	Pole("panel_moc_wp", 4, 223.9, 734.55, "tekst", maks_szerokosc=55.16),
	Pole("panel_szt", 4, 381.7, 734.55, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 4, 186.09, 717.3, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 4, 280.02, 700.06, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 4, 249.46, 682.81, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 4, 183.31, 648.31, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 4, 174.42, 631.06, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_producent_model", 4, 205.01, 613.81, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 596.56, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 540.64, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 540.64, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 540.64, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 518.95, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 497.52, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 497.52, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 4, 157.28, 471.65, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 4, 213.37, 471.65, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 4, 268.9, 449.95, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 4, 182.29, 428.52, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 4, 228.76, 428.52, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 4, 398.41, 385.4, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 444.89, 385.4, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 4, 165.06, 359.53, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 4, 222.03, 359.02, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 4, 281.0, 359.53, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 4, 161.18, 333.66, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 4, 218.15, 333.15, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 4, 277.12, 333.66, "kratka", wyrownanie="srodek"),
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 281.49, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 264.24, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 246.99, "tekst", maks_szerokosc=158.0),
	Pole("podpis_zamawiajacy", 4, 75.0, 124.53, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 124.53, "tekst", maks_szerokosc=155.22),
)

_STRONA_6: tuple[Pole, ...] = (
	# Strona 6 (idx 5): Zalacznik 2, arkusz klimatyzacji: dwie rubryki CEO "Rodzaj klimatyzacji" i "Moc klimatyzacji (kW)" (klucze klima_rodzaj, klima_moc_kw; wzor nie ma rubryki modelu) oraz podpisy obu stron.
	Pole("klima_rodzaj", 5, 165.55, 711.56, "tekst", maks_szerokosc=227.5),
	Pole("klima_moc_kw", 5, 177.18, 687.41, "tekst", maks_szerokosc=227.5),
	Pole("podpis_zamawiajacy", 5, 75.0, 624.16, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 624.16, "tekst", maks_szerokosc=155.22),
)

_STRONA_7: tuple[Pole, ...] = (
	# Strona 7 (idx 6): Zalacznik 3 (zgody: kontakt telefoniczny, dzialania promocyjne) i Zalacznik 4 (wczesniejsza realizacja), kratki male (10x10 pt), kazdy zalacznik z wlasna linia podpisu WYLACZNIE Zamawiajacego.
	Pole("zgoda_telefon", 6, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 6, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 6, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 6, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 6, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

_STRONA_9: tuple[Pole, ...] = (
	# Strona 9 (idx 8): koniec Zalacznika 5 (RODO), linia "data i podpis" klienta.
	Pole("rodo_data_imie_nazwisko", 8, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
)

_STRONA_17: tuple[Pole, ...] = (
	# Strona 17 (idx 16): Zalacznik 9, pelnomocnictwo OSD: data (reuzyta data_zawarcia), dane klienta, jedna linia podpisu Mocodawcy (prawa kolumna, klucz Zamawiajacego).
	Pole("data_zawarcia", 16, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 16, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 16, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 16, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 16, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PVK: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_7
	+ _STRONA_9
	+ _STRONA_17
)
"""Pelna mapa dla `crm/szablony/umowa_pv_k.pdf` (70 pozycji), zmierzona od zera."""
