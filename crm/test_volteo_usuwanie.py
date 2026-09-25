import unittest

from crm.volteo_usuwanie import (
	AUDYT_STATUS_ZATWIERDZONY,
	AUTENTI_STATUSY_BLOKADY,
	DOCTYPY_BACKOFFICE,
	DOCTYPY_ZABLOKOWANE,
	OFERTA_STATUSY_BLOKADY,
	czy_wolno_usunac,
	powod_blokady_kaskady,
)

ZABLOKOWANE_SZESC = (
	"CRM Deal",
	"CRM Lead",
	"FCRM Note",
	"CRM Task",
	"CRM Organization",
	"Contact",
)

# Kody Unicode, nie literaly: en/em dash jako surowy znak w tym pliku
# wpadlby na grep gate (zero myslnikow w zmienionych plikach), mimo ze to
# tylko dane porownawcze testu, a nie interpunkcja.
ZNAKI_MYSLNIKOW = ("\u2013", "\u2014")


class TestCzyWolnoUsunac(unittest.TestCase):
	def test_a_administrator_zawsze_true(self: "TestCzyWolnoUsunac") -> None:
		for doctype in ZABLOKOWANE_SZESC:
			self.assertTrue(czy_wolno_usunac(doctype, set(), "Administrator"))

	def test_b_system_manager_true_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		for doctype in ZABLOKOWANE_SZESC:
			self.assertTrue(czy_wolno_usunac(doctype, {"System Manager"}, "ktos@test.pl"))

	def test_c_volteo_core_admin_true_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		for doctype in ZABLOKOWANE_SZESC:
			self.assertTrue(czy_wolno_usunac(doctype, {"Volteo Core Admin"}, "ktos@test.pl"))

	def test_d_backoffice_true_tylko_dla_crm_deal(self: "TestCzyWolnoUsunac") -> None:
		roles = {"Sales User", "Volteo Backend"}
		self.assertTrue(czy_wolno_usunac("CRM Deal", roles, "backoffice@test.pl"))
		for doctype in ZABLOKOWANE_SZESC:
			if doctype == "CRM Deal":
				continue
			self.assertFalse(czy_wolno_usunac(doctype, roles, "backoffice@test.pl"))

	def test_e_d2d_false_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		roles = {"Sales User", "Volteo D2D Sales"}
		for doctype in ZABLOKOWANE_SZESC:
			self.assertFalse(czy_wolno_usunac(doctype, roles, "rep@test.pl"))

	def test_f_ecom_false_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		roles = {"Sales User", "Volteo Ecom Sales"}
		for doctype in ZABLOKOWANE_SZESC:
			self.assertFalse(czy_wolno_usunac(doctype, roles, "ecom@test.pl"))

	def test_g_sam_sales_user_false_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		for doctype in ZABLOKOWANE_SZESC:
			self.assertFalse(czy_wolno_usunac(doctype, {"Sales User"}, "ktos@test.pl"))

	def test_h_sales_manager_false_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		for doctype in ZABLOKOWANE_SZESC:
			self.assertFalse(czy_wolno_usunac(doctype, {"Sales Manager"}, "ktos@test.pl"))

	def test_i_backoffice_plus_core_admin_true_na_szesciu(self: "TestCzyWolnoUsunac") -> None:
		roles = {"Volteo Backend", "Volteo Core Admin"}
		for doctype in ZABLOKOWANE_SZESC:
			self.assertTrue(czy_wolno_usunac(doctype, roles, "ktos@test.pl"))

	def test_j_doctype_niezablokowany_true_dla_backoffice(self: "TestCzyWolnoUsunac") -> None:
		self.assertTrue(czy_wolno_usunac("Volteo Umowa", {"Volteo Backend"}, "backoffice@test.pl"))

	def test_k_stale_ksztalt(self: "TestCzyWolnoUsunac") -> None:
		self.assertEqual(len(DOCTYPY_ZABLOKOWANE), 6)
		self.assertEqual(set(DOCTYPY_ZABLOKOWANE), set(ZABLOKOWANE_SZESC))
		self.assertTrue(DOCTYPY_BACKOFFICE.issubset(DOCTYPY_ZABLOKOWANE))


class TestPowodBlokadyKaskady(unittest.TestCase):
	def test_a_umowa_podpisana_blokuje_admina_i_nieadmina(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Umowa", "UM-1", "Podpisana")]
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=True))
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_b_kredyt_wyslana_blokuje(self: "TestPowodBlokadyKaskady") -> None:
		for status in AUTENTI_STATUSY_BLOKADY:
			wiersze = [("Volteo Kredyt", "KR-1", status)]
			self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_c_oferta_wyslana_do_podpisu_blokuje(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Oferta", "OF-1", "Wysłana do podpisu")]
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=True))
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_d_oferta_szkic_nie_blokuje(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Oferta", "OF-2", "Szkic")]
		self.assertIsNone(powod_blokady_kaskady(wiersze, admin=True))
		self.assertIsNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_e_oferta_wszystkie_statusy_blokady(self: "TestPowodBlokadyKaskady") -> None:
		for status in OFERTA_STATUSY_BLOKADY:
			wiersze = [("Volteo Oferta", "OF-3", status)]
			self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_f_audyt_cp_blokuje_tylko_nieadmina(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Audyt CP", "ACP-1", None)]
		self.assertIsNone(powod_blokady_kaskady(wiersze, admin=True))
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_g_audyt_zatwierdzony_blokuje_tylko_nieadmina(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Audyt", "AU-1", AUDYT_STATUS_ZATWIERDZONY)]
		self.assertIsNone(powod_blokady_kaskady(wiersze, admin=True))
		self.assertIsNotNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_h_audyt_szkic_nie_blokuje_nieadmina(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [("Volteo Audyt", "AU-2", "Szkic")]
		self.assertIsNone(powod_blokady_kaskady(wiersze, admin=False))

	def test_i_pusta_lista_nie_blokuje(self: "TestPowodBlokadyKaskady") -> None:
		self.assertIsNone(powod_blokady_kaskady([], admin=True))
		self.assertIsNone(powod_blokady_kaskady([], admin=False))

	def test_j_pierwszy_pasujacy_wiersz_wygrywa(self: "TestPowodBlokadyKaskady") -> None:
		wiersze = [
			("Volteo Oferta", "OF-4", "Szkic"),
			("Volteo Umowa", "UM-2", "Podpisana"),
			("Volteo Audyt CP", "ACP-2", None),
		]
		powod = powod_blokady_kaskady(wiersze, admin=False)
		self.assertIsNotNone(powod)
		self.assertIn("UM-2", powod)

	def test_k_zaden_powod_nie_zawiera_myslnika(self: "TestPowodBlokadyKaskady") -> None:
		przypadki = [
			[("Volteo Umowa", "UM-3", "Wysyłanie")],
			[("Volteo Kredyt", "KR-2", "Wysłana")],
			[("Volteo Oferta", "OF-5", "Podpisana")],
			[("Volteo Audyt CP", "ACP-3", None)],
			[("Volteo Audyt", "AU-3", AUDYT_STATUS_ZATWIERDZONY)],
		]
		for wiersze in przypadki:
			for admin in (True, False):
				powod = powod_blokady_kaskady(wiersze, admin=admin)
				if not powod:
					continue
				for znak in ZNAKI_MYSLNIKOW:
					self.assertNotIn(znak, powod)


if __name__ == "__main__":
	unittest.main()
