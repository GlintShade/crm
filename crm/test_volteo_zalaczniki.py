import unittest

from crm.integrations.autenti.logika import nazwa_pliku_umowy, prefiks_pliku_kredytu
from crm.volteo_zalaczniki import (
	MAKS_DLUGOSC,
	czy_nazwa_systemowa,
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

	def test_s_nazwa_systemowa_umowa_pro(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_nazwa_systemowa("Umowa-PRO-CP-26-1024.pdf"))

	def test_s_nazwa_systemowa_umowa_pro_kod_czteroliterowy(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_nazwa_systemowa("Umowa-PRO-PVME-26-1000e41034.pdf"))

	def test_s_nazwa_systemowa_umowa_pro_kod_fallback(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_nazwa_systemowa("Umowa-PRO-XX-26-1050.pdf"))

	def test_s_nazwa_systemowa_umowa_legacy_crm_deal(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_nazwa_systemowa("Umowa-CRM-DEAL-2026-00016.pdf"))

	def test_s_nazwa_systemowa_formularz_kredytowy_pro(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(
			czy_nazwa_systemowa("Formularz-kredytowy-PRO-PV-26-1011-20260904-115057.pdf")
		)

	def test_s_nazwa_systemowa_umowa_podpisana(self: "TestVolteoZalaczniki") -> None:
		self.assertTrue(czy_nazwa_systemowa("Umowa-PRO-CP-26-1024-podpisana.pdf"))

	def test_t_nazwa_niesystemowa_umowa_najmu(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa("Umowa-najmu.pdf"))

	def test_t_nazwa_niesystemowa_umowa_pro_bez_reszty(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa("Umowa-PRO.pdf"))

	def test_t_nazwa_niesystemowa_umowa_pro_bez_numeru(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa("Umowa-PRO-CP-26.pdf"))

	def test_t_nazwa_niesystemowa_male_u_celowo(self: "TestVolteoZalaczniki") -> None:
		# Małe "u" na początku — celowo False: generator plików systemowych
		# zawsze pisze "Umowa-" z wielkiej litery.
		self.assertFalse(czy_nazwa_systemowa("umowa-PRO-CP-26-1024.pdf"))

	def test_t_nazwa_niesystemowa_skan(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa("skan.pdf"))

	def test_t_nazwa_niesystemowa_pusty_string(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa(""))

	def test_t_nazwa_niesystemowa_none(self: "TestVolteoZalaczniki") -> None:
		self.assertFalse(czy_nazwa_systemowa(None))

	def test_u_spojnosc_z_generatorami_dla_kilku_szans(self: "TestVolteoZalaczniki") -> None:
		# Dla realnych szans (bieżący format PRO/... i legacy CRM-DEAL-...),
		# nazwa wygenerowana przez generator umowy albo formularza kredytowego
		# musi zawsze zostać rozpoznana jako systemowa przez czy_nazwa_systemowa —
		# inaczej rezerwacja nazw nie chroniłaby własnej szansy.
		for deal in ("PRO/PV/26/1011", "PRO/CP/26/1024", "CRM-DEAL-2026-00016"):
			with self.subTest(deal=deal):
				self.assertTrue(czy_nazwa_systemowa(nazwa_pliku_umowy(deal)))
				self.assertTrue(
					czy_nazwa_systemowa(prefiks_pliku_kredytu(deal) + "-20260904-115057.pdf")
				)

	def test_v_spojnosc_czy_plik_systemowy_implikuje_czy_nazwa_systemowa(
		self: "TestVolteoZalaczniki",
	) -> None:
		# Każda nazwa, którą czy_plik_systemowy() (dla JEDNEJ szansy) uznaje za
		# systemową, musi też zostać uznana za systemową przez czy_nazwa_systemowa()
		# (dla DOWOLNEJ szansy) — ten drugi wzorzec musi być co najmniej tak
		# szeroki jak pierwszy, inaczej rezerwacja nazw miałaby dziury.
		warianty_sufiksow = ("", "-podpisana", "-podpisany", "e41034")
		for deal in ("PRO/PV/26/1011", "PRO/CP/26/1024", "CRM-DEAL-2026-00016"):
			nazwa_bazowa_umowy = nazwa_pliku_umowy(deal)[: -len(".pdf")]
			prefiks_kredytu = prefiks_pliku_kredytu(deal)
			for sufiks in warianty_sufiksow:
				for nazwa in (
					f"{nazwa_bazowa_umowy}{sufiks}.pdf",
					f"{prefiks_kredytu}{sufiks}.pdf",
				):
					with self.subTest(deal=deal, nazwa=nazwa):
						if czy_plik_systemowy(nazwa, deal):
							self.assertTrue(czy_nazwa_systemowa(nazwa))


if __name__ == "__main__":
	unittest.main()
