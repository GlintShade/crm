# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import date
from decimal import Decimal
from typing import Any

from crm.volteo_umowa_mapa import (
	MAPA,
	SZEROKOSC_STRONY_PT,
	WYSOKOSC_STRONY_PT,
	Pole,
	klucze_w_mapie,
	pozycje_dla,
)
from crm.volteo_umowa_pdf import zbuduj_kontekst

_LICZBA_STRON = 18

# Klucze z kontekstu świadomie pominięte w `MAPA` — puste, bo szablon PDF-u nie ma
# dla nich osobnego miejsca w tej wersji dokumentu. Każdy wpis wymaga uzasadnienia,
# żeby brak pozycji nigdy nie był przeoczeniem. Aktualnie pusty: wszystkie klucze
# `zbuduj_kontekst` mają co najmniej jedną pozycję w `MAPA`.
WYJATKI_BRAK_POZYCJI: frozenset[str] = frozenset()


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
	od "wartość akurat pusta w tym fixture."""
	return zbuduj_kontekst(
		_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), date(2026, 8, 6)
	)


class TestKlucze(unittest.TestCase):
	def test_a_kazdy_klucz_mapy_istnieje_w_kontekscie(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_kontekstu = set(kontekst.keys())
		for pole in MAPA:
			self.assertIn(
				pole.klucz,
				klucze_kontekstu,
				f"MAPA odwołuje się do klucza {pole.klucz!r}, którego nie ma w zbuduj_kontekst()",
			)

	def test_b_kazdy_klucz_kontekstu_ma_pozycje_albo_jawny_wyjatek(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_mapy = klucze_w_mapie()
		for klucz in kontekst:
			if klucz in WYJATKI_BRAK_POZYCJI:
				continue
			self.assertIn(
				klucz,
				klucze_mapy,
				f"Klucz {klucz!r} nie ma żadnej pozycji w MAPA i nie jest w WYJATKI_BRAK_POZYCJI "
				"— dana po cichu zniknęłaby z wydrukowanego dokumentu.",
			)

	def test_c_wyjatki_i_mapa_sie_nie_pokrywaja(self: "TestKlucze") -> None:
		# Klucz nie może być jednocześnie "świadomie pominięty" i obecny w mapie —
		# to by znaczyło, że komentarz uzasadniający wyjątek jest nieaktualny.
		self.assertEqual(WYJATKI_BRAK_POZYCJI & klucze_w_mapie(), frozenset())

	def test_d_wszystkie_wyjatki_sa_prawdziwymi_kluczami_kontekstu(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		for klucz in WYJATKI_BRAK_POZYCJI:
			self.assertIn(klucz, kontekst)


class TestGeometria(unittest.TestCase):
	def test_a_strona_w_zakresie(self: "TestGeometria") -> None:
		for pole in MAPA:
			self.assertGreaterEqual(pole.strona, 0, pole)
			self.assertLessEqual(pole.strona, _LICZBA_STRON - 1, pole)

	def test_b_x_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA:
			self.assertGreaterEqual(pole.x, 0.0, pole)
			self.assertLessEqual(pole.x, SZEROKOSC_STRONY_PT, pole)

	def test_c_y_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA:
			self.assertGreaterEqual(pole.y, 0.0, pole)
			self.assertLessEqual(pole.y, WYSOKOSC_STRONY_PT, pole)

	def test_d_maks_szerokosc_nie_wychodzi_poza_strone(self: "TestGeometria") -> None:
		for pole in MAPA:
			if pole.maks_szerokosc is None:
				continue
			self.assertGreater(pole.maks_szerokosc, 0.0, pole)
			self.assertLessEqual(pole.x + pole.maks_szerokosc, SZEROKOSC_STRONY_PT + 1.0, pole)

	def test_e_rozmiar_fontu_dodatni_i_sensowny(self: "TestGeometria") -> None:
		for pole in MAPA:
			self.assertGreater(pole.rozmiar, 0.0, pole)
			self.assertLess(pole.rozmiar, 24.0, pole)


class TestRodzajIWyrownanie(unittest.TestCase):
	def test_a_rodzaj_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA:
			self.assertIn(pole.rodzaj, ("tekst", "kratka"), pole)

	def test_b_wyrownanie_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA:
			self.assertIn(pole.wyrownanie, ("lewo", "srodek", "prawo"), pole)

	def test_c_kratki_sa_wyrownane_do_srodka(self: "TestRodzajIWyrownanie") -> None:
		# Kratka to pojedynczy znak "X" rysowany w środku kwadratu — mapa
		# zawsze podaje jego środek, więc wyrównanie musi być "srodek".
		for pole in MAPA:
			if pole.rodzaj == "kratka":
				self.assertEqual(pole.wyrownanie, "srodek", pole)

	def test_d_kratki_nie_maja_maks_szerokosci(self: "TestRodzajIWyrownanie") -> None:
		# maks_szerokosc słuzy do przycinania/zawijania długich wartości tekstowych
		# — nie ma zastosowania do pojedynczego znaku "X" w kratce.
		for pole in MAPA:
			if pole.rodzaj == "kratka":
				self.assertIsNone(pole.maks_szerokosc, pole)

	def test_e_klucze_logiczne_kontekstu_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, bool):
				continue
			for pole in pozycje_dla(klucz):
				self.assertEqual(
					pole.rodzaj,
					"kratka",
					f"{klucz!r} zwraca bool w zbuduj_kontekst(), ale MAPA oznacza go jako "
					f"{pole.rodzaj!r} na stronie {pole.strona}",
				)

	def test_f_klucze_tekstowe_kontekstu_nie_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, str):
				continue
			for pole in pozycje_dla(klucz):
				self.assertEqual(
					pole.rodzaj,
					"tekst",
					f"{klucz!r} zwraca str w zbuduj_kontekst(), ale MAPA oznacza go jako "
					f"{pole.rodzaj!r} na stronie {pole.strona}",
				)


class TestWielokrotnePozycje(unittest.TestCase):
	def test_a_dane_klienta_powtarzaja_sie_na_wielu_stronach(self: "TestWielokrotnePozycje") -> None:
		# Imię i nazwisko klienta drukuje się w komparycji (str. 1), obu
		# protokołach odbioru (str. 12, 15) i pełnomocnictwie (str. 18) —
		# dokładnie tak jak opisuje docstring modułu. Regresja tego testu =
		# ktoś przypadkiem usunął jedną z pozycji przy edycji mapy.
		strony = {pole.strona for pole in pozycje_dla("klient_imie_nazwisko")}
		self.assertEqual(strony, {0, 11, 14, 17})

	def test_b_zero_duplikatow_tej_samej_pozycji(self: "TestWielokrotnePozycje") -> None:
		widziane: set[tuple[str, int, float, float]] = set()
		for pole in MAPA:
			klucz_pozycji = (pole.klucz, pole.strona, pole.x, pole.y)
			self.assertNotIn(klucz_pozycji, widziane, f"Zduplikowana pozycja: {pole}")
			widziane.add(klucz_pozycji)


class TestPoleDataclass(unittest.TestCase):
	def test_a_pole_jest_niemutowalny(self: "TestPoleDataclass") -> None:
		pole = Pole("test_klucz", 0, 10.0, 10.0, "tekst")
		with self.assertRaises(Exception):
			pole.x = 20.0  # type: ignore[misc]

	def test_b_mapa_nie_jest_pusta(self: "TestPoleDataclass") -> None:
		self.assertGreater(len(MAPA), 50)


class TestPodpisy(unittest.TestCase):
	"""ZADANIE 2: pozycje `podpis_zamawiajacy`/`podpis_wykonawca` w `MAPA`."""

	def test_a_oba_klucze_maja_przynajmniej_jedna_pozycje(self: "TestPodpisy") -> None:
		self.assertGreater(len(pozycje_dla("podpis_zamawiajacy")), 0)
		self.assertGreater(len(pozycje_dla("podpis_wykonawca")), 0)

	def test_b_zadna_pozycja_podpisu_nie_lezy_na_stronach_protokolow_odbioru(
		self: "TestPodpisy",
	) -> None:
		# Strony 11-18 (indeksy 10-17) w druku to: formularz odstąpienia (10),
		# protokoły odbioru wypełniane przez instalatora po montażu (11-16) i
		# Załącznik 8 - pełnomocnictwo (17, JEDYNY wyjątek z tego zakresu, bo
		# to osobny, jednostronny dokument klienta, nie protokół montażowy).
		# Test wg zadania sprawdza indeksy 9-16 (strony 10-17) - dokładnie
		# formularz odstąpienia + wszystkie protokoły, z wyłączeniem strony 18.
		zakazane_strony = set(range(9, 17))
		for klucz in ("podpis_zamawiajacy", "podpis_wykonawca"):
			for pole in pozycje_dla(klucz):
				self.assertNotIn(
					pole.strona,
					zakazane_strony,
					f"{klucz!r} ma pozycję na stronie {pole.strona} (protokół/odstąpienie) — "
					"instalator/klient wypełnia to pole, nie ProEnergy z góry.",
				)

	def test_c_wykonawca_nie_wystepuje_na_stronie_pelnomocnictwa(self: "TestPodpisy") -> None:
		# Załącznik 8 (strona 18, indeks 17) ma tylko jedną linię podpisu -
		# Mocodawcy (klienta) - pełnomocnictwo jest jednostronnym
		# oświadczeniem, więc ProEnergy się tam nie podpisuje.
		strony_wykonawcy = {pole.strona for pole in pozycje_dla("podpis_wykonawca")}
		self.assertNotIn(17, strony_wykonawcy)

	def test_d_zamawiajacy_wystepuje_na_stronie_pelnomocnictwa(self: "TestPodpisy") -> None:
		strony_zamawiajacego = {pole.strona for pole in pozycje_dla("podpis_zamawiajacy")}
		self.assertIn(17, strony_zamawiajacego)

	def test_e_podpisy_na_oczekiwanych_stronach_umowy_i_zalacznikow(self: "TestPodpisy") -> None:
		# Strona 4 (umowa główna), 5 (Zał. 1a), 6 (Zał. 1b), 7 (Zał. 2 i 3, po
		# dwie pozycje zamawiającego) - indeksy 3, 4, 5, 6.
		strony_zamawiajacego = {pole.strona for pole in pozycje_dla("podpis_zamawiajacy")}
		strony_wykonawcy = {pole.strona for pole in pozycje_dla("podpis_wykonawca")}
		self.assertEqual(strony_zamawiajacego, {3, 4, 5, 6, 17})
		self.assertEqual(strony_wykonawcy, {3, 4, 5})

	def test_f_zalacznik_2_i_3_maja_po_jednej_odrebnej_pozycji_na_stronie_7(
		self: "TestPodpisy",
	) -> None:
		pozycje_strona_7 = [pole for pole in pozycje_dla("podpis_zamawiajacy") if pole.strona == 6]
		self.assertEqual(len(pozycje_strona_7), 2)
		self.assertNotEqual(pozycje_strona_7[0].y, pozycje_strona_7[1].y)


if __name__ == "__main__":
	unittest.main()
