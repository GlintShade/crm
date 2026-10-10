# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Pompa ciepla, `crm/szablony/umowa_pompa_ciepla.pdf`.

Plik zrodlowy wzoru: `Umowa PC ProEnergy - 09.10.2026.pdf` (wzor dostarczony przez CEO 2026-10-09,
b69, dogrywka chunka U1), A4, 12 stron.

POMIAR: wspolrzedne zmierzone OD ZERA 2026-10-10 narzedziem
`ops/narzedzia/umowa-mapa-pomiar.py` z deklaracji `ops/narzedzia/deklaracje/umowa_pompa_ciepla.py`,
bezposrednio z pliku `crm/szablony/umowa_pompa_ciepla.pdf` (zadnej wartosci nie przepisano
z map siostrzanych ani ze starych wzorow). Podglad kontrolny: `--sprawdz`, 12 stron obejrzanych na PNG.
Konwencje ukladu (`y_reportlab = 842 - y_od_gory`, offsety tekstu, kratek i komorek
tabeli): naglowek `crm/volteo_umowa_mapa.py` oraz `crm/volteo_umowa_mapa_pv2.py`.

STRUKTURA WZORU (12 stron): bez pelnomocnictwa OSD; Zal. 1 urzadzenie; Zal. 2 i 3 zgody;
Zal. 4 RODO; Zal. 5 pouczenie i formularz odstapienia; Zal. 6 protokol odbioru.
Zal. 1 (urzadzenie): Producent, Typ, Moc, Zasobnik CWU (NIE / TAK 200 l / TAK 300 l),
  grzejniki 600x600 / 800 / 1000 / 1200 / 1600 (ilosc szt.). Uwaga: to NIE jest umowa
  Czyste Powietrze (`umowa_cp_obsluga_dotacji.pdf`, kod CP).

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_PC` i odmawia renderu przy niezgodnosci.

STRONY BEZ POZYCJI (celowo): idx 2 (par. 3 ust. 2 do par. 7), idx 3 poza podpisami (par. 8),
idx 6 (RODO, tresc), idx 8 (pouczenie o odstapieniu), idx 9 (formularz odstapienia),
idx 10 i 11 (Zal. 6 protokol odbioru: wypelniaja instalator i klient po montazu, w tym wlasne
kratki "Zasobnik CWU" protokolu, NIE sa mapowane). Wzor nie ma pelnomocnictwa OSD.

OSOBLIWOSCI: Zal. 3 miesci sie na tej samej stronie co Zal. 2 (idx 5, dwa podpisy
Zamawiajacego, n=0 i n=1); wynagrodzenie i powierzchnia budynku leza na stronie 2 (idx 1);
kratki CWU sa w jednej linii i rozrozniane kotwica `obok` ("NIE", "TAK - 200", "TAK - 300").
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PC: str = "6050d38c01764225d7387093002b25ee6f177a251ae2114a8ac839f8f665724a"
"""SHA-256 pliku `crm/szablony/umowa_pompa_ciepla.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PC: int = 12
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

_STRONA_0: tuple[Pole, ...] = (
	# Strona 1: komparycja (tabela klienta), numer i data umowy, adres montazu, rodzaj budynku (par. 1).
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 353.57, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 289.88, "kratka", wyrownanie="srodek"),
)

_STRONA_1: tuple[Pole, ...] = (
	# Strona 2: wynagrodzenie netto/brutto, opcja finansowania z wkladem i kredytem (par. 2), powierzchnia budynku (par. 3 ust. 1 lit. f).
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
	Pole("pow_do_300", 1, 115.5, 89.02, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 1, 240.5, 89.02, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 1, 377.66, 88.51, "tekst", maks_szerokosc=66.27),
)

_STRONA_3: tuple[Pole, ...] = (
	# Strona 4: podpisy umowy glownej: Zamawiajacy (lewa), Wykonawca (prawa).
	Pole("podpis_zamawiajacy", 3, 75.0, 456.85, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 456.85, "tekst", maks_szerokosc=155.22),
)

_STRONA_4: tuple[Pole, ...] = (
	# Strona 5: Zal. 1, arkusz ustalen montazowych pompy ciepla: producent, typ, moc, zasobnik CWU (3 kratki w jednej linii), 5 rozmiarow grzejnikow, podpisy obu stron (ostatnie linie kolumn).
	Pole("pc_producent", 4, 126.12, 711.56, "tekst", maks_szerokosc=227.5),
	Pole("pc_typ", 4, 96.67, 687.41, "tekst", maks_szerokosc=227.5),
	Pole("pc_moc_kw", 4, 99.44, 664.41, "tekst", maks_szerokosc=88.51),
	Pole("cwu_nie", 4, 155.04, 613.08, "kratka", wyrownanie="srodek"),
	Pole("cwu_200", 4, 203.37, 613.08, "kratka", wyrownanie="srodek"),
	Pole("cwu_300", 4, 286.52, 613.08, "kratka", wyrownanie="srodek"),
	Pole("grzejnik_600x600_szt", 4, 175.84, 563.22, "tekst", maks_szerokosc=94.07),
	Pole("grzejnik_600x800_szt", 4, 175.84, 539.07, "tekst", maks_szerokosc=94.07),
	Pole("grzejnik_600x1000_szt", 4, 181.4, 514.92, "tekst", maks_szerokosc=94.07),
	Pole("grzejnik_600x1200_szt", 4, 181.4, 490.77, "tekst", maks_szerokosc=94.07),
	Pole("grzejnik_600x1600_szt", 4, 181.4, 466.63, "tekst", maks_szerokosc=94.07),
	Pole("podpis_zamawiajacy", 4, 75.0, 375.78, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 375.78, "tekst", maks_szerokosc=155.22),
)

_STRONA_5: tuple[Pole, ...] = (
	# Strona 6: Zal. 2 (zgoda telefoniczna, zgoda promocyjna, podpis) i Zal. 3 (zgoda na wczesniejsza realizacje, podpis); kratki zgod 10x10 pt.
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

_STRONA_7: tuple[Pole, ...] = (
	# Strona 8: Zal. 4 RODO, koniec: data i podpis Zamawiajacego.
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

MAPA_PC: tuple[Pole, ...] = _STRONA_0 + _STRONA_1 + _STRONA_3 + _STRONA_4 + _STRONA_5 + _STRONA_7
"""Pozycje mapy wzoru PC: suma krotek stron, zmierzona od zera."""
