# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import datetime, timezone

from crm.volteo_limit_zadan import klucz_limitu, limit_przekroczony


def _t(s: int) -> datetime:
	return datetime.fromtimestamp(s, tz=timezone.utc)


class TestKluczLimitu(unittest.TestCase):
	def test_ten_sam_klucz_wewnatrz_okna(self):
		self.assertEqual(klucz_limitu("m", "u", _t(120), 60), klucz_limitu("m", "u", _t(179), 60))

	def test_klucz_zmienia_sie_na_granicy_okna(self):
		self.assertNotEqual(klucz_limitu("m", "u", _t(179), 60), klucz_limitu("m", "u", _t(180), 60))

	def test_rozni_uzytkownicy(self):
		self.assertNotEqual(klucz_limitu("m", "a", _t(120), 60), klucz_limitu("m", "b", _t(120), 60))

	def test_rozne_metody(self):
		self.assertNotEqual(klucz_limitu("m1", "u", _t(120), 60), klucz_limitu("m2", "u", _t(120), 60))

	def test_metoda_z_kropkami(self):
		k = klucz_limitu("crm.api.umowa.volteo_umowa_get", "a@b.pl", _t(120), 60)
		self.assertEqual(k, "volteo:limit:crm.api.umowa.volteo_umowa_get:a@b.pl:2")

	def test_okno_inne_niz_60(self):
		self.assertEqual(klucz_limitu("m", "u", _t(299), 300), klucz_limitu("m", "u", _t(0), 300))
		self.assertNotEqual(klucz_limitu("m", "u", _t(299), 300), klucz_limitu("m", "u", _t(300), 300))
		self.assertTrue(klucz_limitu("m", "u", _t(3600), 3600).endswith(":1"))


class TestLimitPrzekroczony(unittest.TestCase):
	def test_rowny_limitowi_nie_przekracza(self):
		self.assertFalse(limit_przekroczony(5, 5))

	def test_powyzej_limitu_przekracza(self):
		self.assertTrue(limit_przekroczony(6, 5))

	def test_ponizej(self):
		self.assertFalse(limit_przekroczony(1, 5))


if __name__ == "__main__":
	unittest.main()
