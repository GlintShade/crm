# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Kociol (kod PP, nie KO), `crm/szablony/umowa_kociol.pdf`.

Plik zrodlowy wzoru: `Umowa Kocioł ProEnergy - 09.10.2026.pdf` (wzor dostarczony przez CEO
2026-10-09, b69), A4 596x842 pt, 12 stron.

POCHODZENIE WSPOLRZEDNYCH: pomiar OD ZERA, 2026-10-10 (b69, chunk U2n, issue ops#258),
narzedziem `ops/narzedzia/umowa-mapa-pomiar.py` z repo `proenergy-crm-ops`
(deklaracja `ops/narzedzia/deklaracje/umowa_kociol.py`) na pliku o SHA-256 ponizej.
Zadna wartosc nie pochodzi z map siostrzanych ani ze starej wersji wzoru. Konwencje
ukladu (`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkresleniu, kratek i
komorek tabeli): naglowek `crm/volteo_umowa_mapa.py`. Wynik przejrzany wzrokowo na
renderze `--sprawdz` (pdftoppm -r 110).

POLITYKA (klucze na strony):
- idx 0: komparycja, adres montazu, rodzaj budynku; idx 1: §2 (kratki `fin_*`
  mapowane 1:1: Kredyt 100% / Kredyt z wkladem / Przelew) ORAZ powierzchnia budynku
  (§3 ust. 1 lit. f) na tej samej stronie;
- podpisy: Zamawiajacy i Wykonawca w umowie glownej (idx 3) i w Zal. 1 (idx 4); w
  Zal. 2, 3 (idx 5) i RODO (idx 7) tylko linia Zamawiajacego;
- Zal. 1 (idx 4): `kociol_rodzaj`, `kociol_model_moc`, kratki `cwu_nie`/`cwu_200`/`cwu_300`;
- BEZ pozycji (celowo): idx 2, 3 poza podpisami (tresc umowy), idx 6 (RODO czesc 1),
  idx 8 (pouczenie o odstapieniu), idx 9 (formularz odstapienia), idx 10 i 11 (protokol
  odbioru kotla, z WLASNYMI kratkami CWU, nie mapowanymi: wypelnia instalator po
  montazu);
- osobliwosci wzoru: BRAK pelnomocnictwa OSD; brak arkusza PV/ME, dodatkow, drugiego
  Zamawiajacego i pol PC/KL.

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_PP` i odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PP: str = "5074ab6a8676ad8ab780ed9fcfe0e7cae2f8a7497a291ed7f3e8514192f93a4b"
"""SHA-256 pliku `crm/szablony/umowa_kociol.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PP: int = 12
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""


# ---------------------------------------------------------------------------
# Strona 1: komparycja (tabela danych klienta, numer, data zawarcia), adres miejsca
# montazu (§1 ust. 1) i rodzaj budynku (§1 ust. 2).
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
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

# ---------------------------------------------------------------------------
# Strona 2: §2 wynagrodzenie netto/brutto, trzy kratki platnosci (Kredyt 100% / Kredyt
# z wkladem wlasnym / Przelew; trzecia niesie `fin_gotowka`), wklad wlasny, kwota kredytu
# oraz §3 ust. 1 lit. f: kratki powierzchni budynku (do 300 m2 / ponad 300 m2) i
# powierzchnia w m2 (w tym wzorze lezy na stronie 2, nie 3).
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
	Pole("pow_do_300", 1, 115.5, 89.02, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 1, 242.73, 89.02, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 1, 379.34, 88.51, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4: blok podpisow umowy glownej (Zamawiajacy po lewej, Wykonawca po prawej).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 390.73, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 390.73, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5: Zalacznik 1, arkusz ustalen montazowych kotla: rodzaj kotla, model i moc,
# kratki zasobnika CWU (NIE / TAK 200 l / TAK 300 l), podpisy obu stron. Kreski pol
# danych wpadaja do lewej kolumny razem z linia podpisu, wiec podpis Zamawiajacego
# to trzecia kreska z lewej (n=2).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("kociol_rodzaj", 4, 138.34, 711.56, "tekst", maks_szerokosc=227.5),
	Pole("kociol_model_moc", 4, 134.44, 687.41, "tekst", maks_szerokosc=227.5),
	Pole("cwu_nie", 4, 155.04, 660.23, "kratka", wyrownanie="srodek"),
	Pole("cwu_200", 4, 203.37, 660.23, "kratka", wyrownanie="srodek"),
	Pole("cwu_300", 4, 286.52, 660.23, "kratka", wyrownanie="srodek"),
	Pole("podpis_zamawiajacy", 4, 75.0, 467.78, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 467.78, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6: Zalaczniki 2 i 3, zgody (3 male kratki) i po jednej linii podpisu
# Zamawiajacego (Zal. 2 u gory, Zal. 3 u dolu).
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8: Zalacznik 4 (RODO, koniec): linia daty i podpisu Zamawiajacego.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

MAPA_PP: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_4,
	*_STRONA_5,
	*_STRONA_6,
	*_STRONA_8,
)
