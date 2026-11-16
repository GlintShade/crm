import unittest

from crm.volteo_powiadomienia_zadan import (
	autor_wzmiankowany,
	czy_zadanie_automatyczne,
	etykieta_statusu,
	tekst_powiadomienia,
	wybierz_odbiorce,
	wykryj_zdarzenia,
)


class TestZadanieAutomatyczne(unittest.TestCase):
	def test_znacznik(self: "TestZadanieAutomatyczne") -> None:
		self.assertTrue(czy_zadanie_automatyczne(True, "Cokolwiek", None))

	def test_tytul_audytu_na_szansie(self: "TestZadanieAutomatyczne") -> None:
		self.assertTrue(czy_zadanie_automatyczne(False, "Audyt OZE: Kowalski", "CRM Deal"))
		self.assertTrue(czy_zadanie_automatyczne(False, "Audyt CP: Nowak", "CRM Deal"))

	def test_reczne(self: "TestZadanieAutomatyczne") -> None:
		self.assertFalse(czy_zadanie_automatyczne(False, "Zadzwonić", "CRM Deal"))
		self.assertFalse(czy_zadanie_automatyczne(False, "Audyt OZE: X", "CRM Lead"))
		self.assertFalse(czy_zadanie_automatyczne(False, None, None))


class TestZdarzenia(unittest.TestCase):
	def test_brak_zmian(self: "TestZdarzenia") -> None:
		stan = {"status": "Todo", "due_date": "2026-11-20 10:00:00", "assigned_to": "a@x"}
		self.assertEqual(wykryj_zdarzenia(stan, dict(stan)), [])

	def test_wszystkie(self: "TestZdarzenia") -> None:
		przed = {"status": "Todo", "due_date": None, "assigned_to": "a@x"}
		po = {"status": "Done", "due_date": "2026-11-20 10:00:00", "assigned_to": "b@x"}
		self.assertEqual(wykryj_zdarzenia(przed, po), ["status", "termin", "wykonawca"])

	def test_termin_do_minuty(self: "TestZdarzenia") -> None:
		przed = {"due_date": "2026-11-20 10:00:00"}
		po = {"due_date": "2026-11-20 10:00:30"}
		self.assertEqual(wykryj_zdarzenia(przed, po), [])

	def test_none_i_pusty_rowne(self: "TestZdarzenia") -> None:
		self.assertEqual(wykryj_zdarzenia({"assigned_to": None}, {"assigned_to": ""}), [])


class TestOdbiorca(unittest.TestCase):
	def test_inny_aktor(self: "TestOdbiorca") -> None:
		self.assertEqual(wybierz_odbiorce("a@x", "b@x", True, False), "a@x")

	def test_wlasna_zmiana(self: "TestOdbiorca") -> None:
		self.assertIsNone(wybierz_odbiorce("a@x", "a@x", True, False))

	def test_wylaczony(self: "TestOdbiorca") -> None:
		self.assertIsNone(wybierz_odbiorce("a@x", "b@x", False, False))

	def test_automatyczne(self: "TestOdbiorca") -> None:
		self.assertIsNone(wybierz_odbiorce("a@x", "b@x", True, True))

	def test_brak_autora(self: "TestOdbiorca") -> None:
		self.assertIsNone(wybierz_odbiorce(None, "b@x", True, False))
		self.assertIsNone(wybierz_odbiorce("Guest", "b@x", True, False))


class TestWzmianka(unittest.TestCase):
	def test_jest(self: "TestWzmianka") -> None:
		html = '<p>Hej <span class="mention" data-type="mention" data-id="A@X.pl" data-label="A">@A</span></p>'
		self.assertTrue(autor_wzmiankowany(html, "a@x.pl"))

	def test_inny(self: "TestWzmianka") -> None:
		html = '<span data-type="mention" data-id="c@x.pl" data-label="C">@C</span>'
		self.assertFalse(autor_wzmiankowany(html, "a@x.pl"))

	def test_pusty(self: "TestWzmianka") -> None:
		self.assertFalse(autor_wzmiankowany("", "a@x.pl"))
		self.assertFalse(autor_wzmiankowany("<p>a@x.pl</p>", "a@x.pl"))
		self.assertFalse(autor_wzmiankowany("<p>x</p>", None))


class TestTekst(unittest.TestCase):
	def test_escape(self: "TestTekst") -> None:
		t = tekst_powiadomienia("status", "Jan <b>", "Zad <i>", "Wykonane")
		self.assertIn("Jan &lt;b&gt;", t)
		self.assertIn("Zad &lt;i&gt;", t)
		self.assertIn("(Wykonane)", t)

	def test_wpis_bez_dopisku(self: "TestTekst") -> None:
		t = tekst_powiadomienia("wpis", "Jan", "Zad")
		self.assertIn("dodał(a) wpis w zadaniu", t)
		self.assertNotIn("</span> <span class=\"text-ink-gray-5\">(", t)

	def test_nieznane(self: "TestTekst") -> None:
		with self.assertRaises(ValueError):
			tekst_powiadomienia("x", "a", "b")

	def test_etykieta(self: "TestTekst") -> None:
		self.assertEqual(etykieta_statusu("Done"), "Wykonane")
		self.assertEqual(etykieta_statusu("Inny"), "Inny")
		self.assertEqual(etykieta_statusu(None), "")


if __name__ == "__main__":
	unittest.main()
