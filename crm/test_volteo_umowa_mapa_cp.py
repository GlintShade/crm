# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Test kontraktu dwukierunkowego mapa↔kontekst dla umowy obsługi dotacji CP
(`crm/volteo_umowa_mapa_cp.py` ↔ `crm/volteo_umowa_pdf_cp.py`).

Odpowiednik `crm/test_volteo_kredyt_mapa.py` dla piątego dokumentu. Umowa
obsługi dotacji CP ma JEDEN szablon i JEDNĄ mapę (`MAPA_CP`), więc testy niżej
nie pętlą się po żadnym rejestrze — operują bezpośrednio na `MAPA_CP` i na
kontekście zwracanym przez `zbuduj_kontekst_cp`."""

import unittest
from datetime import date
from typing import Any

from crm.volteo_umowa_mapa import SZEROKOSC_STRONY_PT, WYSOKOSC_STRONY_PT, Pole
from crm.volteo_umowa_mapa_cp import LICZBA_STRON_CP, MAPA_CP, klucze_w_mapie_cp, pozycje_dla_cp
from crm.volteo_umowa_pdf_cp import zbuduj_kontekst_cp

_DZIS = date(2026, 9, 29)

# ---------------------------------------------------------------------------
# Wyjątki kontraktu dwukierunkowego.
#
# Klucz kontekstu, którego fizycznie nie ma gdzie wydrukować, byłby tu jawnie
# wymieniony z uzasadnieniem. `MAPA_CP` pokrywa każdy z 15 kluczy kontekstu
# zwracanych przez `zbuduj_kontekst_cp` — brak tu żadnego pola bez pozycji.
# ---------------------------------------------------------------------------
WYJATKI_CP: frozenset[str] = frozenset()
"""Umowa obsługi dotacji CP ma jeden szablon obejmujący wszystkie 15 kluczy
kontekstu — brak kluczy bez pozycji w mapie, więc zbiór jest pusty."""

# Strony (0-based) na których `podpis_zamawiajacy` ma pozycję: str. 4 (indeks
# 3, koniec umowy głównej) i str. 5 (indeks 4, Załącznik nr 1).
_STRONY_PODPIS_ZAMAWIAJACY: frozenset[int] = frozenset({3, 4})

# Strony celowo bez żadnej pozycji: str. 3 (indeks 2) jest czystym tekstem
# prawnym (§5-§9), zweryfikowane brakiem glifu kratki/podkreślenia/podpisu.
_STRONY_PUSTE: frozenset[int] = frozenset({2})


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"umowa1_netto": "1600",
		"umowa1_brutto": "1968",
		"umowa2_netto": "2400",
		"umowa2_brutto": "2952",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"first_name": "Anna",
		"last_name": "Kowalska",
		"custom_pesel": "90010112345",
		"custom_ulica": "Kwiatowa",
		"custom_nr_domu": "5",
		"custom_nr_mieszkania": "12",
		"custom_kod_pocztowy": "00-001",
		"custom_miasto": "Warszawa",
		"email": "anna@example.com",
		"mobile_no": "500600700",
	}
	baza.update(nadpisania)
	return baza


def _umowa(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"wynagrodzenie_wariant": "2",
		"zgoda_przetwarzanie_danych": 1,
		"zgoda_kontakt_telefoniczny": 1,
		"zgoda_dzialania_promocyjne": 1,
	}
	baza.update(nadpisania)
	return baza


def _deal(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {"name": "PRO/CP/26/0001"}
	baza.update(nadpisania)
	return baza


def _pelny_kontekst() -> dict[str, Any]:
	"""Referencyjny kontekst — KAŻDE pole wypełnione poprawną, niepustą wartością
	(w tym wariant wynagrodzenia i wszystkie trzy zgody włączone), żeby żadna
	wartość nie wypadła pusta z powodu reguły "brak danych = pustka". Ten sam
	kontekst służy wszystkim testom niżej."""
	return zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)


class TestKlucze(unittest.TestCase):
	def test_a_kazdy_klucz_mapy_istnieje_w_kontekscie(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_kontekstu = set(kontekst.keys())
		for pole in MAPA_CP:
			with self.subTest(klucz=pole.klucz):
				self.assertIn(
					pole.klucz,
					klucze_kontekstu,
					f"MAPA_CP odwołuje się do klucza {pole.klucz!r}, którego nie ma "
					"w zbuduj_kontekst_cp()",
				)

	def test_b_kazdy_klucz_kontekstu_ma_pozycje_albo_jawny_wyjatek(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_mapy = klucze_w_mapie_cp()
		for klucz in kontekst:
			if klucz in WYJATKI_CP:
				continue
			with self.subTest(klucz=klucz):
				self.assertIn(
					klucz,
					klucze_mapy,
					f"Klucz {klucz!r} nie ma żadnej pozycji w MAPA_CP i nie jest w "
					"WYJATKI_CP — dana po cichu zniknęłaby z wydrukowanej umowy.",
				)

	def test_c_wyjatki_i_mapa_sie_nie_pokrywaja(self: "TestKlucze") -> None:
		self.assertEqual(WYJATKI_CP & klucze_w_mapie_cp(), frozenset())

	def test_d_wszystkie_wyjatki_sa_prawdziwymi_kluczami_kontekstu(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		for klucz in WYJATKI_CP:
			with self.subTest(klucz=klucz):
				self.assertIn(klucz, kontekst)


class TestGeometria(unittest.TestCase):
	def test_a_strona_w_zakresie(self: "TestGeometria") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.strona, 0, pole)
				self.assertLess(pole.strona, LICZBA_STRON_CP, pole)

	def test_b_x_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.x, 0.0, pole)
				self.assertLessEqual(pole.x, SZEROKOSC_STRONY_PT, pole)

	def test_c_y_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.y, 0.0, pole)
				self.assertLessEqual(pole.y, WYSOKOSC_STRONY_PT, pole)

	def test_d_maks_szerokosc_nie_wychodzi_poza_strone(self: "TestGeometria") -> None:
		for pole in MAPA_CP:
			if pole.maks_szerokosc is None:
				continue
			with self.subTest(pole=pole):
				self.assertGreater(pole.maks_szerokosc, 0.0, pole)
				self.assertLessEqual(pole.x + pole.maks_szerokosc, SZEROKOSC_STRONY_PT, pole)

	def test_e_rozmiar_fontu_dodatni_i_sensowny(self: "TestGeometria") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertGreater(pole.rozmiar, 0.0, pole)
				self.assertLess(pole.rozmiar, 24.0, pole)


class TestStrony(unittest.TestCase):
	def test_a_puste_strony_bez_pozycji(self: "TestStrony") -> None:
		strony_z_pozycjami = {pole.strona for pole in MAPA_CP}
		for strona in _STRONY_PUSTE:
			with self.subTest(strona=strona):
				self.assertNotIn(strona, strony_z_pozycjami)

	def test_b_liczba_pozycji_wg_strony(self: "TestStrony") -> None:
		# Rozkład zamrożony w docstringu `MAPA_CP`: 7 (str. 1) + 2 (str. 2) +
		# 0 (str. 3) + 2 (str. 4) + 4 (str. 5) + 1 (str. 6) = 16.
		oczekiwane = {0: 7, 1: 2, 2: 0, 3: 2, 4: 4, 5: 1}
		for strona, liczba in oczekiwane.items():
			with self.subTest(strona=strona):
				self.assertEqual(len([pole for pole in MAPA_CP if pole.strona == strona]), liczba)

	def test_c_podpis_zamawiajacy_na_dwoch_stronach(self: "TestStrony") -> None:
		strony = {pole.strona for pole in pozycje_dla_cp("podpis_zamawiajacy")}
		self.assertEqual(strony, _STRONY_PODPIS_ZAMAWIAJACY)
		for strona in _STRONY_PODPIS_ZAMAWIAJACY:
			with self.subTest(strona=strona):
				pozycje_na_stronie = [
					pole for pole in pozycje_dla_cp("podpis_zamawiajacy") if pole.strona == strona
				]
				self.assertEqual(len(pozycje_na_stronie), 1)

	def test_d_podpis_wykonawca_tylko_na_stronie_4(self: "TestStrony") -> None:
		strony = {pole.strona for pole in pozycje_dla_cp("podpis_wykonawca")}
		self.assertEqual(strony, {3})


class TestRodzajIWyrownanie(unittest.TestCase):
	def test_a_rodzaj_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertIn(pole.rodzaj, ("tekst", "kratka"), pole)

	def test_b_wyrownanie_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_CP:
			with self.subTest(pole=pole):
				self.assertIn(pole.wyrownanie, ("lewo", "srodek", "prawo"), pole)

	def test_c_kratki_sa_wyrownane_do_srodka(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_CP:
			if pole.rodzaj == "kratka":
				with self.subTest(pole=pole):
					self.assertEqual(pole.wyrownanie, "srodek", pole)

	def test_d_kratki_nie_maja_maks_szerokosci(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_CP:
			if pole.rodzaj == "kratka":
				with self.subTest(pole=pole):
					self.assertIsNone(pole.maks_szerokosc, pole)

	def test_e_klucze_logiczne_kontekstu_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, bool):
				continue
			for pole in pozycje_dla_cp(klucz):
				with self.subTest(klucz=klucz, strona=pole.strona):
					self.assertEqual(
						pole.rodzaj,
						"kratka",
						f"{klucz!r} zwraca bool w zbuduj_kontekst_cp(), ale mapa oznacza go "
						f"jako {pole.rodzaj!r} na stronie {pole.strona}",
					)

	def test_f_klucze_tekstowe_kontekstu_nie_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, str):
				continue
			for pole in pozycje_dla_cp(klucz):
				with self.subTest(klucz=klucz, strona=pole.strona):
					self.assertEqual(
						pole.rodzaj,
						"tekst",
						f"{klucz!r} zwraca str w zbuduj_kontekst_cp(), ale mapa oznacza go "
						f"jako {pole.rodzaj!r} na stronie {pole.strona}",
					)


class TestWielokrotnePozycjeIDuplikaty(unittest.TestCase):
	def test_a_zero_duplikatow_tej_samej_pozycji(self: "TestWielokrotnePozycjeIDuplikaty") -> None:
		widziane: set[tuple[str, int, float, float]] = set()
		for pole in MAPA_CP:
			klucz_pozycji = (pole.klucz, pole.strona, pole.x, pole.y)
			with self.subTest(pole=pole):
				self.assertNotIn(klucz_pozycji, widziane, f"Zduplikowana pozycja: {pole}")
			widziane.add(klucz_pozycji)

	def test_b_tylko_podpis_zamawiajacy_wystepuje_wiecej_niz_raz(
		self: "TestWielokrotnePozycjeIDuplikaty",
	) -> None:
		liczniki: dict[str, int] = {}
		for pole in MAPA_CP:
			liczniki[pole.klucz] = liczniki.get(pole.klucz, 0) + 1
		wielokrotne = {klucz for klucz, ile in liczniki.items() if ile > 1}
		self.assertEqual(wielokrotne, {"podpis_zamawiajacy"})


class TestPoleDataclass(unittest.TestCase):
	def test_a_pole_jest_niemutowalny(self: "TestPoleDataclass") -> None:
		pole = Pole("test_klucz", 0, 10.0, 10.0, "tekst")
		with self.assertRaises(Exception):
			pole.x = 20.0  # type: ignore[misc]

	def test_b_mapa_nie_jest_pusta(self: "TestPoleDataclass") -> None:
		self.assertGreater(len(MAPA_CP), 5)

	def test_c_liczba_pozycji_zgodna_z_dokumentacja_modulu(self: "TestPoleDataclass") -> None:
		self.assertEqual(len(MAPA_CP), 16)


class TestWartosciKontekstu(unittest.TestCase):
	def test_a_kazda_wartosc_referencyjnego_kontekstu_jest_str_albo_bool(
		self: "TestWartosciKontekstu",
	) -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			with self.subTest(klucz=klucz):
				self.assertIsInstance(wartosc, (str, bool))
				self.assertIsNotNone(wartosc)


if __name__ == "__main__":
	unittest.main()
