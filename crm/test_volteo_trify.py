import unittest

from crm.volteo_trify import DOCTYPE, TYPY, tekst_pusty, zbuduj_powiadomienie


class TestVolteoTrifyTekstPusty(unittest.TestCase):
	def test_a_none_i_pusty_string_sa_puste(self: "TestVolteoTrifyTekstPusty") -> None:
		self.assertTrue(tekst_pusty(None))
		self.assertTrue(tekst_pusty(""))

	def test_b_pusty_akapit_tiptapa_jest_pusty(self: "TestVolteoTrifyTekstPusty") -> None:
		self.assertTrue(tekst_pusty("<p></p>"))

	def test_c_nbsp_jest_pusty(self: "TestVolteoTrifyTekstPusty") -> None:
		self.assertTrue(tekst_pusty("<p>&nbsp;</p>"))

	def test_d_sam_br_jest_pusty(self: "TestVolteoTrifyTekstPusty") -> None:
		self.assertTrue(tekst_pusty("<p><br></p>"))

	def test_e_tekst_nie_jest_pusty(self: "TestVolteoTrifyTekstPusty") -> None:
		self.assertFalse(tekst_pusty("<p>x</p>"))

	def test_f_tekst_ze_wzmianka_nie_jest_pusty(self: "TestVolteoTrifyTekstPusty") -> None:
		html = '<p>Hej <span class="mention" data-type="mention" data-id="a@b.pl">@A</span></p>'
		self.assertFalse(tekst_pusty(html))


class TestVolteoTrifyTypy(unittest.TestCase):
	def test_a_szesc_elementow(self: "TestVolteoTrifyTypy") -> None:
		self.assertEqual(len(TYPY), 6)

	def test_b_pierwszy_to_notatka(self: "TestVolteoTrifyTypy") -> None:
		self.assertEqual(TYPY[0], "Notatka")

	def test_c_bez_duplikatow(self: "TestVolteoTrifyTypy") -> None:
		self.assertEqual(len(TYPY), len(set(TYPY)))


class TestVolteoTrifyZbudujPowiadomienie(unittest.TestCase):
	def test_a_komplet_kluczy(self: "TestVolteoTrifyZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie("autor@proenergy.pro", "Jan Kowalski", "PRO/CP/26/0001", "TU-0001", "b@proenergy.pro")
		oczekiwane_klucze = {
			"owner",
			"assigned_to",
			"notification_type",
			"message",
			"notification_text",
			"reference_doctype",
			"reference_docname",
			"redirect_to_doctype",
			"redirect_to_docname",
		}
		self.assertEqual(set(wynik.keys()), oczekiwane_klucze)

	def test_b_typ_i_referencje(self: "TestVolteoTrifyZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie("autor@proenergy.pro", "Jan Kowalski", "PRO/CP/26/0001", "TU-0001", "b@proenergy.pro")
		self.assertEqual(wynik["notification_type"], "Mention")
		self.assertEqual(wynik["redirect_to_doctype"], "CRM Deal")
		self.assertEqual(wynik["reference_doctype"], DOCTYPE)
		self.assertEqual(wynik["reference_docname"], "TU-0001")
		self.assertEqual(wynik["redirect_to_docname"], "PRO/CP/26/0001")
		self.assertEqual(wynik["owner"], "autor@proenergy.pro")
		self.assertEqual(wynik["assigned_to"], "b@proenergy.pro")

	def test_c_nazwa_autora_i_szansy_w_html(self: "TestVolteoTrifyZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie("autor@proenergy.pro", "Jan Kowalski", "PRO/CP/26/0001", "TU-0001", "b@proenergy.pro")
		self.assertIn("Jan Kowalski", wynik["message"])
		self.assertIn("PRO/CP/26/0001", wynik["message"])
		self.assertIn("Jan Kowalski", wynik["notification_text"])
		self.assertIn("PRO/CP/26/0001", wynik["notification_text"])

	def test_d_escapowanie_nazwy_autora(self: "TestVolteoTrifyZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie("autor@proenergy.pro", "<script>alert(1)</script>", "PRO/CP/26/0001", "TU-0001", "b@proenergy.pro")
		self.assertNotIn("<script>", wynik["message"])
		self.assertIn("&lt;script&gt;", wynik["message"])


if __name__ == "__main__":
	unittest.main()
