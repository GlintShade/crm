# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_szansa_doradca import (
	LIMIT_PARTII_ZBIORCZEJ,
	ROLE_ZMIANY_DORADCY,
	ROLE_ZMIANY_DORADCY_ZBIORCZO,
	czy_dozwolony_doradca,
	czy_moze_zmienic_doradce,
	czy_moze_zmienic_doradce_zbiorczo,
	normalizuj_partie,
)


class TestCzyMozeZmienicDoradce(unittest.TestCase):
	def test_administrator(self):
		self.assertTrue(czy_moze_zmienic_doradce("Administrator", []))

	def test_role_dopuszczone(self):
		for rola in ROLE_ZMIANY_DORADCY:
			self.assertTrue(czy_moze_zmienic_doradce("u@x.pl", [rola]), rola)

	def test_backend_z_innymi_rolami(self):
		self.assertTrue(czy_moze_zmienic_doradce("u@x.pl", ["Sales User", "Volteo Backend"]))

	def test_guest(self):
		self.assertFalse(czy_moze_zmienic_doradce("Guest", ["Volteo Backend"]))

	def test_pusty_uzytkownik(self):
		self.assertFalse(czy_moze_zmienic_doradce("", ["Volteo Backend"]))

	def test_sam_d2d(self):
		self.assertFalse(czy_moze_zmienic_doradce("h@x.pl", ["Volteo D2D Sales"]))

	def test_sam_cc(self):
		self.assertFalse(czy_moze_zmienic_doradce("c@x.pl", ["Volteo Call Center"]))

	def test_puste_role(self):
		self.assertFalse(czy_moze_zmienic_doradce("u@x.pl", []))
		self.assertFalse(czy_moze_zmienic_doradce("u@x.pl", None))


class TestCzyDozwolonyDoradca(unittest.TestCase):
	def test_wlaczony_d2d(self):
		self.assertTrue(czy_dozwolony_doradca(True, ["Volteo D2D Sales", "Sales User"]))

	def test_wylaczony(self):
		self.assertFalse(czy_dozwolony_doradca(False, ["Volteo D2D Sales"]))

	def test_bez_roli_d2d(self):
		self.assertFalse(czy_dozwolony_doradca(True, ["Volteo Backend"]))

	def test_puste_role(self):
		self.assertFalse(czy_dozwolony_doradca(True, []))
		self.assertFalse(czy_dozwolony_doradca(True, None))


class TestCzyMozeZmienicDoradceZbiorczo(unittest.TestCase):
	def test_administrator(self):
		self.assertTrue(czy_moze_zmienic_doradce_zbiorczo("Administrator", []))

	def test_role_administratorskie(self):
		for rola in ROLE_ZMIANY_DORADCY_ZBIORCZO:
			self.assertTrue(czy_moze_zmienic_doradce_zbiorczo("u@x.pl", [rola]), rola)

	def test_backoffice_odmowa(self):
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("b@x.pl", ["Volteo Backend", "Sales User"]))

	def test_d2d_i_cc_odmowa(self):
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("h@x.pl", ["Volteo D2D Sales"]))
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("c@x.pl", ["Volteo Call Center"]))

	def test_guest_i_puste(self):
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("Guest", ["System Manager"]))
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("", ["System Manager"]))
		self.assertFalse(czy_moze_zmienic_doradce_zbiorczo("u@x.pl", None))

	def test_zbior_wezszy_niz_pojedynczy(self):
		self.assertTrue(ROLE_ZMIANY_DORADCY_ZBIORCZO < ROLE_ZMIANY_DORADCY)


class TestNormalizujPartie(unittest.TestCase):
	def test_unikalne_w_kolejnosci(self):
		self.assertEqual(normalizuj_partie(["A", " B ", "A", "", None, "C"]), ["A", "B", "C"])

	def test_nie_lista(self):
		for zle in ("A", None, {"a": 1}, 5):
			with self.assertRaises(ValueError):
				normalizuj_partie(zle)

	def test_pusta(self):
		with self.assertRaises(ValueError):
			normalizuj_partie([])
		with self.assertRaises(ValueError):
			normalizuj_partie(["", "  "])

	def test_limit(self):
		self.assertEqual(len(normalizuj_partie([f"D{i}" for i in range(LIMIT_PARTII_ZBIORCZEJ)])), LIMIT_PARTII_ZBIORCZEJ)
		with self.assertRaises(ValueError):
			normalizuj_partie([f"D{i}" for i in range(LIMIT_PARTII_ZBIORCZEJ + 1)])

	def test_duplikaty_nie_licza_sie_do_limitu(self):
		self.assertEqual(normalizuj_partie(["A"] * 500), ["A"])
