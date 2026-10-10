# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: ME z klimatyzacja (K), `crm/szablony/umowa_me_k.pdf`.

Plik zrodlowy wzoru: `Umowa ME + K ProEnergy - 06.10.2026-3.pdf` (ostateczny wzor
z 06.10.2026, b69), 19 stron A4 (596x842 pt), SHA-256 w `SHA256_SZABLONU_MEK`.

POMIAR OD ZERA, 2026-10-10 (chunk U2h, issue ops#246): kazda wartosc `MAPA_MEK`
pochodzi z narzedzia `ops/narzedzia/umowa-mapa-pomiar.py` (repo
`proenergy-crm-ops`) uruchomionego na TYM pliku z deklaracja
`ops/narzedzia/deklaracje/umowa_me_k.py`: tekst i kreski z `pdftotext -bbox`,
pionowe kreski tabeli klienta i granulacja znakowa z `pdfminer.six`. Zadna
wspolrzedna nie jest przepisana z map siostrzanych ani ze starej mapy (reeksport
z Google Docs przesuwa nawet niezmienione strony). Konwencje: nagl. `volteo_umowa_mapa.py`
i docstring `volteo_umowa_mapa_pv2.py`: `y_reportlab = 842 - y_od_gory`; tekst na
kresce x = xMin + 3, y = 842 - yMax + 2.5, maks_szerokosc = szer. kreski - 6;
kratka x = srodek glifu, y = 842 - yMax + 3.0 (mala 10x10 pt: +2.0, rozmiar 8);
komorka tabeli x = pionowa kreska + 6; podpis: kolumna wg wspolrzednej x.

Strony BEZ pozycji (celowo, z powodu): idx 4 (spis zalacznikow),
idx 8 (RODO tresc), idx 10 (pouczenie o odstapieniu), idx 11 (formularz
odstapienia), idx 12-17 (protokol odbioru magazynu, protokol pomiarow, protokol
odbioru klimatyzacji z listami instalatora): wypelnia je klient/instalator po
montazu lub przy odstapieniu, nie generator z gory. Podpis Wykonawcy drukuje sie
w umowie glownej i Zalacznikach 1 i 2, w Zal. 3/4, RODO i pelnomocnictwie tylko
linia Zamawiajacego.

Osobliwosci wzoru: brak Zalacznika 1a (PV) i bloku drugiego Zamawiajacego; Zal. 1
to magazyn energii z sekcja istniejacej PV i opcjami dodatkowymi (dodatkowe moduly,
moduly z mikroinwerterem); Zal. 2 to klimatyzacja z DWIEMA rubrykami (rodzaj, moc),
bez modelu; wynagrodzenie netto i brutto lezy juz na stronie 2, a powierzchnia budynku (kratki do/ponad 300 m2) dopiero na stronie 3; na stronach
zalacznikow pierwsze kreski sa rubrykami, wiec podpisy wymagaja n=-1.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_MEK: str = "67a9912a37320b6b6099fcdf2576ef8b117ec0f66d9c8bbb24e1b9adb735f535"
"""SHA-256 pliku `crm/szablony/umowa_me_k.pdf`, policzone na pliku w repo."""

LICZBA_STRON_MEK: int = 19
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

_STRONA_1: tuple[Pole, ...] = (
	# Strona 1 (idx 0): komparycja (jedna tabela danych klienta), numer i data umowy, adres montazu (§1 ust. 1) i typ budynku (§1 ust. 2). Brak kwot: §2 zaczyna sie na nastepnej stronie.
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

_STRONA_2: tuple[Pole, ...] = (
	# Strona 2 (idx 1): §2 wynagrodzenie netto i brutto, opcje finansowania. Wzor drukuje kratki "Kredyt 100%" / "Kredyt z wkladem" / "Przelew", mapowane 1:1 na fin_kredyt_100 / fin_kredyt_wklad / fin_gotowka (kratka Przelew = literal bazy 'Gotowka 100%'). Zdanie pod kratkami o gotowce/przelewie jest stalym tekstem.
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
)

_STRONA_3: tuple[Pole, ...] = (
	# Strona 3 (idx 2): §3 ust. 1 lit. g, powierzchnia uzytkowa budynku: dwie kratki (do 300 m2 / powyzej) i rubryka z powierzchnia w m2 (pow_do_300, pow_ponad_300, powierzchnia_m2). Reszta strony to tresc umowy bez rubryk.
	Pole("pow_do_300", 2, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 703.93, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 703.42, "tekst", maks_szerokosc=66.27),
)

_STRONA_4: tuple[Pole, ...] = (
	# Strona 4 (idx 3): podpisy umowy glownej (Zamawiajacy, Wykonawca), pierwsze i jedyne kreski podpisu na stronie.
	Pole("podpis_zamawiajacy", 3, 75.0, 165.93, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 165.93, "tekst", maks_szerokosc=155.22),
)

_STRONA_6: tuple[Pole, ...] = (
	# Strona 6 (idx 5): Zalacznik 1, arkusz ustalen montazowych magazynu energii: inwerter hybrydowy, bateria (w tym liczba i pojemnosc), internet, moc przylaczeniowa, fazy, sekcja istniejacej PV (ist_pv_*), opcje dodatkowe (dod_panele_szt, dod_panele_mikro_szt: slownictwo mikroinwerter ze wzoru zostaje) i podpisy obu stron (n=-1: wczesniejsze kreski to rubryki).
	Pole("inwerter_producent_model", 5, 205.01, 694.88, "tekst", maks_szerokosc=244.17),
	Pole("inwerter_moc_kw", 5, 229.43, 677.63, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_gwarancja_lat", 5, 250.57, 660.38, "tekst", maks_szerokosc=55.16),
	Pole("bateria_producent_model", 5, 191.13, 625.89, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 5, 153.31, 608.64, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 5, 293.9, 591.39, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 5, 444.49, 591.39, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 5, 272.24, 574.14, "tekst", maks_szerokosc=57.93),
	Pole("bateria_gwarancja_lat", 5, 236.69, 556.89, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 5, 118.95, 518.22, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 5, 173.93, 518.22, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 5, 251.14, 518.22, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 5, 229.43, 496.52, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 5, 121.72, 475.09, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 5, 157.83, 475.09, "kratka", wyrownanie="srodek"),
	Pole("ist_pv_moc_inwertera_kw", 5, 222.76, 413.73, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 5, 232.76, 396.48, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 5, 170.01, 379.23, "tekst", maks_szerokosc=155.22),
	Pole("dod_panele_szt", 5, 195.0, 318.29, "tekst", maks_szerokosc=57.93),
	Pole("dod_panele_mikro_szt", 5, 303.3, 301.04, "tekst", maks_szerokosc=55.16),
	Pole("podpis_zamawiajacy", 5, 75.0, 178.58, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 178.58, "tekst", maks_szerokosc=155.22),
)

_STRONA_7: tuple[Pole, ...] = (
	# Strona 7 (idx 6): Zalacznik 2, arkusz klimatyzacji: rodzaj i moc (klima_rodzaj, klima_moc_kw) oraz podpisy obu stron (n=-1). Rubryki modelu klimatyzacji wzor nie ma (klima_model w wyjatkach testow).
	Pole("klima_rodzaj", 6, 165.55, 685.11, "tekst", maks_szerokosc=227.5),
	Pole("klima_moc_kw", 6, 177.18, 660.96, "tekst", maks_szerokosc=227.5),
	Pole("podpis_zamawiajacy", 6, 75.0, 597.71, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 6, 363.0, 597.71, "tekst", maks_szerokosc=155.22),
)

_STRONA_8: tuple[Pole, ...] = (
	# Strona 8 (idx 7): Zal. 3 (zgoda na kontakt telefoniczny, zgoda na dzialania promocyjne) i Zal. 4 (wczesniejsza realizacja) z dwiema liniami podpisu Zamawiajacego: n=0 = Zal. 3 (wyzej), n=1 = Zal. 4 (nizej). Wykonawca nie podpisuje.
	Pole("zgoda_telefon", 7, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 7, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 7, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 7, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

_STRONA_10: tuple[Pole, ...] = (
	# Strona 10 (idx 9): koniec Zal. 5 (RODO), linia "data i podpis" Zamawiajacego: drukujemy tu imie, nazwisko i date (rodo_data_imie_nazwisko).
	Pole("rodo_data_imie_nazwisko", 9, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

_STRONA_19: tuple[Pole, ...] = (
	# Strona 19 (idx 18): Zal. 9, pelnomocnictwo OSD: data zawarcia reuzyta w "udzielone w dniu", dane klienta oraz podpis Mocodawcy (tylko Zamawiajacy).
	Pole("data_zawarcia", 18, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 18, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 18, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 18, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 18, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_MEK: tuple[Pole, ...] = (
	*_STRONA_1, *_STRONA_2, *_STRONA_3, *_STRONA_4, *_STRONA_6, *_STRONA_7, *_STRONA_8, *_STRONA_10, *_STRONA_19,
)
"""Pozycje mapy wzoru ME_K, pogrupowane per strona w `_STRONA_n`."""
