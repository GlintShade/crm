# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_szansa_doradca import (
	ROLE_ZMIANY_DORADCY,
	czy_dozwolony_doradca,
	czy_moze_zmienic_doradce,
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
