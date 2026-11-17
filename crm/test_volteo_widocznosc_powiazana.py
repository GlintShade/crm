import unittest

from crm.volteo_widocznosc_powiazana import (
	literal_sql,
	nazwa_tabeli,
	polacz_haki,
	warunek_bez_znacznikow,
	warunek_pliku,
	warunek_powiazania,
)


class TestLiteral(unittest.TestCase):
	def test_prosty(self: "TestLiteral") -> None:
		self.assertEqual(literal_sql("abc"), "'abc'")

	def test_apostrof_i_ukosnik(self: "TestLiteral") -> None:
		self.assertEqual(literal_sql("o'b"), "'o\\'b'")
		self.assertEqual(literal_sql("a\\b"), "'a\\\\b'")

	def test_niedozwolone(self: "TestLiteral") -> None:
		for zle in ("a%b", "a\x00b", "a\nb", "a\rb"):
			with self.assertRaises(ValueError):
				literal_sql(zle)


class TestTabela(unittest.TestCase):
	def test_poprawna(self: "TestTabela") -> None:
		self.assertEqual(nazwa_tabeli("CRM Deal"), "`tabCRM Deal`")

	def test_niedozwolone(self: "TestTabela") -> None:
		for zle in ("a`b", "a%b", "a'b", 'a"b', "a\\b"):
			with self.assertRaises(ValueError):
				nazwa_tabeli(zle)


class TestPolaczHaki(unittest.TestCase):
	def test_puste(self: "TestPolaczHaki") -> None:
		self.assertEqual(polacz_haki([]), "")
		self.assertEqual(polacz_haki([None, "", "  "]), "")

	def test_nawiasy(self: "TestPolaczHaki") -> None:
		self.assertEqual(polacz_haki(["a OR b"]), "(a OR b)")
		self.assertEqual(polacz_haki(["a OR b", None, " c "]), "(a OR b) AND (c)")


class TestPowiazanie(unittest.TestCase):
	def test_puste(self: "TestPowiazanie") -> None:
		self.assertEqual(warunek_powiazania("Comment", "reference_doctype", "reference_name", {}), "")
		self.assertEqual(warunek_powiazania("Comment", "reference_doctype", "reference_name", {}, {}), "")

	def test_warunek_w_nawiasach(self: "TestPowiazanie") -> None:
		w = warunek_powiazania("Comment", "reference_doctype", "reference_name", {"CRM Deal": "a OR b"})
		self.assertIn("WHERE (a OR b)", w)
		self.assertTrue(w.startswith("(") and w.endswith(")"))
		self.assertIn("ifnull(`tabComment`.`reference_doctype`, '') = ''", w)
		self.assertIn("NOT IN ('CRM Deal')", w)
		self.assertIn("`tabComment`.`reference_name` IN (SELECT `name` FROM `tabCRM Deal`", w)

	def test_kolejnosc_posortowana(self: "TestPowiazanie") -> None:
		w = warunek_powiazania("Comment", "reference_doctype", "reference_name", {"Z": "1", "A": "2"})
		self.assertIn("NOT IN ('A', 'Z')", w)
		self.assertLess(w.index("= 'A'"), w.index("= 'Z'"))

	def test_galaz_dodatkowa(self: "TestPowiazanie") -> None:
		w = warunek_powiazania(
			"Comment", "reference_doctype", "reference_name", {}, {"Comment": "owner = 'x'"}
		)
		self.assertIn("`tabComment`.`reference_doctype` = 'Comment' AND (owner = 'x')", w)
		self.assertNotIn("SELECT", w)

	def test_galaz_dodatkowa_wygrywa(self: "TestPowiazanie") -> None:
		w = warunek_powiazania(
			"Comment", "reference_doctype", "reference_name", {"Comment": "zly"}, {"Comment": "dobry"}
		)
		self.assertIn("dobry", w)
		self.assertNotIn("zly", w)

	def test_bez_procenta(self: "TestPowiazanie") -> None:
		w = warunek_powiazania("Comment", "reference_doctype", "reference_name", {"CRM Deal": "x=1"})
		self.assertNotIn("%", w)

	def test_zla_nazwa_pola(self: "TestPowiazanie") -> None:
		with self.assertRaises(ValueError):
			warunek_powiazania("Comment", "a`b", "reference_name", {"X": "1"})
		with self.assertRaises(ValueError):
			warunek_powiazania("Comment", "reference_doctype", "", {"X": "1"})

	def test_zly_typ(self: "TestPowiazanie") -> None:
		with self.assertRaises(ValueError):
			warunek_powiazania("Comment", "t", "n", {"a`b": "1"})

	def test_apostrof_w_typie_odrzucony(self: "TestPowiazanie") -> None:
		with self.assertRaises(ValueError):
			warunek_powiazania("Comment", "t", "n", {"O'Neil": "1"})


class TestBezZnacznikow(unittest.TestCase):
	def test_puste(self: "TestBezZnacznikow") -> None:
		self.assertEqual(warunek_bez_znacznikow("Comment", "content", []), "")

	def test_ksztalt_i_kolejnosc(self: "TestBezZnacznikow") -> None:
		w = warunek_bez_znacznikow("Comment", "content", ["[b]", "[a]", "[a]"])
		self.assertEqual(
			w,
			"(LOCATE('[a]', ifnull(`tabComment`.`content`, '')) = 0 AND "
			"LOCATE('[b]', ifnull(`tabComment`.`content`, '')) = 0)",
		)

	def test_bez_procenta(self: "TestBezZnacznikow") -> None:
		self.assertNotIn("%", warunek_bez_znacznikow("Comment", "content", ["[volteo:cc]"]))

	def test_procent_w_znaczniku(self: "TestBezZnacznikow") -> None:
		with self.assertRaises(ValueError):
			warunek_bez_znacznikow("Comment", "content", ["50%"])


class TestWarunekPliku(unittest.TestCase):
	def test_pusty_powiazanie(self: "TestWarunekPliku") -> None:
		self.assertEqual(warunek_pliku("u@x.pl", ""), "")

	def test_ksztalt(self: "TestWarunekPliku") -> None:
		w = warunek_pliku("u@x.pl", "(p)")
		self.assertEqual(
			w,
			"(`tabFile`.`is_private` = 0 OR `tabFile`.`owner` = 'u@x.pl' "
			"OR `tabFile`.`is_folder` = 1 OR (p))",
		)

	def test_bez_procenta(self: "TestWarunekPliku") -> None:
		self.assertNotIn("%", warunek_pliku("u@x.pl", "(p)"))

	def test_apostrof_uzytkownika(self: "TestWarunekPliku") -> None:
		self.assertIn("'o\\'x@x.pl'", warunek_pliku("o'x@x.pl", "(p)"))

	def test_zly_uzytkownik(self: "TestWarunekPliku") -> None:
		with self.assertRaises(ValueError):
			warunek_pliku("a%b", "(p)")

	def test_zagniezdzenie_z_powiazaniem(self: "TestWarunekPliku") -> None:
		pow_ = warunek_powiazania(
			"File", "attached_to_doctype", "attached_to_name", {"CRM Deal": "a OR b", "Comment": "c"}
		)
		w = warunek_pliku("u@x.pl", pow_)
		self.assertIn("WHERE (a OR b)", w)
		self.assertIn("FROM `tabComment` WHERE (c)", w)
		self.assertTrue(w.startswith("(") and w.endswith(")"))


if __name__ == "__main__":
	unittest.main()
