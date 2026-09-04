import unittest

from crm.volteo_zalaczniki import (
	MAKS_DLUGOSC,
	czy_plik_systemowy,
	nowa_nazwa_pliku,
	rozszerzenie,
)


class TestVolteoZalaczniki(unittest.TestCase):
	def test_a_rozszerzenie_zachowane(self: "TestVolteoZalaczniki") -> None:
		self.assertEqual(
			nowa_nazwa_pliku("Adobe Scan 02 wrz 2026 (1).pdf", "Formularz kredytowy"),
			"Formularz kredytowy.pdf",
		)

	def test_b_rozszerzenie_z_wielu_kropek_bierze_ostatnia(self: "TestVolteoZalaczniki") -> None:
		self.assertEqual(rozszerzenie("Adobe Scan (1).pdf"), ".pdf")
		self.assertEqual(rozszerzenie("archiwum.tar.gz"), ".gz")

	def test_c_brak_rozszerzenia_w_starej_nazwie(self: "TestVolteoZalaczniki") -> None:
		self.assertEqual(nowa_nazwa_pliku("bezrozszerzenia", "Nowa nazwa"), "Nowa nazwa")
		self.assertEqual(rozszerzenie("bezrozszerzenia"), "")

	def test_d_biale_znaki_obcinane(self: "TestVolteoZalaczniki") -> None:
		self.assertEqual(nowa_nazwa_pliku("stara.pdf", "  Nowy trzon  "), "Nowy trzon.pdf")

	def test_e_pusty_trzon_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", "")

	def test_f_sam_biały_znak_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", "   ")

	def test_g_ukosnik_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", "nowy/trzon")

	def test_h_wsteczny_ukosnik_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", "nowy\\trzon")

	def test_i_znak_sterujacy_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", "nowy\ttrzon")

	def test_j_zbyt_dluga_nazwa_rzuca_blad(self: "TestVolteoZalaczniki") -> None:
		trzon = "a" * (MAKS_DLUGOSC - len(".pdf") + 1)
		with self.assertRaises(ValueError):
			nowa_nazwa_pliku("stara.pdf", trzon)

	def test_k_dokladnie_maks_dlugosc_ok(self: "TestVolteoZalaczniki") -> None:
		trzon = "a" * (MAKS_DLUGOSC - len(".pdf"))
		nowa = nowa_nazwa_pliku("stara.pdf", trzon)
		self.assertEqual(len(nowa), MAKS_DLUGOSC)

	def test_l_plik_umowy_niepodpisanej_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_plik_systemowy("Umowa-PRO-PV-26-1011.pdf", "PRO/PV/26/1011"))

	def test_m_plik_umowy_podpisanej_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_plik_systemowy("Umowa-PRO-PV-26-1011-podpisana.pdf", "PRO/PV/26/1011"))

	def test_n_plik_umowy_ze_znacznikiem_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_plik_systemowy("Umowa-PRO-PV-26-1011e41034.pdf", "PRO/PV/26/1011"))

	def test_o_plik_kredytu_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		from crm.integrations.autenti.logika import prefiks_pliku_kredytu

		nazwa = prefiks_pliku_kredytu("PRO/PV/26/1011") + "-podpisany.pdf"
		self.assertTrue(czy_plik_systemowy(nazwa, "PRO/PV/26/1011"))

	def test_p_zwykly_plik_nie_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_plik_systemowy("Adobe Scan.pdf", "PRO/PV/26/1011"))

	def test_q_plik_umowy_innej_szansy_nie_jest_systemowy(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_plik_systemowy("Umowa-PRO-PV-26-2222.pdf", "PRO/PV/26/1011"))

	def test_r_pusta_nazwa_pliku_nie_jest_systemowa(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_plik_systemowy("", "PRO/PV/26/1011"))


if __name__ == "__main__":
	unittest.main()
