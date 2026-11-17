import unittest

from crm.volteo_umowa_widocznosc import (
	PTYPY_ODCZYTU,
	ZAPIS_TYLKO_AUTOR,
	ZAPIS_TYLKO_PRZEZ_API,
	czy_autor,
	czy_odczyt,
	decyzja,
)

PTYPY_ZAPISU = ("write", "create", "delete", "submit", "cancel", "amend")


class TestCzyOdczyt(unittest.TestCase):
	def test_ptypy_odczytu(self: "TestCzyOdczyt") -> None:
		for p in PTYPY_ODCZYTU:
			self.assertTrue(czy_odczyt(p), p)

	def test_ptypy_zapisu(self: "TestCzyOdczyt") -> None:
		for p in PTYPY_ZAPISU:
			self.assertFalse(czy_odczyt(p), p)

	def test_znacznik(self: "TestCzyOdczyt") -> None:
		self.assertIs(ZAPIS_TYLKO_AUTOR, True)
		self.assertIs(ZAPIS_TYLKO_PRZEZ_API, True)


class TestCzyAutor(unittest.TestCase):
	def test_pusty_autor(self: "TestCzyAutor") -> None:
		self.assertTrue(czy_autor("a@x.pl", None))
		self.assertTrue(czy_autor("a@x.pl", ""))

	def test_ten_sam(self: "TestCzyAutor") -> None:
		self.assertTrue(czy_autor("a@x.pl", "a@x.pl"))

	def test_inny(self: "TestCzyAutor") -> None:
		self.assertFalse(czy_autor("a@x.pl", "b@x.pl"))


class TestDecyzja(unittest.TestCase):
	def test_odczyt_z_widocznoscia(self: "TestDecyzja") -> None:
		for p in PTYPY_ODCZYTU:
			self.assertTrue(decyzja(p, True, False, "a@x.pl", "b@x.pl"), p)

	def test_odczyt_bez_widocznosci(self: "TestDecyzja") -> None:
		for p in PTYPY_ODCZYTU:
			self.assertFalse(decyzja(p, False, True, "a@x.pl", "a@x.pl"), p)

	def test_zapis_autor_zamkniety(self: "TestDecyzja") -> None:
		for p in ("write", "delete", "submit", "cancel", "amend", "import"):
			self.assertFalse(decyzja(p, True, True, "a@x.pl", "a@x.pl"), p)

	def test_create_autor_z_zapisem_szansy(self: "TestDecyzja") -> None:
		self.assertTrue(decyzja("create", True, True, "a@x.pl", "a@x.pl"))

	def test_create_bez_zapisu_szansy(self: "TestDecyzja") -> None:
		self.assertFalse(decyzja("create", True, False, "a@x.pl", "a@x.pl"))
		self.assertFalse(decyzja("create", True, False, "a@x.pl", None))

	def test_create_nie_autor(self: "TestDecyzja") -> None:
		self.assertFalse(decyzja("create", True, True, "a@x.pl", "b@x.pl"))

	def test_zapis_nie_autor_przypisany_i_przelozony(self: "TestDecyzja") -> None:
		for p in PTYPY_ZAPISU:
			self.assertFalse(decyzja(p, True, True, "a@x.pl", "b@x.pl"), p)
			self.assertFalse(decyzja(p, True, False, "a@x.pl", "b@x.pl"), p)

	def test_create_pusty_autor(self: "TestDecyzja") -> None:
		self.assertTrue(decyzja("create", True, True, "a@x.pl", None))
		self.assertFalse(decyzja("create", True, False, "a@x.pl", None))

	def test_zapis_bez_widocznosci(self: "TestDecyzja") -> None:
		self.assertFalse(decyzja("write", False, True, "a@x.pl", "a@x.pl"))


if __name__ == "__main__":
	unittest.main()
