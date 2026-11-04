# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_kontakt_cien import czy_pominac_kontakt_cien


def _decyzja(**kw):
	args = {
		"user": "a@x.pl",
		"user_type": "System User",
		"enabled": 1,
		"ma_linki": False,
		"wymuszony": False,
	}
	args.update(kw)
	return czy_pominac_kontakt_cien(**args)


class TestCzyPominacKontaktCien(unittest.TestCase):
	def test_system_user_bez_linkow_pomijany(self):
		self.assertTrue(_decyzja())

	def test_enabled_nie_ma_znaczenia(self):
		self.assertTrue(_decyzja(enabled=0))
		self.assertTrue(_decyzja(enabled=None))

	def test_brak_usera(self):
		self.assertFalse(_decyzja(user=None))
		self.assertFalse(_decyzja(user=""))

	def test_administrator_i_guest(self):
		self.assertFalse(_decyzja(user="Administrator"))
		self.assertFalse(_decyzja(user="Guest"))

	def test_website_user(self):
		self.assertFalse(_decyzja(user_type="Website User"))

	def test_brak_typu(self):
		self.assertFalse(_decyzja(user_type=None))

	def test_kontakt_z_linkami(self):
		self.assertFalse(_decyzja(ma_linki=True))

	def test_wymuszony_flaga(self):
		self.assertFalse(_decyzja(wymuszony=True))


if __name__ == "__main__":
	unittest.main()
