import unittest
from decimal import Decimal
from typing import Any

from crm.czyste_powietrze.mapowanie import (
	CPBladMapowania,
	katalog_z_wierszy,
	limity_z_wierszy,
	stale_z_dokumentu,
)
from crm.czyste_powietrze.obliczenia import oblicz_oferte


def _wiersz_pozycji(**zmiany: Any) -> dict[str, Any]:
	wiersz: dict[str, Any] = {
		"kod": "pompa_ciepla",
		"nazwa": "Pompa ciepła",
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "35200",
		"dotacja_podstawowy": "14080",
		"dotacja_podwyzszony": "24640",
		"dotacja_najwyzszy": "35200",
		"limit_podstawowy": None,
		"limit_podwyzszony": None,
		"limit_najwyzszy": None,
		"prowizja": "3000",
		"koszt_proenergy": "26500",
		"koszt_staly": "0",
		"aktywny": 1,
	}
	wiersz.update(zmiany)
	return wiersz


def _stale() -> dict[str, Any]:
	return {
		"vat_mnoznik": "1.08",
		"mnoznik_elewacja": "1.4",
		"mnoznik_strop": "0.9",
		"mnoznik_dach": "1.3",
		"mnoznik_okna": "0.15",
		"m2_na_drzwi": "2",
		"umowa_min": "ignored",
	}


class TestMapowanie(unittest.TestCase):
	def test_limit_zero_is_no_cap_and_value_is_preserved(self: "TestMapowanie") -> None:
		wiersz = _wiersz_pozycji(
			limit_podstawowy=0,
			limit_podwyzszony=0.0,
			limit_najwyzszy=8200,
		)

		katalog = katalog_z_wierszy([wiersz])

		self.assertIsNone(katalog["pompa_ciepla"]["limit_dotacji"]["podstawowy"])
		self.assertIsNone(katalog["pompa_ciepla"]["limit_dotacji"]["podwyzszony"])
		self.assertEqual(katalog["pompa_ciepla"]["limit_dotacji"]["najwyzszy"], 8200)

	def test_missing_limit_is_no_cap(self: "TestMapowanie") -> None:
		wiersz = _wiersz_pozycji()
		del wiersz["limit_podstawowy"]
		del wiersz["limit_podwyzszony"]
		del wiersz["limit_najwyzszy"]

		katalog = katalog_z_wierszy([wiersz])

		self.assertEqual(
			katalog["pompa_ciepla"]["limit_dotacji"],
			{"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		)

	def test_aktywny_is_real_bool(self: "TestMapowanie") -> None:
		self.assertIs(katalog_z_wierszy([_wiersz_pozycji(aktywny=0)])["pompa_ciepla"]["aktywny"], False)
		self.assertIs(katalog_z_wierszy([_wiersz_pozycji(aktywny=1)])["pompa_ciepla"]["aktywny"], True)

	def test_limit_amount_only_for_amount_status(self: "TestMapowanie") -> None:
		wiersze = [
			{"poziom": "podstawowy", "standard": "do80", "status_limitu": "kwota", "limit_laczny": 100},
			{
				"poziom": "podstawowy",
				"standard": "od80do140",
				"status_limitu": "brak_dotacji",
				"limit_laczny": 200,
			},
			{
				"poziom": "podstawowy",
				"standard": "powyzej140",
				"status_limitu": "niedozwolone",
				"limit_laczny": 300,
			},
			{
				"poziom": "podwyzszony",
				"standard": "do80",
				"status_limitu": "do_ustalenia",
				"limit_laczny": 400,
			},
		]

		limity = limity_z_wierszy(wiersze)

		self.assertEqual(limity[("podstawowy", "do80")]["kwota"], 100)
		for klucz in (
			("podstawowy", "od80do140"),
			("podstawowy", "powyzej140"),
			("podwyzszony", "do80"),
		):
			self.assertIsNone(limity[klucz]["kwota"])

	def test_stale_preserve_values_and_ignore_umowa(self: "TestMapowanie") -> None:
		vat = Decimal("1.08")
		dokument = _stale()
		dokument["vat_mnoznik"] = vat

		stale = stale_z_dokumentu(dokument)

		self.assertIs(stale["vat_mnoznik"], vat)
		self.assertEqual(stale["mnozniki"]["elewacja"], "1.4")
		self.assertEqual(stale["m2_na_drzwi"], "2")
		self.assertNotIn("umowa_min", stale)

	def test_unknown_status_raises(self: "TestMapowanie") -> None:
		wiersz = {
			"poziom": "podstawowy",
			"standard": "do80",
			"status_limitu": "nieznany",
			"limit_laczny": 100,
		}

		with self.assertRaises(CPBladMapowania):
			limity_z_wierszy([wiersz])

	def test_duplicate_code_raises(self: "TestMapowanie") -> None:
		with self.assertRaises(CPBladMapowania):
			katalog_z_wierszy([_wiersz_pozycji(), _wiersz_pozycji()])

	def test_duplicate_limit_raises(self: "TestMapowanie") -> None:
		wiersz = {"poziom": "podstawowy", "standard": "do80", "status_limitu": "kwota", "limit_laczny": 100}

		with self.assertRaises(CPBladMapowania):
			limity_z_wierszy([wiersz, dict(wiersz)])

	def test_missing_required_field_raises(self: "TestMapowanie") -> None:
		wiersz = _wiersz_pozycji()
		del wiersz["dotacja_najwyzszy"]

		with self.assertRaises(CPBladMapowania):
			katalog_z_wierszy([wiersz])

	def test_mapping_fits_core_end_to_end(self: "TestMapowanie") -> None:
		wejscie = {
			"poziom": "najwyzszy",
			"standard": "powyzej140",
			"zrodlo_ciepla": "pompa_ciepla",
			"cwu": False,
			"typ_grzejnikow": None,
			"ilosc_grzejnikow": 0,
			"powierzchnia_m2": "120",
			"prace": {
				"elewacja": {"wybrana": False, "m2": None},
				"strop": {"wybrana": False, "m2": None},
				"dach": {"wybrana": False, "m2": None},
				"okna": {"wybrana": False, "m2": None},
				"drzwi": {"wybrana": False, "ilosc": 0},
			},
		}
		limity = limity_z_wierszy(
			[
				{
					"poziom": "najwyzszy",
					"standard": "powyzej140",
					"status_limitu": "kwota",
					"limit_laczny": "83000",
				}
			]
		)

		katalog = katalog_z_wierszy([_wiersz_pozycji()])
		wynik = oblicz_oferte(wejscie, katalog, limity, stale_z_dokumentu(_stale()))

		self.assertEqual(wynik["wklad_wlasny"], Decimal("2816.00"))
		self.assertIn("pompa_ciepla", katalog)


if __name__ == "__main__":
	unittest.main()
