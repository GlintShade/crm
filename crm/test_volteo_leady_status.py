# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_leady_status import czy_moze_zmienic_status_cc as moze
from crm.volteo_leady_status import lead_bezposredni_wlasny


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


class TestLeadBezposredniWlasny(unittest.TestCase):
	def test_wlasny_lead_z_reguly(self):
		self.assertTrue(lead_bezposredni_wlasny("h@x.pl", 1, "h@x.pl"))
		self.assertTrue(lead_bezposredni_wlasny("h@x.pl", "1", "h@x.pl"))

	def test_cudzy_lead_z_reguly(self):
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", 1, "inny@x.pl"))

	def test_lead_bez_znacznika(self):
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", 0, "h@x.pl"))
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", None, "h@x.pl"))
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", "", "h@x.pl"))

	def test_znacznik_bez_wlasciciela(self):
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", 1, None))
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", 1, ""))

	def test_smieciowa_wartosc_znacznika(self):
		self.assertFalse(lead_bezposredni_wlasny("h@x.pl", "abc", "h@x.pl"))

	def test_brak_uzytkownika(self):
		self.assertFalse(lead_bezposredni_wlasny("", 1, ""))


class TestMozeZLeademBezposrednim(unittest.TestCase):
	def test_handlowiec_na_wlasnym_leadzie_z_reguly(self):
		self.assertTrue(moze("h@x.pl", ["Volteo D2D Sales"], False, True))

	def test_handlowiec_na_cudzym_leadzie_z_reguly(self):
		self.assertFalse(moze("h@x.pl", ["Volteo D2D Sales"], False, False))

	def test_domyslnie_blokada_zostaje(self):
		self.assertFalse(moze("h@x.pl", ["Volteo D2D Sales"]))
