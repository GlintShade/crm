# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Budowniczy kontekstu do renderowania PDF-u umowy instalacyjnej.

Moduł celowo nie importuje ``frappe`` — z tego samego powodu co
`crm/volteo_umowa.py`: ``frappe`` nie jest instalowalne na tej maszynie, więc
to jedyny sposób na lokalną, silną bramkę testową (`crm/test_volteo_umowa_pdf.py`).
Cała logika zależna od frameworka (pobranie dokumentów, wywołanie
`get_pdf`/`frappe.render_template`) mieszka gdzie indziej — tu tylko czysta
funkcja `zbuduj_kontekst`, która zamienia surowe dane domenowe na gotowe do
wydruku stringi i booleany. Szablon HTML nie liczy ani nie formatuje niczego.

REGUŁA NADRZĘDNA (dokument prawny podpisywany przez klienta): brak danych
zawsze renderuje się jako pusty string, nigdy jako zmyślona wartość — ani
``"0"``, ani ``"0,00"``, ani ``"None"``, ani tekst placeholdera z bazy.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from crm.volteo_umowa import _sparsuj_decimal as _sparsuj_decimal_wspolny
from crm.volteo_umowa import miejsce_i_pokrycie

# `KONSTRUKCJA_MONTAZ` (mapowanie `custom_konstrukcja` → miejsce/pokrycie) NIE
# jest tu importowana bezpośrednio: zamiast duplikować logikę odczytu tej mapy,
# używamy już przetestowanej funkcji `miejsce_i_pokrycie()` poniżej, która
# korzysta z niej wewnętrznie. Import samej stałej byłby tu martwym kodem.

# Reużyty jeden parser z `crm/volteo_umowa.py` (string→Decimal, nigdy nie rzuca)
# — patrz tamtejszy docstring dla szczegółów. Nadany lokalny alias zamiast
# przenoszenia funkcji do wspólnego pliku: PDF jest jedynym drugim konsumentem,
# a przenosiny złamałyby import w `crm/test_volteo_umowa.py`, którego nie wolno
# ruszać w tym zadaniu.
_sparsuj_decimal = _sparsuj_decimal_wspolny

POLA_KOMPONENTU: tuple[str, ...] = (
	"kategoria",
	"nazwa",
	"model",
	"producent",
	"moc_kw",
	"moc_wp",
	"pojemnosc_kwh",
	"gwarancja_lat",
	"gwarancja_tekst",
)
"""JEDYNE źródło prawdy o polach `Volteo Komponent`, których ten moduł potrzebuje
od wywołującego. `_znajdz_komponent()` poniżej dopasowuje wiersze po `kategoria`
i sklejonym `nazwa`+`model`; `zbuduj_kontekst()` czyta z dopasowanego wiersza
`moc_kw`/`moc_wp`/`gwarancja_lat`/`gwarancja_tekst`/`pojemnosc_kwh`. Wywołujący
(dziś: `crm/api/umowa.py`
przy pobieraniu `frappe.get_all("Volteo Komponent", ...)`) MA pobierać z bazy
DOKŁADNIE ten zestaw pól — ani mniej, ani więcej:

- Mniej cicho psuje dopasowanie: `wiersz.get(klucz)` na brakującym kluczu zwraca
  `None` zamiast rzucać, więc np. pominięcie `kategoria` sprawia, że
  `_znajdz_komponent` nigdy niczego nie znajduje — bez wyjątku, bez wpisu w
  logach, po prostu ciche puste pola w gotowym PDF-ie umowy. Dokładnie to
  wydarzyło się 2026-08-06: `_KOMPONENT_POLA` w `crm/api/umowa.py` był osobnym
  literałem bez `kategoria`, `inwerter_*`/`bateria_*` wychodziły puste na
  produkcji, a żadna bramka (ruff, py_compile, ten plik testów) tego nie
  złapała, bo test wywołuje `zbuduj_kontekst()` bezpośrednio z poprawnymi
  fixture'ami — nie przechodzi przez rzeczywistą listę pól API.
- Więcej ryzykuje przeciek pola kosztowego: `Volteo Komponent` ma także
  `cena_jednostkowa_netto` (permlevel 1, wewnętrzna cena zakupu) — to pole
  NIGDY nie może się tu pojawić ani trafić do kontekstu szablonu PDF-u,
  zgodnie z modelem tajemnicy kosztów/prowizji obowiązującym w całym projekcie.

Wywołujący powinien wyprowadzać swoją listę pól z tej stałej (np.
`list(POLA_KOMPONENTU)`), żeby obie strony kontraktu nie mogły się już rozjechać."""

_KWOTA_KWANT = Decimal("0.01")
"""Precyzja kwotowa (grosze) przy formatowaniu do wydruku."""

_WZORZEC_MODULOW_BATERII = re.compile(r"\(([0-9]+(?:\+[0-9]+)*)\)\s*$")
"""Wylapuje nawias z modulami na KONCU stringu `model` (np. "(6+6)" w
"12 kWh (6+6)"). Celowo dopasowuje tylko cyfry i "+" - katalog nie ma dzis
modulow o pojemnosci niecalkowitej wewnatrz nawiasu; string niepasujacy do
tego wzorca jest traktowany jak "brak nawiasu" (pojedynczy modul), nie jak
blad, wiec np. nawias z literami nie zostanie tu w ogole rozpoznany."""

_NBSP = " "
"""Spacja nierozdzielająca — polski separator tysięcy w kwotach na wydruku."""

# ŚWIADOMA RÓŻNICA wobec `_ZERO_OZNACZA_PUSTE` w `crm/volteo_umowa.py`:
# tamten zbiór celowo WYKLUCZA pola kwotowe (`wklad_wlasny_pln`), bo służy do
# `brakujace_pola` — sprawdzenia kompletności ROBOCZEGO formularza, gdzie
# "0 zł wkładu własnego" jest poprawną, wypełnioną odpowiedzią. Tu renderujemy
# GOTOWY DOKUMENT PRAWNY: umowa na wynagrodzenie 0,00 zł nie ma sensu, więc
# w tym module zero jest pustką dla WSZYSTKICH wartości liczbowych, łącznie
# z czterema kwotami (netto, brutto, wkład własny, kwota kredytu). Nie
# "naprawiać" tego przez zaimportowanie tamtego zbioru.
_WSZYSTKO_ZERO_JEST_PUSTKA = True


def zbuduj_kontekst(
	umowa: dict[str, Any],
	deal: dict[str, Any],
	kontakt: dict[str, Any],
	zestaw: list[dict[str, Any]],
	komponenty: list[dict[str, Any]],
	stale: dict[str, Any],
	dzis: date,
) -> dict[str, Any]:
	"""Buduje kontekst do wstawienia w szablon PDF-u umowy (§1-§7, Zał. 1a/1b/2).

	Nie mutuje żadnego z argumentów — wszystkie zwracane wartości są nowymi
	stringami/boolami wyliczonymi z wejścia. Klucze i ich znaczenie są
	zdefiniowane w kontrakcie `UMOWA-PDF-KONTRAKT.md`; nazwy są wiążące.
	"""
	falownik_nazwa = deal.get("custom_falownik")
	falownik_komponent = _znajdz_komponent(komponenty, "Falownik", falownik_nazwa)
	falownik_ilosc = _ilosc_z_zestawu(zestaw, falownik_nazwa)

	bateria_nazwa = deal.get("custom_bateria")
	bateria_komponent = _znajdz_komponent(komponenty, "Magazyn energii", bateria_nazwa)
	bateria_szt, bateria_pojemnosc_jedn_kwh = _bateria_szt_i_pojemnosc_jedn(bateria_komponent)

	panel_nazwa = deal.get("custom_panel")
	panel_komponent = _znajdz_komponent(komponenty, "Panel PV", panel_nazwa)
	if panel_komponent is None:
		panel_moc_wp = _liczba_calkowita(stale.get("panel_moc_wp"))
		panel_producent_model = _polacz(stale.get("panel_producent"), stale.get("panel_model"))
		panel_gwarancja_lat = _tekst(stale.get("panel_gwarancja_lat"))
	else:
		panel_moc_wp = _liczba_calkowita(_pole(panel_komponent, "moc_wp"))
		panel_producent_model = _tekst(panel_nazwa)
		panel_gwarancja_lat = _tekst(_pole(panel_komponent, "gwarancja_tekst"))

	miejsce_montazu, pokrycie_dachowe = miejsce_i_pokrycie(deal.get("custom_konstrukcja"))

	adres_zam = _adres(
		umowa.get("adres_zam_ulica"),
		umowa.get("adres_zam_nr_domu"),
		umowa.get("adres_zam_nr_mieszkania"),
		umowa.get("adres_zam_kod"),
		umowa.get("adres_zam_miasto"),
	)
	adres_montaz_szczegolowy = _adres(
		umowa.get("adres_montaz_ulica"),
		umowa.get("adres_montaz_nr_domu"),
		umowa.get("adres_montaz_nr_mieszkania"),
		umowa.get("adres_montaz_kod"),
		umowa.get("adres_montaz_miasto"),
	)
	adres_montazu = adres_montaz_szczegolowy or _adres_montazu_deal(deal)

	# Decyzja projektowa (poza kontraktem — tam był tylko klucz `klient_adres`,
	# nie jego źródło): gdy przedstawiciel zaznaczył `adres_zam_jak_montaz ==
	# "Tak"`, formularz świadomie NIE zbiera osobno pól adresu zamieszkania
	# (`_WYMAGANE_INNY_ADRES` w `crm/volteo_umowa.py` wymaga ich tylko dla
	# "Nie") — więc `adres_zam` jest wtedy legalnie pusty, mimo że adres
	# faktycznie jest znany. W takim wypadku klient_adres spada na adres
	# montażu zamiast wychodzić puste.
	klient_adres = adres_zam
	if not klient_adres and _rowna(umowa.get("adres_zam_jak_montaz"), "Tak"):
		klient_adres = adres_montazu

	typ_budynku = umowa.get("typ_budynku")
	finansowanie = umowa.get("finansowanie")
	powierzchnia_prog = umowa.get("powierzchnia_prog")
	internet = umowa.get("internet")

	ppoz_stan = _stan_bool(umowa.get("ppoz_wymagane"))
	zgoda_telefon_stan = _stan_bool(umowa.get("zgoda_kontakt_telefoniczny"))
	zgoda_promocja_stan = _stan_bool(umowa.get("zgoda_dzialania_promocyjne"))
	zgoda_wczesniejsza_realizacja_stan = _stan_bool(umowa.get("zgoda_realizacja_przed_odstapieniem"))

	kabel_mb_dec = _sparsuj_decimal(umowa.get("dodatkowy_kabel_m"))
	kabel_mb_puste = kabel_mb_dec is None or kabel_mb_dec == 0
	kabel_wybor = umowa.get("dodatkowy_kabel")
	kabel_tak_wybrano = _rowna(kabel_wybor, "Tak")
	kabel_nie_wybrano = _rowna(kabel_wybor, "Nie")

	klient_imie_nazwisko = _polacz(kontakt.get("first_name"), kontakt.get("last_name"))

	return {
		# Strony i nagłówek
		"umowa_nr": _tekst(deal.get("name")),
		"data_zawarcia": _data_pl(dzis),
		"klient_imie_nazwisko": klient_imie_nazwisko,
		"klient_adres": klient_adres,
		"klient_pesel": _tekst(kontakt.get("custom_pesel")),
		"klient_telefon": _tekst(kontakt.get("mobile_no")),
		"klient_email": _tekst(kontakt.get("email")),
		# §1
		"adres_montazu": adres_montazu,
		"budynek_jednorodzinny": _rowna(typ_budynku, "Jednorodzinny"),
		"budynek_wielorodzinny": _rowna(typ_budynku, "Wielorodzinny"),
		# §2
		"wynagrodzenie_netto": _kwota(deal.get("custom_netto")),
		"wynagrodzenie_brutto": _kwota(deal.get("deal_value")),
		"fin_kredyt_100": _rowna(finansowanie, "Kredyt 100%"),
		"fin_kredyt_wklad": _rowna(finansowanie, "Kredyt + gotówka"),
		"fin_gotowka": _rowna(finansowanie, "Gotówka 100%"),
		"wklad_wlasny": _kwota(umowa.get("wklad_wlasny_pln")),
		"kwota_kredytu": _kwota(umowa.get("kwota_kredytu_pln")),
		# §3 ust. 1 lit. g
		"pow_do_300": _rowna(powierzchnia_prog, "do 300 m²"),
		"pow_ponad_300": _rowna(powierzchnia_prog, "powyżej 300 m²"),
		"powierzchnia_m2": _liczba(umowa.get("powierzchnia_m2")),
		# Załącznik 1a
		"panel_moc_wp": panel_moc_wp,
		"panel_szt": _liczba_calkowita(deal.get("custom_panele")),
		"moc_pv_kwp": _liczba(deal.get("custom_pv_power_kwp")),
		"panel_producent_model": panel_producent_model,
		"panel_gwarancja_lat": panel_gwarancja_lat,
		"inwerter_moc_kw": _liczba(_pole(falownik_komponent, "moc_kw")),
		"inwerter_szt": _liczba_calkowita(falownik_ilosc),
		"inwerter_producent_model": _tekst(falownik_nazwa),
		"inwerter_gwarancja_lat": _liczba_calkowita(_pole(falownik_komponent, "gwarancja_lat")),
		"internet_wifi": _rowna(internet, "Wi-Fi"),
		"internet_kablowy": _rowna(internet, "Kablowy"),
		"internet_brak": _rowna(internet, "Brak"),
		"moc_przylaczeniowa_kw": _liczba(umowa.get("moc_przylaczeniowa_kw")),
		"fazy_1": _rowna(umowa.get("liczba_faz"), "1"),
		"fazy_3": _rowna(umowa.get("liczba_faz"), "3"),
		"montaz_dach": miejsce_montazu == "Dach",
		"montaz_grunt": miejsce_montazu == "Grunt",
		"pokrycie_dachowe": _tekst(pokrycie_dachowe),
		"odgromowa_tak": _rowna(umowa.get("instalacja_odgromowa"), "Tak"),
		"odgromowa_nie": _rowna(umowa.get("instalacja_odgromowa"), "Nie"),
		"ppoz_tak": ppoz_stan is True,
		"ppoz_nie": ppoz_stan is False,
		"przekop_tak": _rowna(umowa.get("przekop_gruntowy"), "Tak"),
		"przekop_nie": _rowna(umowa.get("przekop_gruntowy"), "Nie"),
		# `przekop_mb` istnieje w schemacie `Volteo Umowa` (`ops/crm-umowa.py`)
		# i na whiteliście zapisu `crm/api/umowa.py`, ale może zostać
		# niewypełnione przez przedstawiciela — odczyt jest więc defensywny
		# (`.get()` na brakującym/pustym kluczu daje pustkę, nigdy wyjątek).
		"przekop_mb": _liczba_calkowita(umowa.get("przekop_mb")),
		# `dodatkowy_kabel` (Select: Tak/Nie) jest właściwym źródłem prawdy,
		# gdy wypełniony — jawne "Nie" ZAWSZE wygrywa i tłumi metry na
		# wydruku, nawet gdy `dodatkowy_kabel_m` ma dodatnią wartość (formularz
		# niespójny): dokument prawny nie ma prawa sam sobie zaprzeczać.
		# Gdy Select jest pusty/nierozpoznany (umowy sprzed jego wprowadzenia),
		# wracamy do starej heurystyki: dodatnia liczba metrów = Tak.
		"kabel_tak": kabel_tak_wybrano or (not kabel_nie_wybrano and not kabel_mb_puste),
		"kabel_nie": kabel_nie_wybrano,
		"kabel_mb": "" if (kabel_nie_wybrano or kabel_mb_puste) else _liczba_calkowita(kabel_mb_dec),
		# Załącznik 1b
		"bateria_producent_model": _tekst(bateria_nazwa),
		"bateria_moc_kw": _liczba(_pole(bateria_komponent, "moc_kw")),
		# `bateria_pojemnosc_jedn_kwh`/`bateria_szt`: odczytane z konwencji
		# nazewnictwa katalogu przez `_bateria_szt_i_pojemnosc_jedn()` — patrz
		# jej docstring dla pełnych reguł (moduły równe/różne, literówka w
		# katalogu, model nierozpoznawalny).
		"bateria_pojemnosc_jedn_kwh": bateria_pojemnosc_jedn_kwh,
		"bateria_szt": bateria_szt,
		"bateria_pojemnosc_lacznie_kwh": _liczba(deal.get("custom_pojemnosc_kwh")),
		"bateria_gwarancja_lat": _liczba_calkowita(_pole(bateria_komponent, "gwarancja_lat")),
		"ist_pv_moc_inwertera_kw": _liczba(umowa.get("istniejaca_pv_moc_inwertera_kw")),
		"ist_pv_moc_kwp": _liczba(umowa.get("istniejaca_pv_moc_kwp")),
		"ist_pv_producent_inwertera": _tekst(umowa.get("istniejaca_pv_producent_inwertera")),
		# Załącznik 2
		"zgoda_telefon": zgoda_telefon_stan is True,
		"zgoda_promocja": zgoda_promocja_stan is True,
		# Załącznik 3
		"zgoda_wczesniejsza_realizacja": zgoda_wczesniejsza_realizacja_stan is True,
		# Bloki podpisów — Autenti dokleja jedno zbiorcze poświadczenie na
		# końcu pliku (jeden podpis elektroniczny obejmujący całość), więc
		# miejsca na podpis klienta w środku dokumentu wypełniamy za niego
		# drukowanymi literami; to oznaczenie strony, nie podpis prawny.
		# `.upper()` poprawnie zamienia polskie znaki (np. "ł"→"Ł").
		"podpis_zamawiajacy": klient_imie_nazwisko.upper(),
		"podpis_wykonawca": "PROENERGY",
		# Linia podpisu klienta na str. 9 (koniec Załącznika nr 4 - klauzula
		# RODO): "data i podpis" pod kreską — pre-drukowana data zawarcia umowy
		# + imię i nazwisko klienta wielkimi literami, decyzja produktowa
		# 2026-08-12. Brak nazwiska nigdy nie kasuje daty — tylko pomija
		# przecinek, który by go poprzedzał.
		"rodo_data_imie_nazwisko": ", ".join(
			c for c in (_data_pl(dzis), klient_imie_nazwisko.upper()) if c
		),
	}


def _pole(wiersz: dict[str, Any] | None, nazwa_pola: str) -> Any:
	"""Bezpieczny odczyt pola z wiersza, który może nie istnieć (`None`)."""
	if wiersz is None:
		return None
	return wiersz.get(nazwa_pola)


def _znajdz_komponent(
	komponenty: list[dict[str, Any]], kategoria: str, docelowa_nazwa: Any
) -> dict[str, Any] | None:
	"""Dopasowuje wiersz `Volteo Komponent` po kategorii i sklejonym `f"{nazwa} {model}"`.

	Struktura `Volteo Komponent` jest odwrotna do intuicji: `nazwa` bywa
	producentem (`"Sigenergy"`) a `model` resztą oznaczenia (`"TP2 6 kW"`) —
	dopasowanie działa niezależnie od tego podziału, bo porównuje sklejony
	string, dokładnie tak jak zapisano w `deal.custom_falownik`/`custom_bateria`/`custom_panel`.
	Zwraca `None`, gdy nazwa docelowa jest pusta albo żaden wiersz nie pasuje.
	"""
	docelowa = _tekst(docelowa_nazwa)
	if not docelowa:
		return None
	for wiersz in komponenty:
		if wiersz.get("kategoria") != kategoria:
			continue
		sklejone = f"{wiersz.get('nazwa') or ''} {wiersz.get('model') or ''}".strip()
		if sklejone == docelowa:
			return wiersz
	return None


def _ilosc_z_zestawu(zestaw: list[dict[str, Any]], docelowa_nazwa: Any) -> Any:
	"""Zwraca `ilosc` z wiersza `custom_zestaw`, którego `nazwa` pasuje dokładnie.

	Zwraca `None`, gdy nazwa docelowa jest pusta albo żaden wiersz nie pasuje —
	odróżnialne od legalnego `0` (który i tak zostanie potraktowany jak pustka
	przez `_liczba_calkowita`).
	"""
	docelowa = _tekst(docelowa_nazwa)
	if not docelowa:
		return None
	for wiersz in zestaw:
		if _tekst(wiersz.get("nazwa")) == docelowa:
			return wiersz.get("ilosc")
	return None


def _bateria_szt_i_pojemnosc_jedn(komponent: dict[str, Any] | None) -> tuple[str, str]:
	"""Odczytuje liczbe modulow baterii i pojemnosc pojedynczego modulu z `model`.

	Katalog koduje moduly w nawiasie na koncu `model` (np. "12 kWh (6+6)" = 2
	moduly po 6 kWh). Reguly, w kolejnosci sprawdzania:

	1. Brak dopasowanego komponentu albo brak/pusty `model` -> oba klucze puste.
	2. Nawias obecny (np. "(6+6)", "(6+9+9)"): liczba skladnikow -> sztuki.
	   Jesli suma skladnikow NIE zgadza sie z `pojemnosc_kwh` komponentu (np.
	   literowka w katalogu: "(6+6)" przy zapisanych 15 kWh) -> oba klucze
	   puste, nigdy nie zgadujemy ktora wartosc jest bledna. Jesli suma sie
	   zgadza i wszystkie skladniki sa rowne -> pojemnosc jednostkowa to ta
	   wspolna wartosc; jesli skladniki sa rozne -> pojemnosc jednostkowa to
	   lista skladnikow po przecinku (np. "6,6,9"), zeby dokument pokazywal
	   realny sklad zestawu zamiast udawac jedna wspolna wartosc.
	3. Brak nawiasu w ogole (np. "12 kWh", "T-BAT 5.8kWh"): jesli string mimo
	   to nie wyglada na zapis pojemnosci (nie zawiera "kWh") -> oba klucze
	   puste (model nierozpoznawalny, nigdy nie zgadujemy). W przeciwnym razie
	   pojedynczy modul: sztuki = 1, pojemnosc jednostkowa = pojemnosc
	   calkowita komponentu (albo puste, gdy ta jest sama pusta/zero).

	Zwraca gotowe do wydruku stringi (przez `_liczba`/`_liczba_calkowita`),
	nigdy surowe liczby. Uwaga do listy przecinkowej w regule 2: `_liczba`
	renderuje polskie przecinki dziesietne, wiec hipotetyczny modul o
	niecalkowitej pojemnosci bylby w takiej liscie wizualnie niejednoznaczny
	("6,5,9" - dwie liczby czy trzy?); dzis wzorzec `_WZORZEC_MODULOW_BATERII`
	dopasowuje wylacznie liczby calkowite w nawiasie, wiec format
	przecinkowo-rozdzielany jest tu swiadoma decyzja produktowa (zyczenie
	uzytkownika, 2026-08-12), nie ogolnym rozwiazaniem na przyszlosc.
	"""
	if komponent is None:
		return "", ""
	model = _tekst(komponent.get("model"))
	if not model:
		return "", ""
	calkowita = _sparsuj_decimal(komponent.get("pojemnosc_kwh"))

	dopasowanie = _WZORZEC_MODULOW_BATERII.search(model)
	if dopasowanie:
		skladniki = [Decimal(s) for s in dopasowanie.group(1).split("+")]
		if calkowita is None or sum(skladniki) != calkowita:
			return "", ""
		szt = _liczba_calkowita(len(skladniki))
		if all(s == skladniki[0] for s in skladniki):
			return szt, _liczba(skladniki[0])
		return szt, ",".join(_liczba(s) for s in skladniki)

	if "kwh" not in model.lower():
		return "", ""
	if calkowita is None or calkowita == 0:
		return "", ""
	return "1", _liczba(calkowita)


def _rowna(wartosc: Any, wzorzec: str) -> bool:
	"""Porównanie tekstowe odporne na białe znaki na brzegach i nie-stringi.

	Zwraca `False` dla `None`/nietekstowych wartości zamiast rzucać —
	nieznana wartość źródłowa nigdy nie ma zgadywać, że pasuje.
	"""
	return isinstance(wartosc, str) and wartosc.strip() == wzorzec


def _stan_bool(wartosc: Any) -> bool | None:
	"""Parsuje pole typu Check (0/1, `True`/`False`, albo string z tych wartości).

	Zwraca `None`, gdy stanu nie da się jednoznacznie ustalić (brak wartości
	albo tekst nieparsowalny jako liczba) — odróżnia to "nieznane" od
	jednoznacznego, zapisanego `0`. Wywołujący renderuje "nieznane" jako obie
	kratki puste, nigdy nie zgaduje domyślnej.
	"""
	if isinstance(wartosc, bool):
		return wartosc
	liczba = _sparsuj_decimal(wartosc)
	if liczba is None:
		return None
	return liczba != 0


def _tekst(wartosc: Any) -> str:
	"""Normalizuje dowolną wartość tekstową do gotowego do wydruku stringu.

	Reguły: `None` → `""`; białe znaki na brzegach ucięte; wartość, która po
	`.strip().upper()` zaczyna się od `"PLACEHOLDER"`, jest traktowana jak
	brak danych (baza zawiera dosłownie `"PLACEHOLDER — do uzupelnienia..."`
	w `panel_producent`/`panel_model`, dopóki admin ich nie uzupełni).
	"""
	if wartosc is None:
		return ""
	tekst = str(wartosc).strip()
	if tekst.upper().startswith("PLACEHOLDER"):
		return ""
	return tekst


def _polacz(*czesci: Any, sep: str = " ") -> str:
	"""Łączy niepuste, przefiltrowane przez `_tekst` fragmenty jednym separatorem."""
	niepuste = [c for c in (_tekst(c) for c in czesci) if c]
	return sep.join(niepuste)


def _data_pl(dzis: date) -> str:
	"""Formatuje datę jako `DD.MM.RRRR`."""
	return f"{dzis.day:02d}.{dzis.month:02d}.{dzis.year:04d}"


def _adres(ulica: Any, nr_domu: Any, nr_mieszkania: Any, kod: Any, miasto: Any) -> str:
	"""Składa adres z pól rozbitych (ulica/nr domu/nr mieszkania/kod/miasto).

	Każdy brakujący fragment jest po prostu pomijany — nigdy nie wstawia się
	pustego miejsca w stylu "ul. , 5". Zwraca `""`, gdy wszystkie pola są puste.
	"""
	ulica_t = _tekst(ulica)
	nr_domu_t = _tekst(nr_domu)
	nr_mieszkania_t = _tekst(nr_mieszkania)
	kod_t = _tekst(kod)
	miasto_t = _tekst(miasto)

	czesc_ulicy = ""
	if ulica_t:
		czesc_ulicy = f"ul. {ulica_t}"
		if nr_domu_t:
			czesc_ulicy += f" {nr_domu_t}"
	elif nr_domu_t:
		czesc_ulicy = nr_domu_t
	if nr_mieszkania_t and (ulica_t or nr_domu_t):
		czesc_ulicy += f"/{nr_mieszkania_t}"

	if kod_t and miasto_t:
		czesc_miasta = f"{kod_t} {miasto_t}"
	else:
		czesc_miasta = kod_t or miasto_t

	return ", ".join(c for c in (czesc_ulicy, czesc_miasta) if c)


def _adres_montazu_deal(deal: dict[str, Any]) -> str:
	"""Awaryjne złożenie adresu montażu z `CRM Deal`, gdy `Volteo Umowa` go nie ma.

	`custom_install_address` jest JEDNYM polem tekstowym (bez wydzielonego
	numeru domu — patrz komentarz w `crm/api/umowa.py::_PREFILL_MAPOWANIE`),
	więc tu tylko sklejamy je z kodem/miastem, bez próby wyciągania numeru.
	"""
	ulica_calosc = _tekst(deal.get("custom_install_address"))
	kod_t = _tekst(deal.get("custom_install_postal_code"))
	miasto_t = _tekst(deal.get("custom_install_city"))

	if kod_t and miasto_t:
		czesc_miasta = f"{kod_t} {miasto_t}"
	else:
		czesc_miasta = kod_t or miasto_t

	return ", ".join(c for c in (ulica_calosc, czesc_miasta) if c)


def _liczba(wartosc: Any) -> str:
	"""Formatuje moc/wymiar: zero i puste → `""`, bez zbędnych zer po przecinku.

	`5.0` → `"5"`, `4.5` → `"4,5"`. Wartości ujemne nie są oczekiwane w tej
	domenie, ale formatowanie ich nie psuje (znak zostaje przed liczbą).
	"""
	dec = _sparsuj_decimal(wartosc)
	if dec is None or dec == 0:
		return ""
	tekst = format(dec, "f")
	if "." in tekst:
		tekst = tekst.rstrip("0").rstrip(".")
	return tekst.replace(".", ",")


def _liczba_calkowita(wartosc: Any) -> str:
	"""Formatuje sztuki/lata gwarancji/mb: zero i puste → `""`, zawsze bez części dziesiętnej."""
	dec = _sparsuj_decimal(wartosc)
	if dec is None or dec == 0:
		return ""
	zaokraglona = dec.to_integral_value(rounding=ROUND_HALF_UP)
	return str(int(zaokraglona))


def _grupuj_tysiace(cyfry: str) -> str:
	"""Grupuje ciąg cyfr (część całkowita kwoty) po 3 od prawej, spacją nierozdzielającą."""
	n = len(cyfry)
	grupy = []
	while n > 3:
		grupy.append(cyfry[n - 3 : n])
		n -= 3
	grupy.append(cyfry[:n])
	return _NBSP.join(reversed(grupy))


def _kwota(wartosc: Any) -> str:
	"""Formatuje kwotę pieniężną: zero i puste → `""`, inaczej `"40 236,00"`.

	Zero jest tu pustką dla WSZYSTKICH czterech kwot umowy (netto, brutto,
	wkład własny, kwota kredytu) — zob. komentarz przy `_WSZYSTKO_ZERO_JEST_PUSTKA`
	na górze pliku dla uzasadnienia tej świadomej różnicy wobec `volteo_umowa.py`.
	"""
	dec = _sparsuj_decimal(wartosc)
	if dec is None or dec == 0:
		return ""
	zaokraglona = dec.quantize(_KWOTA_KWANT, rounding=ROUND_HALF_UP)
	znak = "-" if zaokraglona < 0 else ""
	zaokraglona = abs(zaokraglona)
	czesc_calkowita, _, czesc_dziesietna = format(zaokraglona, "f").partition(".")
	czesc_dziesietna = (czesc_dziesietna + "00")[:2]
	return f"{znak}{_grupuj_tysiace(czesc_calkowita)},{czesc_dziesietna}"
