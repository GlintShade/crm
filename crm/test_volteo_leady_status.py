# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_leady_status import czy_moze_zmienic_status_cc as moze


class TestCzyMozeZmienicStatusCC(unittest.TestCase):
	def test_administrator(self):
		self.assertTrue(moze("Administrator", ["Volteo D2D Sales"]))

	def test_administrator_bez_rol(self):
		self.assertTrue(moze("Administrator", []))

	def test_czysty_cc(self):
		self.assertTrue(moze("cc@x.pl", ["Volteo Call Center"]))

	def test_czysty_backend(self):
		self.assertTrue(moze("b@x.pl", ["Volteo Backend"]))

	def test_core_admin(self):
		self.assertTrue(moze("a@x.pl", ["Volteo Core Admin"]))

	def test_system_manager(self):
		self.assertTrue(moze("s@x.pl", ["System Manager"]))

	def test_czysty_d2d_zablokowany(self):
		self.assertFalse(moze("h@x.pl", ["Volteo D2D Sales", "Sales User"]))

	def test_d2d_plus_cc(self):
		self.assertTrue(moze("h@x.pl", ["Volteo D2D Sales", "Volteo Call Center"]))

	def test_d2d_plus_backend(self):
		self.assertTrue(moze("h@x.pl", ["Volteo D2D Sales", "Volteo Backend"]))

	def test_rola_spoza_listy_bez_d2d(self):
		self.assertTrue(moze("m@x.pl", ["Sales Manager"]))

	def test_puste_role(self):
		self.assertTrue(moze("m@x.pl", []))

	def test_none_roles(self):
		self.assertTrue(moze("m@x.pl", None))

	def test_krotka_i_set_rol(self):
		self.assertFalse(moze("h@x.pl", ("Volteo D2D Sales",)))
		self.assertFalse(moze("h@x.pl", {"Volteo D2D Sales"}))

	def test_d2d_z_flaga(self):
		self.assertTrue(moze("h@x.pl", ["Volteo D2D Sales"], True))

	def test_d2d_bez_flagi(self):
		self.assertFalse(moze("h@x.pl", ["Volteo D2D Sales"], False))

	def test_flaga_bez_rol(self):
		self.assertTrue(moze("h@x.pl", None, True))

	def test_administrator_bez_flagi(self):
		self.assertTrue(moze("Administrator", ["Volteo D2D Sales"], False))

	def test_cc_bez_flagi(self):
		self.assertTrue(moze("cc@x.pl", ["Volteo Call Center"], False))


if __name__ == "__main__":
	unittest.main()
