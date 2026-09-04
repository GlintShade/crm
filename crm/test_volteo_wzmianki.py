import unittest

from crm.volteo_wzmianki import WYKLUCZENI_ZAWSZE, wybierz_wzmiankowalnych


class TestVolteoWzmianki(unittest.TestCase):
	def test_a_bypass_zwraca_wszystkich_crm(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="admin@proenergy.pro",
			role_wolajacego={"Volteo Core Admin"},
			bypass=True,
			zarzad=["zarzad@proenergy.pro"],
			backoffice=["backoffice@proenergy.pro"],
			poddrzewo=["rep1@proenergy.pro"],
			wszyscy_crm=["admin@proenergy.pro", "rep1@proenergy.pro", "rep2@proenergy.pro", "zarzad@proenergy.pro"],
		)
		self.assertEqual(wynik, ["rep1@proenergy.pro", "rep2@proenergy.pro", "zarzad@proenergy.pro"])

	def test_b_rep_w_drzewie_widzi_zarzad_backoffice_i_poddrzewo(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="manager@proenergy.pro",
			role_wolajacego={"Sales Manager"},
			bypass=False,
			zarzad=["core1@proenergy.pro", "core2@proenergy.pro"],
			backoffice=["back1@proenergy.pro"],
			poddrzewo=["manager@proenergy.pro", "rep1@proenergy.pro", "rep2@proenergy.pro"],
			wszyscy_crm=["ktokolwiek@proenergy.pro"],
		)
		self.assertEqual(
			wynik,
			[
				"back1@proenergy.pro",
				"core1@proenergy.pro",
				"core2@proenergy.pro",
				"rep1@proenergy.pro",
				"rep2@proenergy.pro",
			],
		)

	def test_c_rep_poza_drzewem_widzi_tylko_zarzad_i_backoffice(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="rep@proenergy.pro",
			role_wolajacego={"Volteo D2D Sales"},
			bypass=False,
			zarzad=["core1@proenergy.pro"],
			backoffice=["back1@proenergy.pro"],
			poddrzewo=None,
			wszyscy_crm=["ktokolwiek@proenergy.pro"],
		)
		self.assertEqual(wynik, ["back1@proenergy.pro", "core1@proenergy.pro"])

	def test_d_wyklucza_siebie(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="core1@proenergy.pro",
			role_wolajacego={"Volteo Core Admin"},
			bypass=False,
			zarzad=["core1@proenergy.pro", "core2@proenergy.pro"],
			backoffice=[],
			poddrzewo=None,
			wszyscy_crm=[],
		)
		self.assertEqual(wynik, ["core2@proenergy.pro"])

	def test_e_wyklucza_administratora_i_guest_zawsze(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="ktos@proenergy.pro",
			role_wolajacego=set(),
			bypass=True,
			zarzad=[],
			backoffice=[],
			poddrzewo=None,
			wszyscy_crm=["Administrator", "Guest", "ktos@proenergy.pro", "rep1@proenergy.pro"],
		)
		self.assertEqual(wynik, ["rep1@proenergy.pro"])
		self.assertEqual(WYKLUCZENI_ZAWSZE, ("Administrator", "Guest"))

	def test_f_deduplikuje_nakladajace_sie_zbiory(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="wolajacy@proenergy.pro",
			role_wolajacego=set(),
			bypass=False,
			zarzad=["core1@proenergy.pro"],
			backoffice=["core1@proenergy.pro"],
			poddrzewo=["core1@proenergy.pro", "rep1@proenergy.pro"],
			wszyscy_crm=[],
		)
		self.assertEqual(wynik, ["core1@proenergy.pro", "rep1@proenergy.pro"])

	def test_g_sortowanie_alfabetyczne(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="wolajacy@proenergy.pro",
			role_wolajacego=set(),
			bypass=False,
			zarzad=["zorro@proenergy.pro", "adam@proenergy.pro"],
			backoffice=["mira@proenergy.pro"],
			poddrzewo=None,
			wszyscy_crm=[],
		)
		self.assertEqual(wynik, ["adam@proenergy.pro", "mira@proenergy.pro", "zorro@proenergy.pro"])

	def test_h_puste_wejscia_daja_pusta_liste(self: "TestVolteoWzmianki") -> None:
		wynik = wybierz_wzmiankowalnych(
			wolajacy="wolajacy@proenergy.pro",
			role_wolajacego=set(),
			bypass=False,
			zarzad=[],
			backoffice=[],
			poddrzewo=None,
			wszyscy_crm=[],
		)
		self.assertEqual(wynik, [])


if __name__ == "__main__":
	unittest.main()
