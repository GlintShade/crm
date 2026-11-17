import unittest

from crm.volteo_widocznosc_adresu import PTYPY_BEZ_OGRANICZEN, literal_sql, warunek_adresu

WSZYSTKIE = {"Contact": "a OR b", "CRM Deal": "c OR d", "CRM Lead": "1=0"}


class TestLiteral(unittest.TestCase):
	def test_prosty(self: "TestLiteral") -> None:
		self.assertEqual(literal_sql("a@x.pl"), "'a@x.pl'")

	def test_ucieczka_apostrofu_i_backslasha(self: "TestLiteral") -> None:
		self.assertEqual(literal_sql("o'b\\c"), "'o\\'b\\\\c'")

	def test_bledne_znaki(self: "TestLiteral") -> None:
		for zle in ("a%b", "a\x00b", "a\nb"):
			with self.assertRaises(ValueError):
				literal_sql(zle)


class TestWarunek(unittest.TestCase):
	def test_calosc_w_nawiasach(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", WSZYSTKIE)
		self.assertTrue(w.startswith("(") and w.endswith(")"))

	def test_zagniezdzone_warunki_w_nawiasach(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", WSZYSTKIE)
		self.assertIn("AND (a OR b)", w)
		self.assertIn("WHERE (c OR d))", w)

	def test_galezie_przy_pelnym_slowniku(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", WSZYSTKIE)
		self.assertIn("FROM `tabContact`", w)
		self.assertIn("`link_doctype` = 'CRM Deal'", w)
		self.assertIn("`link_doctype` = 'CRM Lead'", w)
		self.assertIn("`link_doctype` = 'Contact'", w)
		self.assertIn("NOT IN ('CRM Deal', 'CRM Lead', 'Contact')", w)
		self.assertIn("`tabAddress`.`owner` = 'u@x.pl'", w)

	def test_pusty_slownik(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", {})
		self.assertNotIn("NOT IN ('", w)
		self.assertNotIn("`link_doctype` = ", w)
		self.assertIn("ifnull(`link_doctype`,'') != ''", w)

	def test_tylko_contact(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", {"Contact": "x=1"})
		self.assertIn("AND (x=1)", w)
		self.assertIn("NOT IN ('Contact')", w)
		self.assertNotIn("'CRM Deal'", w)

	def test_bez_contact_wszyscy_widoczni(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", {"CRM Deal": "x=1"})
		self.assertIn("ifnull(`address`,'') != '')", w)
		self.assertNotIn("`link_doctype` = 'Contact'", w)

	def test_kolejnosc_posortowana(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", {"Contact": "a", "CRM Lead": "b", "CRM Deal": "c"})
		self.assertLess(w.index("= 'CRM Deal'"), w.index("= 'CRM Lead'"))
		self.assertLess(w.index("= 'CRM Lead'"), w.index("= 'Contact'"))

	def test_deterministyczny(self: "TestWarunek") -> None:
		a = warunek_adresu("u@x.pl", {"Contact": "a", "CRM Deal": "c"})
		b = warunek_adresu("u@x.pl", {"CRM Deal": "c", "Contact": "a"})
		self.assertEqual(a, b)

	def test_brak_procenta(self: "TestWarunek") -> None:
		self.assertNotIn("%", warunek_adresu("u@x.pl", WSZYSTKIE))

	def test_procent_w_warunku_typu_odrzucony(self: "TestWarunek") -> None:
		with self.assertRaises(ValueError):
			warunek_adresu("u@x.pl", {"Contact": "name LIKE 'a%'"})

	def test_uzytkownik_z_apostrofem(self: "TestWarunek") -> None:
		w = warunek_adresu("o'x@x.pl", {})
		self.assertIn("'o\\'x@x.pl'", w)

	def test_uzytkownik_z_procentem(self: "TestWarunek") -> None:
		with self.assertRaises(ValueError):
			warunek_adresu("a%@x.pl", {})

	def test_create_bez_ograniczen(self: "TestWarunek") -> None:
		self.assertIn("create", PTYPY_BEZ_OGRANICZEN)
		self.assertNotIn("read", PTYPY_BEZ_OGRANICZEN)

	def test_cztery_galezie_przy_pustym_slowniku(self: "TestWarunek") -> None:
		w = warunek_adresu("u@x.pl", {})
		self.assertEqual(w.count(" OR "), 3)


class TestOrganizacja(unittest.TestCase):
	def test_galaz_organizacji_w_kazdym_przypadku(self: "TestOrganizacja") -> None:
		for slownik in ({}, {"Contact": "x=1"}, WSZYSTKIE):
			w = warunek_adresu("u@x.pl", slownik)
			self.assertIn("IN (SELECT `address` FROM `tabCRM Organization`", w)

	def test_galaz_d_wyklucza_organizacje(self: "TestOrganizacja") -> None:
		w = warunek_adresu("u@x.pl", {})
		self.assertIn("NOT IN (SELECT `address` FROM `tabCRM Organization`", w)
