# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF.

Moduł celowo nie importuje ``frappe`` ani ``reportlab`` — jest to czysta
struktura danych (plus proste funkcje pomocnicze), więc daje się w pełni
przetestować lokalnie (`crm/test_volteo_umowa_mapa.py`), tak jak
`crm/volteo_umowa.py` i `crm/volteo_umowa_pdf.py`.

UKŁAD WSPÓŁRZĘDNYCH (uwaga, przeczytaj to dwa razy przed edycją mapy):
``pdftotext -bbox`` — narzędzie użyte do namierzenia każdej pozycji poniżej —
podaje ``yMin``/``yMax`` liczone OD GÓRY strony. ``reportlab`` (generator,
który skorzysta z tej mapy) rysuje w układzie liczonym OD DOŁU strony.
Każda wartość ``y`` zapisana w tym pliku jest już PRZELICZONA do układu
reportlab: ``y_reportlab = 842 - y_od_gory``. Strona ma wymiary 596x842 pt
(A4). Pomylenie kierunku osi Y daje tekst odbity względem środka strony —
przy pojedynczym polu blisko środka może to nie rzucać się w oczy, więc
każda wartość w ``MAPA`` została policzona SKRYPTEM z surowych ``xMin``/
``xMax``/``yMax`` odczytanych z `pdftotext -bbox` (żadna arytmetyka „w
pamięci"; patrz uzasadnienie w raporcie zadania, które przepisało tę mapę
2026-08-06 po zmianie szablonu — poprzednie podejście miało w tym miejscu
sześć błędów wynikających właśnie z ręcznego liczenia).

Tekst rysuje się od linii bazowej (baseline), nie od górnej krawędzi liter.
Dla pól z podkreśleniem (``______``) ``y`` w tej mapie leży ok. 2,5 pt NAD
samą kreską (od jej ``yMax`` zmierzonego przez ``pdftotext``), żeby wpisana
wartość wizualnie siedziała na kresce, a nie na niej leżała. Dla kratek
(``rodzaj="kratka"``) ``y`` jest ustawione ok. 2-3 pt nad dolną krawędzią
glifu ``☐``/``▢`` zmierzonego przez ``pdftotext`` (2,0 pt dla mniejszych,
8-punktowych kratek na stronie zgód — Załącznik nr 2/3 — 3,0 pt dla
standardowych, 15-punktowych kratek gdzie indziej), żeby narysowany znak
„X" wizualnie wypełniał kratkę; ``x`` jest środkiem kratki w poziomie
(generator ma wyśrodkować znak „X" względem tego punktu, zgodnie z
``wyrownanie="srodek"``). Dla pól wewnątrz tabel (dane klienta, protokoły
odbioru) ``y`` to wprost ``842 - yMax(etykiety)`` — bez korekty 2,5 pt,
bo w tabeli nie ma osobnej kreski do podkreślenia, wartość ma po prostu
stanąć w tej samej linii co etykieta wiersza; ``x`` to zmierzony pikselowo
(nie zgadnięty) środek pionowej kreski dzielącej kolumnę etykiet od kolumny
wartości, plus 6 pt wcięcia.

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku wejściowego
względem ``SHA256_SZABLONU`` przed użyciem tej mapy i przerwać z czytelnym
komunikatem przy niezgodności — nigdy nie wpisywać danych w oparciu o
niepewne współrzędne.
"""

from dataclasses import dataclass

SHA256_SZABLONU: str = "9d4ca0034bbd3921b96532e1588b6beae2f6feb371d64485e2fcf4a19a125bad"
"""SHA-256 pliku `Umowa PV + ME ProEnergy - 28.07.2026-3.pdf` (A4, 596x842 pt, 18 stron,
bez pól formularza), policzone `shasum -a 256` na oryginale dostarczonym do tego zadania
(2026-08-06) i zweryfikowane ponownie po skopiowaniu do `crm/szablony/umowa_pv_me.pdf`.
Mapa `MAPA` poniżej jest skalibrowana WYŁĄCZNIE dla tego dokładnego pliku — każda zmiana
szablonu (nawet kosmetyczna, np. przesunięcie akapitu) unieważnia współrzędne. Ta wersja
ZASTĘPUJE poprzednią kalibrację zrobioną na `Umowa PV + ME ProEnergy - 28.07.2026.pdf`
(bez `-3`) — dokument się przesunął (przykładowo Pełnomocnictwo: str. 10 → str. 18;
protokoły odbioru: str. 13/16 → str. 12/15), więc WSZYSTKIE współrzędne poniżej zostały
wyznaczone od nowa, żadna nie jest przeniesiona ze starej wersji."""

SZEROKOSC_STRONY_PT: float = 596.0
WYSOKOSC_STRONY_PT: float = 842.0
"""Wymiary strony A4 w punktach, zgodne z `pdfinfo` oryginału. Używane przez testy
do sprawdzenia, że każda współrzędna mieści się na stronie."""

_RODZAJE: frozenset[str] = frozenset({"tekst", "kratka"})
_WYROWNANIA: frozenset[str] = frozenset({"lewo", "srodek", "prawo"})


@dataclass(frozen=True)
class Pole:
	"""Jedna pozycja na jednej stronie, w którą generator ma wpisać wartość klucza.

	Ten sam ``klucz`` może (i często musi) wystąpić w wielu instancjach `Pole`
	— raz na każdej stronie, na której szablon rzeczywiście drukuje tę wartość
	(np. imię i nazwisko klienta pojawia się w komparycji, w pełnomocnictwie
	i w obu protokołach odbioru).
	"""

	klucz: str
	"""Klucz kontekstu zwracanego przez `crm.volteo_umowa_pdf.zbuduj_kontekst`."""

	strona: int
	"""Numer strony, 0-indeksowany (strona 1 dokumentu = 0)."""

	x: float
	"""Współrzędna pozioma w punktach, liczona od LEWEJ krawędzi strony."""

	y: float
	"""Współrzędna pionowa w punktach, liczona od DOLNEJ krawędzi strony
	(układ reportlab — zob. docstring modułu). To linia bazowa tekstu."""

	rodzaj: str
	"""``"tekst"`` — wpisanie wartości stringowej: ``"kratka"`` — narysowanie
	„X" w środku kratki, gdy wartość logiczna jest `True`."""

	wyrownanie: str = "lewo"
	"""``"lewo"`` | ``"srodek"`` | ``"prawo"`` — sposób wyrównania tekstu/znaku
	względem punktu (x, y). Kratki używają `"srodek"` (x = środek kratki)."""

	maks_szerokosc: float | None = None
	"""Maksymalna szerokość w punktach dostępna na wpisanie wartości (do
	przycięcia/zawinięcia długich wartości przez generator). `None`, gdy nie
	zmierzono ograniczenia (np. kratki, gdzie nie ma zastosowania)."""

	rozmiar: float = 10.0
	"""Rozmiar fontu w punktach."""


# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja, §1 Przedmiot umowy
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("umowa_nr", 0, 206.36, 722.57, "tekst", maks_szerokosc=194.22),
	Pole("data_zawarcia", 0, 135.56, 697.43, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 0, 177.16, 658.48, "tekst", maks_szerokosc=342.17),
	Pole("klient_adres", 0, 177.16, 634.01, "tekst", maks_szerokosc=342.17),
	Pole("klient_pesel", 0, 177.16, 609.53, "tekst", maks_szerokosc=342.17),
	Pole("klient_telefon", 0, 177.16, 585.06, "tekst", maks_szerokosc=342.17),
	Pole("klient_email", 0, 177.16, 560.59, "tekst", maks_szerokosc=342.17),
	Pole("adres_montazu", 0, 111.0, 331.4, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 274.49, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 254.49, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 715.33, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 688.88, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 618.58, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 598.75, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 556.64, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 530.19, "tekst", maks_szerokosc=310.88),
	Pole("fin_gotowka", 1, 115.5, 512.79, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. g — powierzchnia budynku
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 662.25, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 662.25, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.35, 661.74, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe — blok podpisów umowy głównej
#
# Autenti dokleja jedno zbiorcze poświadczenie na końcu całego pliku (jeden
# podpis elektroniczny obejmujący cały dokument) — klient nie podpisuje się
# osobno w każdym miejscu. Te pozycje wypełniają miejsce na podpis klienta i
# ProEnergy DRUKOWANYMI literami jako oznaczenie strony, nie jako podpis w
# rozumieniu prawa. `x`/`y` zmierzone identycznie jak reszta mapy i wg tej
# samej konwencji co inne pola tekstowe na podkreśleniu w tym pliku (np.
# `panel_producent_model`, `bateria_producent_model`): `x` = zmierzony
# `xMin` kreski + 3 pt wcięcia z lewej, `maks_szerokosc` = zmierzona
# szerokość kreski - 6 pt (symetryczny zapas 3 pt po obu stronach), `y` leży
# 2,5 pt NAD zmierzoną kreską (``pdftotext -bbox``, linia "_____...", strona
# 4: Zamawiający xMin=72.0/xMax=235.999663, Wykonawca xMin=360.0/
# xMax=521.223511, oba yMax=498.215334).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 346.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 346.28, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik 1a — Instalacja fotowoltaiczna
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 4, 223.9, 715.33, "tekst", maks_szerokosc=55.15),
	Pole("panel_szt", 4, 381.7, 715.33, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 4, 186.09, 698.08, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 4, 280.02, 680.83, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 4, 249.46, 663.58, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 4, 183.31, 629.09, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 4, 174.42, 611.84, "tekst", maks_szerokosc=57.94),
	Pole("inwerter_producent_model", 4, 205.01, 594.59, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 577.34, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 521.41, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 521.41, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 521.41, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 499.72, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 478.29, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 478.29, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 4, 157.28, 452.42, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 4, 213.38, 452.42, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 4, 268.9, 430.73, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 4, 182.29, 409.3, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 4, 228.76, 409.3, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 4, 398.41, 348.93, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 444.89, 348.93, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 4, 165.06, 323.06, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 4, 222.03, 322.55, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 4, 281.0, 323.06, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 4, 161.18, 297.18, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 4, 218.15, 296.67, "tekst", maks_szerokosc=38.47),
	Pole("kabel_nie", 4, 277.12, 297.18, "kratka", wyrownanie="srodek"),
	# Blok podpisów Załącznika 1a — patrz uzasadnienie przy `_STRONA_4` powyżej.
	# Kreska podpisu (pdftotext -bbox): Zamawiający xMin=72.0/xMax=235.999663,
	# Wykonawca xMin=360.0/xMax=521.223511, oba yMax=674.224364.
	Pole("podpis_zamawiajacy", 4, 75.0, 170.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 170.28, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik 1b — Magazyn energii
#
# Ta strona w OBOWIĄZUJĄCEJ wersji NIE powiela już pól internet/moc
# przyłączeniowa/liczba faz (są tylko raz, na stronie 5) — poprzednia
# kalibracja zakładała ich duplikat tutaj, co było błędne dla tego szablonu.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("bateria_producent_model", 5, 191.13, 715.33, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 5, 153.31, 698.08, "tekst", maks_szerokosc=55.15),
	Pole("bateria_pojemnosc_jedn_kwh", 5, 293.9, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 5, 444.5, 680.83, "tekst", maks_szerokosc=55.15),
	Pole("bateria_pojemnosc_lacznie_kwh", 5, 272.24, 663.58, "tekst", maks_szerokosc=55.15),
	Pole("bateria_gwarancja_lat", 5, 236.69, 646.34, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_inwertera_kw", 5, 167.19, 572.17, "tekst", maks_szerokosc=57.94),
	Pole("ist_pv_moc_kwp", 5, 232.76, 554.92, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 5, 170.01, 537.67, "tekst", maks_szerokosc=155.23),
	# Blok podpisów Załącznika 1b — patrz uzasadnienie przy `_STRONA_4` powyżej.
	# Kreska podpisu (pdftotext -bbox): Zamawiający xMin=72.0/xMax=235.999663,
	# Wykonawca xMin=360.0/xMax=521.223511, oba yMax=398.248044.
	Pole("podpis_zamawiajacy", 5, 75.0, 446.25, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 446.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 7 (indeks 6): Załącznik nr 2 (zgody) i Załącznik nr 3 (oświadczenie
# o realizacji przed terminem odstąpienia — ten drugi ma własną kratkę, ale
# BEZ odpowiadającego jej klucza w `zbuduj_kontekst`; zob. raport zadania).
# Kratki na tej stronie są mniejsze (10x10 pt, nie 15x15 jak gdzie indziej),
# stąd inny offset (2,0 pt) i mniejszy `rozmiar` (8 pt) — zgodnie z oryginałem.
# ---------------------------------------------------------------------------
_STRONA_7: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 6, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 6, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Blok podpisów Załącznika 2 i (osobno, niżej na tej samej stronie) blok
	# podpisów Załącznika 3 — oba mają WYŁĄCZNIE linię Zamawiającego, bez
	# Wykonawcy (zob. render strony 7). Patrz uzasadnienie przy `_STRONA_4`.
	# Kreski podpisu (pdftotext -bbox): Zał. 2 xMin=72.0/xMax=233.223511/
	# yMax=242.185544; Zał. 3 xMin=72.0/xMax=233.223511/yMax=728.824224.
	Pole("podpis_zamawiajacy", 6, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 6, 75.0, 115.68, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 12 (indeks 11): Załącznik nr 6 — Protokół odbioru instalacji PV
# (dane techniczne modułów i inwertera; strona 13 to lista szkoleniowa/zdjęć
# wypełniana przez instalatora — bez pól z kontekstu; strona 14 to protokół
# pomiarów, również bez pól z kontekstu)
# ---------------------------------------------------------------------------
_STRONA_12: tuple[Pole, ...] = (
	Pole("data_zawarcia", 11, 152.05, 682.81, "tekst", maks_szerokosc=79.09),
	Pole("klient_imie_nazwisko", 11, 192.22, 638.6, "tekst", maks_szerokosc=327.11),
	Pole("klient_adres", 11, 192.22, 615.45, "tekst", maks_szerokosc=327.11),
	Pole("panel_moc_wp", 11, 228.2, 496.89, "tekst", maks_szerokosc=291.13),
	Pole("panel_szt", 11, 228.2, 473.74, "tekst", maks_szerokosc=291.13),
	Pole("moc_pv_kwp", 11, 228.2, 450.59, "tekst", maks_szerokosc=291.13),
	Pole("panel_producent_model", 11, 228.2, 426.5, "tekst", maks_szerokosc=291.13),
	Pole("inwerter_moc_kw", 11, 225.27, 178.06, "tekst", maks_szerokosc=294.06),
	Pole("inwerter_szt", 11, 225.27, 154.91, "tekst", maks_szerokosc=294.06),
	Pole("inwerter_producent_model", 11, 225.27, 131.76, "tekst", maks_szerokosc=294.06),
)

# ---------------------------------------------------------------------------
# Strona 15 (indeks 14): Załącznik nr 7 — Protokół odbioru magazynu energii
# (strona 16 kontynuuje tę samą tabelę numerami seryjnymi — bez pól z
# kontekstu — i dodaje listę szkoleniową/zdjęć instalatora)
# ---------------------------------------------------------------------------
_STRONA_15: tuple[Pole, ...] = (
	Pole("data_zawarcia", 14, 152.05, 682.81, "tekst", maks_szerokosc=79.09),
	Pole("klient_imie_nazwisko", 14, 192.2, 638.6, "tekst", maks_szerokosc=327.13),
	Pole("klient_adres", 14, 192.2, 615.45, "tekst", maks_szerokosc=327.13),
	Pole("bateria_producent_model", 14, 228.2, 496.89, "tekst", maks_szerokosc=291.13),
	Pole("bateria_moc_kw", 14, 228.2, 450.59, "tekst", maks_szerokosc=291.13),
	Pole("bateria_pojemnosc_lacznie_kwh", 14, 228.2, 426.5, "tekst", maks_szerokosc=291.13),
	Pole("bateria_szt", 14, 228.2, 392.38, "tekst", maks_szerokosc=291.13),
	Pole("ist_pv_producent_inwertera", 14, 225.27, 168.11, "tekst", maks_szerokosc=294.06),
	Pole("ist_pv_moc_inwertera_kw", 14, 225.27, 121.81, "tekst", maks_szerokosc=294.06),
	Pole("ist_pv_moc_kwp", 14, 225.27, 98.66, "tekst", maks_szerokosc=294.06),
)

# ---------------------------------------------------------------------------
# Strona 18 (indeks 17): Załącznik nr 8 — Pełnomocnictwo OSD
# ---------------------------------------------------------------------------
_STRONA_18: tuple[Pole, ...] = (
	# "udzielone w dniu ___" — brak osobnego klucza w kontekście na datę
	# udzielenia pełnomocnictwa (podpisywane tego samego dnia co umowa);
	# świadomie reużyty `data_zawarcia`, zob. docstring testu i raport zadania.
	Pole("data_zawarcia", 17, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 17, 171.13, 681.66, "tekst", maks_szerokosc=87.87),
	Pole("klient_adres", 17, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 17, 110.01, 668.43, "tekst", maks_szerokosc=116.3),
	# Jedna linia podpisu — "Mocodawcy" (klient), BEZ Wykonawcy: pełnomocnictwo
	# jest jednostronnym oświadczeniem klienta wobec ProEnergy, nie umową
	# dwustronną, więc szablon tu nie drukuje drugiej strony do podpisu.
	# Kreska podpisu (pdftotext -bbox): xMin=362.054235/xMax=523.277746/
	# yMax=665.349614. Patrz uzasadnienie przy `_STRONA_4` powyżej.
	Pole("podpis_zamawiajacy", 17, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_7
	+ _STRONA_12
	+ _STRONA_15
	+ _STRONA_18
)
"""Pełna mapa: krotka wszystkich `Pole` na wszystkich stronach. Jeden klucz
kontekstu może wystąpić wielokrotnie (raz na każdej stronie, gdzie faktycznie
jest drukowany) — generator ma narysować wartość we WSZYSTKICH pozycjach
danego klucza, nie tylko w pierwszej."""

# Strony 8, 9, 10, 11, 13, 14, 16, 17 (indeksy 7, 8, 9, 10, 12, 13, 15, 16) nie
# zawierają żadnej pozycji z kontekstu `zbuduj_kontekst` — to statyczne
# oświadczenia (RODO na str. 8-9), pouczenie o prawie do odstąpienia (str. 10),
# pusty formularz odstąpienia do ewentualnego wypełnienia przez klienta w
# przyszłości (str. 11), listy szkoleniowe/zdjęć i protokoły pomiarów
# elektrycznych wypełniane przez instalatora przy montażu (str. 13, 14, 16,
# 17) — żadna z tych wartości nie pochodzi z `Volteo Umowa`/`CRM Deal` w
# chwili generowania PDF-u. Świadomie NIE ma tu bloków podpisów: protokoły
# odbioru (str. 12-17) podpisuje instalator dopiero po montażu, a formularz
# odstąpienia (str. 11) klient wypełnia tylko wtedy, gdy faktycznie odstępuje
# od umowy — wydrukowanie tam naszego podpisu poświadczałoby coś, co się nie
# wydarzyło (decyzja właściciela projektu, zob. raport zadania).


def pozycje_dla(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA if pole.klucz == klucz)


def klucze_w_mapie() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA)
