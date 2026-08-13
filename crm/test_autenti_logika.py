import unittest

from crm.integrations.autenti.logika import (
	PENDING_REMOTE_STATUSES,
	SEND_BLOCKED_STATUSES,
	STATUS_MAP,
	mozna_wyslac,
	nazwa_pliku_podpisanego,
	nazwa_pliku_umowy,
	tytul_dokumentu,
)


class TestAutentiLogika(unittest.TestCase):
	def test_a_status_map_kompletnosc(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			STATUS_MAP,
			{
				"COMPLETED": "Podpisana",
				"REJECTED": "Odrzucona",
				"EXPIRED": "Wygasła",
				"WITHDRAWN": "Wycofana",
			},
		)
		# Mapowane statusy i statusy oczekujące (nieterminalne) nigdy się nie pokrywają.
		self.assertFalse(set(STATUS_MAP) & set(PENDING_REMOTE_STATUSES))

	def test_b_mozna_wyslac_brak_wyslania(self: "TestAutentiLogika") -> None:
		self.assertTrue(mozna_wyslac(None))
		self.assertTrue(mozna_wyslac(""))

	def test_c_mozna_wyslac_statusy_zablokowane(self: "TestAutentiLogika") -> None:
		for status in SEND_BLOCKED_STATUSES:
			with self.subTest(status=status):
				self.assertFalse(mozna_wyslac(status))

	def test_d_mozna_wyslac_statusy_do_ponowienia(self: "TestAutentiLogika") -> None:
		for status in ("Błąd", "Odrzucona", "Wygasła", "Wycofana"):
			with self.subTest(status=status):
				self.assertTrue(mozna_wyslac(status))

	def test_e_mozna_wyslac_nierozpoznany_status(self: "TestAutentiLogika") -> None:
		self.assertFalse(mozna_wyslac("Coś nieznanego"))

	def test_f_tytul_dokumentu_normalny(self: "TestAutentiLogika") -> None:
		self.assertEqual(tytul_dokumentu("Jan Kowalski"), "Umowa ProEnergy — Jan Kowalski")
		self.assertIn("—", tytul_dokumentu("Jan Kowalski"))

	def test_g_tytul_dokumentu_puste_imie(self: "TestAutentiLogika") -> None:
		self.assertEqual(tytul_dokumentu(None), "Umowa ProEnergy")
		self.assertEqual(tytul_dokumentu(""), "Umowa ProEnergy")
		self.assertNotIn("—", tytul_dokumentu(None))

	def test_h_nazwa_pliku_umowy(self: "TestAutentiLogika") -> None:
		self.assertEqual(nazwa_pliku_umowy("PRO/CP/26/0007"), "Umowa-PRO-CP-26-0007.pdf")

	def test_i_nazwa_pliku_podpisanego(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_podpisanego("PRO/CP/26/0007"), "Umowa-PRO-CP-26-0007-podpisana.pdf"
		)


if __name__ == "__main__":
	unittest.main()
