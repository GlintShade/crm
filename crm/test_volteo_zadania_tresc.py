import unittest

from crm.volteo_zadania_tresc import czy_zmiana_tresci_dozwolona, normalizuj

PRZED = {"title": "Zadzwon", "description": "<p>Opis</p>"}


class TestZadaniaTresc(unittest.TestCase):
	def test_autor_moze_zmienic_wszystko(self):
		po = {"title": "Inny", "description": "<p>Nowy</p>"}
		self.assertTrue(czy_zmiana_tresci_dozwolona("a@x.pl", "a@x.pl", PRZED, po))

	def test_inny_nie_zmieni_tytulu(self):
		po = {**PRZED, "title": "Inny"}
		self.assertFalse(czy_zmiana_tresci_dozwolona("a@x.pl", "b@x.pl", PRZED, po))

	def test_inny_nie_zmieni_opisu(self):
		po = {**PRZED, "description": "<p>Nowy</p>"}
		self.assertFalse(czy_zmiana_tresci_dozwolona("a@x.pl", "b@x.pl", PRZED, po))

	def test_administrator_bez_wyjatku(self):
		po = {**PRZED, "title": "Inny"}
		self.assertFalse(czy_zmiana_tresci_dozwolona("a@x.pl", "Administrator", PRZED, po))

	def test_inny_bez_zmiany_tresci_przechodzi(self):
		self.assertTrue(czy_zmiana_tresci_dozwolona("a@x.pl", "b@x.pl", PRZED, dict(PRZED)))

	def test_biale_znaki_i_none_to_brak_zmiany(self):
		przed = {"title": "T", "description": None}
		po = {"title": " T ", "description": ""}
		self.assertTrue(czy_zmiana_tresci_dozwolona("a@x.pl", "b@x.pl", przed, po))
		self.assertEqual(normalizuj("<p>a</p>\n <p>b</p> "), "<p>a</p> <p>b</p>")

	def test_brak_wlasciciela_nie_daje_prawa_pustemu_uzytkownikowi(self):
		po = {**PRZED, "title": "Inny"}
		self.assertFalse(czy_zmiana_tresci_dozwolona(None, None, PRZED, po))


if __name__ == "__main__":
	unittest.main()
