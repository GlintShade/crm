# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy trzech map współrzędnych (`crm/volteo_umowa_mapa*.py`) — PVME, PV, ME.

Od zadania „umowa-szablony-typy” istnieją TRZY szablony PDF-u umowy i TRZY
osobne mapy współrzędnych, zarejestrowane w `crm.volteo_umowa_render.SZABLONY`.
Testy niżej pętlą się po TYM REJESTRZE (`for kod, szablon in SZABLONY.items():`),
nie po nazwach funkcji poszczególnych modułów (`pozycje_dla_pv` itp.) — te nazwy
mogą się jeszcze zmienić, `SZABLONY` jest stabilnym kontraktem. Zbiór kluczy
danej mapy liczymy więc lokalnie: `frozenset(pole.klucz for pole in szablon.mapa)`.
"""

import unittest
from datetime import date
from decimal import Decimal
from typing import Any

from crm.volteo_umowa_mapa import MAPA as MAPA_PVME
from crm.volteo_umowa_mapa import SZEROKOSC_STRONY_PT, WYSOKOSC_STRONY_PT, Pole
from crm.volteo_umowa_mapa_me import MAPA_ME
from crm.volteo_umowa_mapa_me2 import LICZBA_STRON_ME2, MAPA_ME2
from crm.volteo_umowa_mapa_pv import MAPA_PV
from crm.volteo_umowa_mapa_pv2 import LICZBA_STRON_PV2, MAPA_PV2
from crm.volteo_umowa_mapa_pvme2 import LICZBA_STRON_PVME2, MAPA_PVME2
from crm.volteo_umowa_pdf import zbuduj_kontekst
from crm.volteo_umowa_render import SZABLONY

# ---------------------------------------------------------------------------
# Wyjątki kontraktu dwukierunkowego, per szablon.
#
# Każdy szablon PDF-u ma inny zestaw załączników — klucz kontekstu, którego
# fizycznie nie ma gdzie wydrukować w danym dokumencie, jest tu jawnie
# wymieniony z uzasadnieniem. Brak wpisu = klucz MUSI mieć pozycję w mapie
# tego szablonu, inaczej dana po cichu zniknęłaby z wydruku.
# ---------------------------------------------------------------------------

KLUCZE_DRUGIEGO_ZAMAWIAJACEGO: frozenset[str] = frozenset(
	{
		"klient2_imie_nazwisko",
		"klient2_adres",
		"klient2_pesel",
		"klient2_telefon",
		"klient2_email",
		"podpis_zamawiajacy_2",
	}
)
"""Sześć kluczy drugiego Zamawiającego (ops#167): `zbuduj_kontekst()` je
zwraca ZAWSZE (puste bez `kontakt2`, zob. jej docstring), ale mają gdzie się
wydrukować WYŁĄCZNIE w wariantach PODWÓJNYCH (`PV_2`/`ME_2`/`PVME_2`). W
trzech wariantach JEDNOOSOBOWYCH (`PV`/`ME`/`PVME`) ten sześcioelementowy
zestaw jest więc wyjątkiem w KAŻDYM z nich, niezależnie od tego, jakie inne
klucze dany szablon pomija, stąd osobna stała, unijowana do wszystkich
trzech `WYJATKI_*` poniżej zamiast powtarzana ręcznie."""

WYJATKI_PVME: frozenset[str] = KLUCZE_DRUGIEGO_ZAMAWIAJACEGO
"""PV+ME to superset — ma Załącznik 1a (panele) I Załącznik 1b (bateria), więc
poza sześcioma kluczami drugiego Zamawiającego (ten szablon jest JEDNO-
osobowy) żaden klucz kontekstu nie jest tu fizycznie nieobecny."""

WYJATKI_PV: frozenset[str] = frozenset(
	{
		"bateria_producent_model",
		"bateria_moc_kw",
		"bateria_pojemnosc_jedn_kwh",
		"bateria_szt",
		"bateria_pojemnosc_lacznie_kwh",
		"bateria_gwarancja_lat",
	}
) | KLUCZE_DRUGIEGO_ZAMAWIAJACEGO
"""Szablon PV (`umowa_pv.pdf`) nie ma Załącznika dotyczącego magazynu energii —
te sześć kluczy `bateria_*` nie ma więc gdzie się wydrukować (zob. docstring
`MAPA_PV` w `crm/volteo_umowa_mapa_pv.py`), plus sześć kluczy drugiego
Zamawiającego, bo ten szablon jest JEDNOosobowy (`PV_2` istnieje osobno)."""

WYJATKI_ME: frozenset[str] = frozenset(
	{
		"panel_moc_wp",
		"panel_szt",
		"moc_pv_kwp",
		"panel_producent_model",
		"panel_gwarancja_lat",
		"inwerter_szt",
		"montaz_dach",
		"montaz_grunt",
		"pokrycie_dachowe",
		"odgromowa_tak",
		"odgromowa_nie",
		"ppoz_tak",
		"ppoz_nie",
		"przekop_tak",
		"przekop_mb",
		"przekop_nie",
		"kabel_tak",
		"kabel_mb",
		"kabel_nie",
	}
) | KLUCZE_DRUGIEGO_ZAMAWIAJACEGO
"""Szablon ME (`umowa_me.pdf`) opisuje sprzedaż/montaż magazynu energii BEZ
fotowoltaiki — nie ma sekcji paneli/inwertera-do-PV/montażu dachowego/instalacji
odgromowej/ppoż/przekopu/dodatkowego kabla (te elementy montażowe dotyczą
wyłącznie instalacji PV), więc żaden z tych 19 kluczy nie ma gdzie się
wydrukować (zob. docstring `MAPA_ME` w `crm/volteo_umowa_mapa_me.py`), plus
sześć kluczy drugiego Zamawiającego, bo ten szablon jest JEDNOosobowy (`ME_2`
istnieje osobno)."""

WYJATKI_BRAK_POZYCJI_WG_SZABLONU: dict[str, frozenset[str]] = {
	"PVME": WYJATKI_PVME,
	"PV": WYJATKI_PV,
	"ME": WYJATKI_ME,
	# Warianty PODWÓJNE (ops#167) mają STRUKTURALNIE ten sam zestaw
	# załączników co ich odpowiednik jednoosobowy (drugi Zamawiający dokłada
	# pozycje, nie zmienia jakie produkty/sekcje szablon opisuje), te same
	# wyjątki co dla kodu bazowego, MINUS sześć kluczy drugiego Zamawiającego:
	# w przeciwieństwie do wariantu jednoosobowego, mapa podwójna MA dla nich
	# pozycję (to właśnie różnica między tymi dwoma wariantami), więc tu nie
	# są wyjątkiem.
	"PV_2": WYJATKI_PV - KLUCZE_DRUGIEGO_ZAMAWIAJACEGO,
	"PVME_2": WYJATKI_PVME - KLUCZE_DRUGIEGO_ZAMAWIAJACEGO,
	"ME_2": WYJATKI_ME - KLUCZE_DRUGIEGO_ZAMAWIAJACEGO,
}

# ---------------------------------------------------------------------------
# Oczekiwane strony (indeksy 0-based) dla reguł specyficznych dla układu
# strony, per szablon — wyznaczone z komentarzy zamykających każdą mapę
# (`crm/volteo_umowa_mapa*.py`, sekcja „strony bez pozycji”/bloki podpisów).
# ---------------------------------------------------------------------------

_PELNOMOCNICTWO_IDX: dict[str, int] = {
	"PVME": 17,
	"PV": 13,
	"ME": 13,
	# Warianty PODWÓJNE (ops#167): to jest PIERWSZE Pełnomocnictwo (klient 1,
	# `klient_*`/`podpis_zamawiajacy` bez `_2`), DRUGIE Pełnomocnictwo (klient
	# 2) leży o jedną stronę dalej, ostatnia strona każdego wariantu
	# podwójnego (zob. `_PELNOMOCNICTWO_2_IDX_PODWOJNE` niżej, `TestMapyPodwojne`).
	"PV_2": 13,
	"ME_2": 13,
	"PVME_2": 18,
}
"""Pierwszy załącznik Pełnomocnictwa OSD (klient 1) każdego szablonu: jedyna
strona (obok jego bliźniaczej pary dla klienta 2 w wariantach podwójnych) z
linią podpisu WYŁĄCZNIE Zamawiającego (Mocodawcy), bez Wykonawcy."""

_ZAKAZANE_STRONY_PROTOKOLOW: dict[str, frozenset[int]] = {
	# PVME: formularz odstąpienia (idx9) + oba protokoły odbioru + listy
	# szkoleniowe/pomiarowe (idx10-16) — wypełnia je instalator/klient po
	# montażu, nigdy generator z góry.
	"PVME": frozenset(range(9, 17)),
	# PV i ME: formularz odstąpienia (idx9) + JEDEN protokół odbioru + listy
	# szkoleniowe/pomiarowe (idx10-12) — o cztery strony krócej niż PVME, bo
	# oba szablony mają tylko jeden produkt do odebrania.
	"PV": frozenset(range(9, 13)),
	"ME": frozenset(range(9, 13)),
	# Warianty PODWÓJNE (ops#167): drugi blok komparycji na stronie 1 przesuwa
	# treść w dół, więc te same sekcje (pouczenie o odstąpieniu, formularz,
	# protokoły) wypadają o jedną stronę dalej niż w wariancie jednoosobowym
	# (zmierzone bezpośrednio z komentarzy `crm/volteo_umowa_mapa_*2.py`).
	"PV_2": frozenset(range(8, 13)),
	"ME_2": frozenset(range(8, 13)),
	"PVME_2": frozenset(range(10, 18)),
}
"""Strony formularza odstąpienia i protokołów odbioru — generator nie ma
prawa wydrukować tam żadnego podpisu z góry, bo poświadczałoby to coś, co się
jeszcze nie wydarzyło (decyzja produktowa, zob. docstringi map)."""

_ZALACZNIK_2_3_IDX: dict[str, int] = {
	"PVME": 6,
	"PV": 5,
	"ME": 5,
	"PV_2": 5,
	"ME_2": 5,
	"PVME_2": 7,
}
"""Strona, na której razem leżą Załącznik nr 2 (zgody) i Załącznik nr 3
(oświadczenie o realizacji przed odstąpieniem) — obie mają WŁASNĄ, osobną
linię podpisu Zamawiającego (bez Wykonawcy), stąd dwie różne pozycje tego
samego klucza na jednej stronie (w wariantach podwójnych: cztery, po dwie
na osobę)."""

_STRONY_ZAMAWIAJACY_OCZEKIWANE: dict[str, frozenset[int]] = {
	"PVME": frozenset({3, 4, 5, 6, 17}),
	"PV": frozenset({3, 4, 5, 13}),
	"ME": frozenset({3, 4, 5, 13}),
	# Warianty PODWÓJNE (ops#167): strony `podpis_zamawiajacy` (osoba 1, BEZ
	# `_2`); zob. `_STRONY_ZAMAWIAJACY_2_OCZEKIWANE` (`TestMapyPodwojne`) dla
	# osoby 2.
	"PV_2": frozenset({3, 4, 5, 13}),
	"ME_2": frozenset({3, 4, 5, 13}),
	"PVME_2": frozenset({3, 5, 6, 7, 18}),
}
"""Strony z co najmniej jedną pozycją `podpis_zamawiajacy`: umowa główna,
Załącznik(i) montażowy(e), Załącznik 2/3 (zgody), Pełnomocnictwo."""

_STRONY_WYKONAWCA_OCZEKIWANE: dict[str, frozenset[int]] = {
	"PVME": frozenset({3, 4, 5}),
	"PV": frozenset({3, 4}),
	"ME": frozenset({3, 4}),
	"PV_2": frozenset({3, 4}),
	"ME_2": frozenset({3, 4}),
	"PVME_2": frozenset({3, 5, 6}),
}
"""Strony z co najmniej jedną pozycją `podpis_wykonawca`: umowa główna i
Załącznik(i) montażowy(e) — NIGDY Załącznik 2/3 (jednostronne oświadczenia
klienta) ani Pełnomocnictwo (jednostronne wobec ProEnergy)."""

_KLIENT_IMIE_NAZWISKO_STRONY: dict[str, frozenset[int]] = {
	"PVME": frozenset({0, 17}),
	"PV": frozenset({0, 13}),
	"ME": frozenset({0, 13}),
	"PV_2": frozenset({0, 13}),
	"ME_2": frozenset({0, 13}),
	"PVME_2": frozenset({0, 18}),
}
"""Imię i nazwisko klienta drukuje się w komparycji (pierwsza strona) i w
Pełnomocnictwie (ostatnia dla wariantu jednoosobowego, przedostatnia dla
wariantu podwójnego, klient 1 nie ma swojego Pełnomocnictwa na SAMYM końcu,
to miejsce zajmuje Pełnomocnictwo klienta 2), protokoły odbioru od b44 są
celowo puste, więc dane klienta się tam już NIE powtarzają, w żadnym z
sześciu szablonów."""

_RODO_STRONA_IDX: dict[str, int] = {
	"PVME": 8,
	"PV": 7,
	"ME": 7,
	"PV_2": 7,
	"ME_2": 7,
	"PVME_2": 9,
}
"""Strona z linią podpisu klienta na końcu Załącznika RODO
(`rodo_data_imie_nazwisko`) — w PVME to strona 9 (Załącznik 4 zajmuje dwie
strony, 8 i 9), w PV/ME to strona 8 (Załącznik 4 tam mieści się inaczej, więc
linia podpisu wypada o jedną stronę wcześniej). Warianty podwójne: ten sam
klucz drukuje się TYLKO dla osoby 1 (zob. docstring `zbuduj_kontekst` w
`crm/volteo_umowa_pdf.py`), PV_2/ME_2 wypadają na tej samej stronie co ich
odpowiednik jednoosobowy, PVME_2 o jedną stronę dalej niż PVME (drugi blok
komparycji przesuwa całą resztę treści o jedną stronę)."""


def _klucze_mapy(szablon: Any) -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `szablon.mapa` (bez duplikatów)."""
	return frozenset(pole.klucz for pole in szablon.mapa)


def _pozycje(szablon: Any, klucz: str) -> tuple[Pole, ...]:
	"""Wszystkie pozycje `Pole` w `szablon.mapa` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in szablon.mapa if pole.klucz == klucz)


def _umowa(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"adres_zam_jak_montaz": "Nie",
		"adres_zam_ulica": "Kwiatowa",
		"adres_zam_nr_domu": "5",
		"adres_zam_nr_mieszkania": "",
		"adres_zam_kod": "00-001",
		"adres_zam_miasto": "Warszawa",
		"adres_montaz_ulica": "Polna",
		"adres_montaz_nr_domu": "10",
		"adres_montaz_nr_mieszkania": "",
		"adres_montaz_kod": "02-002",
		"adres_montaz_miasto": "Kraków",
		"typ_budynku": "Jednorodzinny",
		"powierzchnia_prog": "powyżej 300 m²",
		"powierzchnia_m2": Decimal("350"),
		"finansowanie": "Kredyt + gotówka",
		"wklad_wlasny_pln": Decimal("5000"),
		"kwota_kredytu_pln": Decimal("35236"),
		"internet": "Wi-Fi",
		"instalacja_odgromowa": "Tak",
		"moc_przylaczeniowa_kw": Decimal("8.5"),
		"liczba_faz": "3",
		"przekop_gruntowy": "Tak",
		"dodatkowy_kabel_m": 12,
		"ppoz_wymagane": 1,
		"istniejaca_pv": "Tak",
		"istniejaca_pv_moc_inwertera_kw": Decimal("4.0"),
		"istniejaca_pv_moc_kwp": Decimal("3.5"),
		"istniejaca_pv_producent_inwertera": "Fronius",
		"zgoda_kontakt_telefoniczny": 1,
		"zgoda_dzialania_promocyjne": 1,
		"zgoda_realizacja_przed_odstapieniem": 1,
	}
	baza.update(nadpisania)
	return baza


def _deal(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"name": "PRO/PVME/26/1000",
		"deal_value": Decimal("43454.88"),
		"custom_netto": Decimal("40236.0"),
		"custom_pv_power_kwp": Decimal("5.0"),
		"custom_panele": 10,
		"custom_falownik": "Sigenergy TP2 6 kW",
		"custom_bateria": "Sigenergy 12 kWh (6+6)",
		"custom_pojemnosc_kwh": Decimal("12.0"),
		"custom_konstrukcja": "Dach skośny - blacha",
		"custom_install_address": "",
		"custom_install_city": "",
		"custom_install_postal_code": "",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"first_name": "Jan",
		"last_name": "Kowalski",
		"custom_pesel": "90010112345",
		"mobile_no": "500600700",
		"email": "jan@example.com",
	}
	baza.update(nadpisania)
	return baza


def _zestaw() -> list[dict[str, Any]]:
	return [
		{"typ": "Falownik", "nazwa": "Sigenergy TP2 6 kW", "ilosc": 1},
		{"typ": "Panele PV", "nazwa": "Panel PV", "ilosc": 10},
	]


def _komponenty() -> list[dict[str, Any]]:
	return [
		{
			"kategoria": "Falownik",
			"nazwa": "Sigenergy",
			"model": "TP2 6 kW",
			"producent": "Sigenergy",
			"moc_kw": Decimal("6.0"),
			"gwarancja_lat": 12,
		},
		{
			"kategoria": "Magazyn energii",
			"nazwa": "Sigenergy",
			"model": "12 kWh (6+6)",
			"producent": "Sigenergy",
			"moc_kw": Decimal("6.0"),
			"pojemnosc_kwh": Decimal("12"),
			"gwarancja_lat": 10,
		},
	]


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"panel_producent": "Longi",
		"panel_model": "Hi-MO 6",
		"panel_moc_wp": 440,
		"panel_gwarancja_lat": 25,
	}
	baza.update(nadpisania)
	return baza


def _pelny_kontekst() -> dict[str, Any]:
	"""Kontekst z WSZYSTKIMI polami wypełnionymi ("bogaty" wariant), żeby żadna
	wartość nie wypadła jako pusta z powodu reguły "zero/brak = pustka" —
	inaczej test kluczy-bez-pozycji nie odróżniałby "brak pozycji w mapie"
	od "wartość akurat pusta w tym fixture." Kontekst jest ten sam dla WSZYSTKICH
	trzech szablonów — `zbuduj_kontekst` nie zna pojęcia "szablon", zawsze zwraca
	pełny zestaw kluczy; to mapa decyduje, które z nich mają gdzie wylądować."""
	return zbuduj_kontekst(
		_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), date(2026, 8, 6)
	)


class TestKlucze(unittest.TestCase):
	def test_a_kazdy_klucz_mapy_istnieje_w_kontekscie(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_kontekstu = set(kontekst.keys())
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertIn(
						pole.klucz,
						klucze_kontekstu,
						f"[{kod}] MAPA odwołuje się do klucza {pole.klucz!r}, którego nie ma w zbuduj_kontekst()",
					)

	def test_b_kazdy_klucz_kontekstu_ma_pozycje_albo_jawny_wyjatek(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				klucze_mapy = _klucze_mapy(szablon)
				wyjatki = WYJATKI_BRAK_POZYCJI_WG_SZABLONU[kod]
				for klucz in kontekst:
					if klucz in wyjatki:
						continue
					self.assertIn(
						klucz,
						klucze_mapy,
						f"[{kod}] Klucz {klucz!r} nie ma żadnej pozycji w mapie i nie jest w wyjątkach "
						"— dana po cichu zniknęłaby z wydrukowanego dokumentu.",
					)

	def test_c_wyjatki_i_mapa_sie_nie_pokrywaja(self: "TestKlucze") -> None:
		# Klucz nie może być jednocześnie "świadomie pominięty" i obecny w mapie —
		# to by znaczyło, że komentarz uzasadniający wyjątek jest nieaktualny.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				wyjatki = WYJATKI_BRAK_POZYCJI_WG_SZABLONU[kod]
				self.assertEqual(wyjatki & _klucze_mapy(szablon), frozenset())

	def test_d_wszystkie_wyjatki_sa_prawdziwymi_kluczami_kontekstu(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		for kod in SZABLONY:
			with self.subTest(kod=kod):
				for klucz in WYJATKI_BRAK_POZYCJI_WG_SZABLONU[kod]:
					self.assertIn(klucz, kontekst)


class TestGeometria(unittest.TestCase):
	def test_a_strona_w_zakresie(self: "TestGeometria") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertGreaterEqual(pole.strona, 0, pole)
					self.assertLess(pole.strona, szablon.liczba_stron, pole)

	def test_b_x_w_granicach_strony(self: "TestGeometria") -> None:
		# Wszystkie trzy szablony to A4 596x842 pt — stałe importowane z
		# `crm.volteo_umowa_mapa` są więc wspólne dla wszystkich trzech map.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertGreaterEqual(pole.x, 0.0, pole)
					self.assertLessEqual(pole.x, SZEROKOSC_STRONY_PT, pole)

	def test_c_y_w_granicach_strony(self: "TestGeometria") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertGreaterEqual(pole.y, 0.0, pole)
					self.assertLessEqual(pole.y, WYSOKOSC_STRONY_PT, pole)

	def test_d_maks_szerokosc_nie_wychodzi_poza_strone(self: "TestGeometria") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					if pole.maks_szerokosc is None:
						continue
					self.assertGreater(pole.maks_szerokosc, 0.0, pole)
					self.assertLessEqual(pole.x + pole.maks_szerokosc, SZEROKOSC_STRONY_PT + 1.0, pole)

	def test_e_rozmiar_fontu_dodatni_i_sensowny(self: "TestGeometria") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertGreater(pole.rozmiar, 0.0, pole)
					self.assertLess(pole.rozmiar, 24.0, pole)


class TestRodzajIWyrownanie(unittest.TestCase):
	def test_a_rodzaj_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertIn(pole.rodzaj, ("tekst", "kratka"), pole)

	def test_b_wyrownanie_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					self.assertIn(pole.wyrownanie, ("lewo", "srodek", "prawo"), pole)

	def test_c_kratki_sa_wyrownane_do_srodka(self: "TestRodzajIWyrownanie") -> None:
		# Kratka to pojedynczy znak "X" rysowany w środku kwadratu — mapa
		# zawsze podaje jego środek, więc wyrównanie musi być "srodek".
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					if pole.rodzaj == "kratka":
						self.assertEqual(pole.wyrownanie, "srodek", pole)

	def test_d_kratki_nie_maja_maks_szerokosci(self: "TestRodzajIWyrownanie") -> None:
		# maks_szerokosc słuzy do przycinania/zawijania długich wartości tekstowych
		# — nie ma zastosowania do pojedynczego znaku "X" w kratce.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for pole in szablon.mapa:
					if pole.rodzaj == "kratka":
						self.assertIsNone(pole.maks_szerokosc, pole)

	def test_e_klucze_logiczne_kontekstu_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for klucz, wartosc in kontekst.items():
					if not isinstance(wartosc, bool):
						continue
					for pole in _pozycje(szablon, klucz):
						self.assertEqual(
							pole.rodzaj,
							"kratka",
							f"[{kod}] {klucz!r} zwraca bool w zbuduj_kontekst(), ale mapa oznacza go jako "
							f"{pole.rodzaj!r} na stronie {pole.strona}",
						)

	def test_f_klucze_tekstowe_kontekstu_nie_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				for klucz, wartosc in kontekst.items():
					if not isinstance(wartosc, str):
						continue
					for pole in _pozycje(szablon, klucz):
						self.assertEqual(
							pole.rodzaj,
							"tekst",
							f"[{kod}] {klucz!r} zwraca str w zbuduj_kontekst(), ale mapa oznacza go jako "
							f"{pole.rodzaj!r} na stronie {pole.strona}",
						)


class TestWielokrotnePozycje(unittest.TestCase):
	def test_a_dane_klienta_powtarzaja_sie_na_wielu_stronach(self: "TestWielokrotnePozycje") -> None:
		# Imię i nazwisko klienta drukuje się w komparycji i w pełnomocnictwie —
		# protokoły odbioru od b44 są celowo puste (decyzja produktowa: wypełnia
		# je instalator po montażu), więc dane klienta się tam już NIE powtarzają,
		# w żadnym z trzech szablonów. Regresja tego testu = ktoś przypadkiem
		# usunął/dodał pozycję przy edycji mapy.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				strony = {pole.strona for pole in _pozycje(szablon, "klient_imie_nazwisko")}
				self.assertEqual(strony, _KLIENT_IMIE_NAZWISKO_STRONY[kod])

	def test_b_zero_duplikatow_tej_samej_pozycji(self: "TestWielokrotnePozycje") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				widziane: set[tuple[str, int, float, float]] = set()
				for pole in szablon.mapa:
					klucz_pozycji = (pole.klucz, pole.strona, pole.x, pole.y)
					self.assertNotIn(klucz_pozycji, widziane, f"[{kod}] Zduplikowana pozycja: {pole}")
					widziane.add(klucz_pozycji)

	def test_c_rodo_data_imie_nazwisko_jedna_pozycja(self: "TestWielokrotnePozycje") -> None:
		# Linia podpisu klienta na końcu Załącznika RODO — jedna pozycja w
		# każdym szablonie. Regresja tego testu = ktoś przesunął pozycję przy
		# przyszłej edycji mapy, bez zauważenia że to zmienia stronę wydruku.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				pozycje = _pozycje(szablon, "rodo_data_imie_nazwisko")
				self.assertEqual(len(pozycje), 1)
				self.assertEqual(pozycje[0].strona, _RODO_STRONA_IDX[kod])


class TestPoleDataclass(unittest.TestCase):
	def test_a_pole_jest_niemutowalny(self: "TestPoleDataclass") -> None:
		pole = Pole("test_klucz", 0, 10.0, 10.0, "tekst")
		with self.assertRaises(Exception):
			pole.x = 20.0  # type: ignore[misc]

	def test_b_kazda_mapa_nie_jest_pusta(self: "TestPoleDataclass") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				self.assertGreater(len(szablon.mapa), 50)


class TestPodpisy(unittest.TestCase):
	"""Pozycje `podpis_zamawiajacy`/`podpis_wykonawca`, wspólne reguły dla
	wszystkich trzech szablonów PDF-u umowy."""

	def test_a_oba_klucze_maja_przynajmniej_jedna_pozycje(self: "TestPodpisy") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				self.assertGreater(len(_pozycje(szablon, "podpis_zamawiajacy")), 0)
				self.assertGreater(len(_pozycje(szablon, "podpis_wykonawca")), 0)

	def test_b_zadna_pozycja_podpisu_nie_lezy_na_stronach_protokolow_odbioru(
		self: "TestPodpisy",
	) -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				zakazane_strony = _ZAKAZANE_STRONY_PROTOKOLOW[kod]
				for klucz in ("podpis_zamawiajacy", "podpis_wykonawca"):
					for pole in _pozycje(szablon, klucz):
						self.assertNotIn(
							pole.strona,
							zakazane_strony,
							f"[{kod}] {klucz!r} ma pozycję na stronie {pole.strona} (protokół/odstąpienie) — "
							"instalator/klient wypełnia to pole, nie ProEnergy z góry.",
						)

	def test_c_wykonawca_nie_wystepuje_na_stronie_pelnomocnictwa(self: "TestPodpisy") -> None:
		# Pełnomocnictwo ma tylko jedną linię podpisu - Mocodawcy (klienta) -
		# to jednostronne oświadczenie, więc ProEnergy się tam nie podpisuje.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				strony_wykonawcy = {pole.strona for pole in _pozycje(szablon, "podpis_wykonawca")}
				self.assertNotIn(_PELNOMOCNICTWO_IDX[kod], strony_wykonawcy)

	def test_d_zamawiajacy_wystepuje_na_stronie_pelnomocnictwa(self: "TestPodpisy") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				strony_zamawiajacego = {pole.strona for pole in _pozycje(szablon, "podpis_zamawiajacy")}
				self.assertIn(_PELNOMOCNICTWO_IDX[kod], strony_zamawiajacego)

	def test_e_podpisy_na_oczekiwanych_stronach_umowy_i_zalacznikow(self: "TestPodpisy") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				strony_zamawiajacego = {pole.strona for pole in _pozycje(szablon, "podpis_zamawiajacy")}
				strony_wykonawcy = {pole.strona for pole in _pozycje(szablon, "podpis_wykonawca")}
				self.assertEqual(strony_zamawiajacego, _STRONY_ZAMAWIAJACY_OCZEKIWANE[kod])
				self.assertEqual(strony_wykonawcy, _STRONY_WYKONAWCA_OCZEKIWANE[kod])

	def test_f_zalacznik_2_i_3_maja_po_jednej_odrebnej_pozycji(self: "TestPodpisy") -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				strona_idx = _ZALACZNIK_2_3_IDX[kod]
				pozycje_strony = [
					pole for pole in _pozycje(szablon, "podpis_zamawiajacy") if pole.strona == strona_idx
				]
				self.assertEqual(len(pozycje_strony), 2)
				self.assertNotEqual(pozycje_strony[0].y, pozycje_strony[1].y)


# ---------------------------------------------------------------------------
# Mapy PODWÓJNE (issue #166) - dwóch Zamawiających, `MAPA_PV2`/`MAPA_ME2`/
# `MAPA_PVME2`. Te trzy mapy NIE są jeszcze zarejestrowane w `SZABLONY`
# (issue #167 rejestruje je razem ze zmianą `zbuduj_kontekst`), więc poniższe
# testy odwołują się do nich BEZPOŚREDNIO, importowane z modułów, nie przez
# pętlę po `SZABLONY` jak reszta tego pliku. `TestWariantyPodwojneJeszczeNie
# Zarejestrowane` w `crm/test_volteo_umowa_szablony_podwojne.py` jest strażnikiem
# tego stanu (G6) - ten plik go nie dubluje.
# ---------------------------------------------------------------------------

_MAPY_PODWOJNE: dict[str, Any] = {
	"PV2": {"mapa": MAPA_PV2, "liczba_stron": LICZBA_STRON_PV2, "mapa_jednoosobowa": MAPA_PV},
	"ME2": {"mapa": MAPA_ME2, "liczba_stron": LICZBA_STRON_ME2, "mapa_jednoosobowa": MAPA_ME},
	"PVME2": {"mapa": MAPA_PVME2, "liczba_stron": LICZBA_STRON_PVME2, "mapa_jednoosobowa": MAPA_PVME},
}

_KLUCZE_DODATKOWE_PODWOJNE: frozenset[str] = frozenset(
	{
		"klient2_imie_nazwisko",
		"klient2_adres",
		"klient2_pesel",
		"klient2_telefon",
		"klient2_email",
		"podpis_zamawiajacy_2",
	}
)
"""Jedyny dozwolony dodatek kluczy w wariancie podwójnym wobec odpowiadającej
mapy jednoosobowej (zob. brief issue #166) - każdy klucz mapy podwójnej, który
nie jest w tym zbiorze, MUSI też istnieć w kluczach mapy jednoosobowej."""

_LICZBA_POZYCJI_OCZEKIWANA: dict[str, int] = {"PV2": 81, "ME2": 68, "PVME2": 90}
"""Dokładna liczba pozycji w każdej mapie podwójnej, potwierdzona przy
pomiarze (issue #166) - regresja tego testu = ktoś przypadkiem dodał/usunął
pozycję przy przyszłej edycji mapy, bez zauważenia zmiany w liczbie."""

_STRONY_ZAMAWIAJACY_2_OCZEKIWANE: dict[str, frozenset[int]] = {
	"PV2": frozenset({3, 4, 5, 7, 14}),
	"ME2": frozenset({3, 4, 5, 7, 14}),
	"PVME2": frozenset({3, 5, 6, 7, 9, 19}),
}
"""Strony z co najmniej jedną pozycją `podpis_zamawiajacy_2`: umowa główna,
Załącznik(i) montażowy(e), Załącznik 2/3 (zgody), Załącznik 4 (RODO) i drugie
Pełnomocnictwo (ostatnia strona każdego wariantu)."""

_PELNOMOCNICTWO_1_IDX_PODWOJNE: dict[str, int] = {"PV2": 13, "ME2": 13, "PVME2": 18}
"""Pierwsze Pełnomocnictwo (klient 1, `klient_*`/`podpis_zamawiajacy`) -
przedostatnia strona każdego wariantu podwójnego."""

_PELNOMOCNICTWO_2_IDX_PODWOJNE: dict[str, int] = {"PV2": 14, "ME2": 14, "PVME2": 19}
"""Drugie Pełnomocnictwo (klient 2, `klient2_*`/`podpis_zamawiajacy_2`) -
OSTATNIA strona każdego wariantu podwójnego."""


class TestMapyPodwojne(unittest.TestCase):
	"""Piny geometryczne i kontraktowe dla `MAPA_PV2`/`MAPA_ME2`/`MAPA_PVME2`
	(issue #166) - analogiczne do `TestGeometria`/`TestPodpisy`/`TestWielokrotne
	Pozycje` powyżej, ale wyliczone bezpośrednio z modułów map (nieobecnych
	jeszcze w `SZABLONY`, zob. komentarz nad tą klasą)."""

	def test_a_strona_w_zakresie(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				for pole in dane["mapa"]:
					self.assertGreaterEqual(pole.strona, 0, pole)
					self.assertLess(pole.strona, dane["liczba_stron"], pole)

	def test_b_wspolrzedne_w_granicach_strony(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				for pole in dane["mapa"]:
					self.assertGreaterEqual(pole.x, 0.0, pole)
					self.assertLessEqual(pole.x, SZEROKOSC_STRONY_PT, pole)
					self.assertGreaterEqual(pole.y, 0.0, pole)
					self.assertLessEqual(pole.y, WYSOKOSC_STRONY_PT, pole)

	def test_c_zero_duplikatow_tej_samej_pozycji(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				widziane: set[tuple[str, int, float, float]] = set()
				for pole in dane["mapa"]:
					klucz_pozycji = (pole.klucz, pole.strona, pole.x, pole.y)
					self.assertNotIn(klucz_pozycji, widziane, f"[{kod}] Zduplikowana pozycja: {pole}")
					widziane.add(klucz_pozycji)

	def test_d_liczba_pozycji_scisle_wieksza_niz_mapa_jednoosobowa(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				self.assertGreater(len(dane["mapa"]), len(dane["mapa_jednoosobowa"]))
				self.assertEqual(len(dane["mapa"]), _LICZBA_POZYCJI_OCZEKIWANA[kod])

	def test_e_kazdy_klucz_w_mapie_jednoosobowej_albo_w_dozwolonych_dodatkach(
		self: "TestMapyPodwojne",
	) -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				klucze_jednoosobowe = frozenset(pole.klucz for pole in dane["mapa_jednoosobowa"])
				for pole in dane["mapa"]:
					self.assertTrue(
						pole.klucz in klucze_jednoosobowe or pole.klucz in _KLUCZE_DODATKOWE_PODWOJNE,
						f"[{kod}] Klucz {pole.klucz!r} nie jest ani w mapie jednoosobowej, ani w "
						"dozwolonych dodatkach dwuosobowych.",
					)

	def test_f_oba_podpisy_zamawiajacego_maja_pozycje(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				mapa = dane["mapa"]
				self.assertGreater(len([p for p in mapa if p.klucz == "podpis_zamawiajacy"]), 0)
				self.assertGreater(len([p for p in mapa if p.klucz == "podpis_zamawiajacy_2"]), 0)
				self.assertGreater(len([p for p in mapa if p.klucz == "podpis_wykonawca"]), 0)

	def test_g_strony_podpisu_zamawiajacego_2_zgodne_z_oczekiwaniem(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				strony = {pole.strona for pole in dane["mapa"] if pole.klucz == "podpis_zamawiajacy_2"}
				self.assertEqual(strony, _STRONY_ZAMAWIAJACY_2_OCZEKIWANE[kod])

	def test_h_pierwsze_pelnomocnictwo_uzywa_klient_i_podpisu_1(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				idx = _PELNOMOCNICTWO_1_IDX_PODWOJNE[kod]
				mapa = dane["mapa"]
				self.assertIn(
					idx, {p.strona for p in mapa if p.klucz == "klient_imie_nazwisko"}
				)
				self.assertIn(idx, {p.strona for p in mapa if p.klucz == "podpis_zamawiajacy"})
				# Pierwsze pelnomocnictwo NIE uzywa kluczy klient2_*/podpis_zamawiajacy_2.
				for pole in mapa:
					if pole.strona == idx:
						self.assertNotIn(pole.klucz, _KLUCZE_DODATKOWE_PODWOJNE, pole)

	def test_i_drugie_pelnomocnictwo_uzywa_klient2_i_podpisu_2(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				idx = _PELNOMOCNICTWO_2_IDX_PODWOJNE[kod]
				mapa = dane["mapa"]
				self.assertIn(
					idx, {p.strona for p in mapa if p.klucz == "klient2_imie_nazwisko"}
				)
				self.assertIn(idx, {p.strona for p in mapa if p.klucz == "podpis_zamawiajacy_2"})
				# Drugie pelnomocnictwo NIE uzywa kluczy klient_*/podpis_zamawiajacy (bez _2).
				for pole in mapa:
					if pole.strona == idx:
						self.assertNotIn(pole.klucz, ("klient_imie_nazwisko", "klient_adres", "klient_pesel", "podpis_zamawiajacy"), pole)

	def test_j_klient_imie_nazwisko_na_stronie_0_i_pierwszym_pelnomocnictwie(
		self: "TestMapyPodwojne",
	) -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				strony = {p.strona for p in dane["mapa"] if p.klucz == "klient_imie_nazwisko"}
				self.assertEqual(strony, {0, _PELNOMOCNICTWO_1_IDX_PODWOJNE[kod]})

	def test_k_klient2_imie_nazwisko_na_stronie_0_i_drugim_pelnomocnictwie(
		self: "TestMapyPodwojne",
	) -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				strony = {p.strona for p in dane["mapa"] if p.klucz == "klient2_imie_nazwisko"}
				self.assertEqual(strony, {0, _PELNOMOCNICTWO_2_IDX_PODWOJNE[kod]})

	def test_l_rodzaj_i_wyrownanie_dozwolone(self: "TestMapyPodwojne") -> None:
		for kod, dane in _MAPY_PODWOJNE.items():
			with self.subTest(kod=kod):
				for pole in dane["mapa"]:
					self.assertIn(pole.rodzaj, ("tekst", "kratka"), pole)
					self.assertIn(pole.wyrownanie, ("lewo", "srodek", "prawo"), pole)
					if pole.rodzaj == "kratka":
						self.assertEqual(pole.wyrownanie, "srodek", pole)
						self.assertIsNone(pole.maks_szerokosc, pole)


if __name__ == "__main__":
	unittest.main()
