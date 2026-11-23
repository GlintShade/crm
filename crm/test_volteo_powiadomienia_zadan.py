import unittest

from crm.volteo_powiadomienia_zadan import (
	autor_wzmiankowany,
	czy_zadanie_automatyczne,
	etykieta_statusu,
	nowo_dodani,
	tekst_powiadomienia,
	wybierz_odbiorce,
	wybierz_odbiorcow,
	wyczysc_do_wiadomosci,
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


class TestOdbiorcy(unittest.TestCase):
	AKTYWNI = frozenset({"a@x", "b@x", "c@x"})

	def test_autor_i_wykonawca(self: "TestOdbiorcy") -> None:
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "c@x", self.AKTYWNI, False), ["a@x", "b@x"])

	def test_ta_sama_osoba_raz(self: "TestOdbiorcy") -> None:
		self.assertEqual(
			wybierz_odbiorcow("a@x", ["a@x", "b@x", "b@x"], "c@x", self.AKTYWNI, False), ["a@x", "b@x"]
		)

	def test_aktor_pominiety(self: "TestOdbiorcy") -> None:
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "a@x", self.AKTYWNI, False), ["b@x"])
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "b@x", self.AKTYWNI, False), ["a@x"])

	def test_automatyczne_wykonawca_tak_autor_nie(self: "TestOdbiorcy") -> None:
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "c@x", self.AKTYWNI, True), ["b@x"])

	def test_wylaczony(self: "TestOdbiorcy") -> None:
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "c@x", {"a@x"}, False), ["a@x"])

	def test_pomin_i_puste(self: "TestOdbiorcy") -> None:
		self.assertEqual(
			wybierz_odbiorcow("a@x", [None, "b@x"], "c@x", self.AKTYWNI, False, {"b@x"}), ["a@x"]
		)
		self.assertEqual(wybierz_odbiorcow(None, [], "c@x", self.AKTYWNI, False), [])


class TestWzmianka(unittest.TestCase):
	def test_jest(self: "TestWzmianka") -> None:
		html = (
			'<p>Hej <span class="mention" data-type="mention" data-id="A@X.pl" data-label="A">@A</span></p>'
		)
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
		self.assertNotIn('</span> <span class="text-ink-gray-5">(', t)

	def test_nieznane(self: "TestTekst") -> None:
		with self.assertRaises(ValueError):
			tekst_powiadomienia("x", "a", "b")

	def test_etykieta(self: "TestTekst") -> None:
		self.assertEqual(etykieta_statusu("Done"), "Wykonane")
		self.assertEqual(etykieta_statusu("Inny"), "Inny")
		self.assertEqual(etykieta_statusu(None), "")


class TestDoWiadomosci(unittest.TestCase):
	AKTYWNI = frozenset({"a@x", "b@x", "c@x", "d@x"})

	def test_wyczysc_duplikaty_puste_i_wykonawca(self: "TestDoWiadomosci") -> None:
		self.assertEqual(
			wyczysc_do_wiadomosci(["d@x", None, "", "c@x", "d@x", "b@x"], "b@x"), ["d@x", "c@x"]
		)
		self.assertEqual(wyczysc_do_wiadomosci(None, "b@x"), [])
		self.assertEqual(wyczysc_do_wiadomosci(["b@x"], None), ["b@x"])

	def test_wyczysc_nie_mutuje(self: "TestDoWiadomosci") -> None:
		wejscie = ["b@x", "c@x"]
		wyczysc_do_wiadomosci(wejscie, "b@x")
		self.assertEqual(wejscie, ["b@x", "c@x"])

	def test_nowo_dodani(self: "TestDoWiadomosci") -> None:
		self.assertEqual(nowo_dodani(["a@x"], ["a@x", "b@x", "b@x"]), ["b@x"])
		self.assertEqual(nowo_dodani(None, ["a@x"]), ["a@x"])
		self.assertEqual(nowo_dodani(["a@x"], ["a@x"]), [])
		self.assertEqual(nowo_dodani(["a@x"], []), [])

	def test_trzecia_grupa_odbiorcow(self: "TestDoWiadomosci") -> None:
		self.assertEqual(
			wybierz_odbiorcow("a@x", ["b@x"], "z@x", self.AKTYWNI, False, do_wiadomosci=["c@x", "d@x"]),
			["a@x", "b@x", "c@x", "d@x"],
		)

	def test_dw_pomija_aktora_nieaktywnych_i_duplikat(self: "TestDoWiadomosci") -> None:
		self.assertEqual(
			wybierz_odbiorcow("a@x", [], "c@x", {"a@x", "c@x"}, False, do_wiadomosci=["c@x", "d@x", "a@x"]),
			["a@x"],
		)

	def test_dw_dostaje_przy_zadaniu_automatycznym(self: "TestDoWiadomosci") -> None:
		self.assertEqual(
			wybierz_odbiorcow("a@x", ["b@x"], "z@x", self.AKTYWNI, True, do_wiadomosci=["c@x"]),
			["b@x", "c@x"],
		)

	def test_bez_dw_jak_dotad(self: "TestDoWiadomosci") -> None:
		self.assertEqual(wybierz_odbiorcow("a@x", ["b@x"], "z@x", self.AKTYWNI, False), ["a@x", "b@x"])

	def test_tekst_dw(self: "TestDoWiadomosci") -> None:
		self.assertIn("dodał(a) Cię do wiadomości w zadaniu", tekst_powiadomienia("dw", "Jan", "Zad"))


if __name__ == "__main__":
	unittest.main()
