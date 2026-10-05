import unittest

from crm.volteo_naming import FALLBACK_CODE, UMOWA_CODES, code_for, format_deal_name


class TestVolteoNaming(unittest.TestCase):
	def test_a_kody_znanych_rodzajow(self: "TestVolteoNaming") -> None:
		self.assertEqual(code_for("Fotowoltaika"), "PV")
		self.assertEqual(code_for("Fotowoltaika + Magazyn"), "PVME")
		self.assertEqual(code_for("Magazyn energii"), "ME")
		self.assertEqual(code_for("Czyste Powietrze"), "CP")

	def test_a2_kody_nowych_rodzajow_b68(self: "TestVolteoNaming") -> None:
		# Paczka "Wielki update kalkulatora OZE" (b68, chunk B3): "Kocioł" mapuje
		# się na kod PP, nie KO (decyzja właściciela 2026-10-04), patrz docstring
		# UMOWA_CODES.
		self.assertEqual(code_for("Rozbudowa PV/ME"), "ROZ")
		self.assertEqual(code_for("Klimatyzacja"), "KL")
		self.assertEqual(code_for("Pompa ciepła"), "PC")
		self.assertEqual(code_for("Kocioł"), "PP")

	def test_b_brak_rodzaju_daje_fallback(self: "TestVolteoNaming") -> None:
		self.assertEqual(code_for(None), FALLBACK_CODE)
		self.assertEqual(code_for(""), FALLBACK_CODE)

	def test_c_nieznany_rodzaj_daje_fallback(self: "TestVolteoNaming") -> None:
		self.assertEqual(code_for("Coś nieznanego"), FALLBACK_CODE)

	def test_d_skladanie_nazwy(self: "TestVolteoNaming") -> None:
		self.assertEqual(format_deal_name("PV", "26", "1000"), "PRO/PV/26/1000")
		self.assertEqual(format_deal_name(FALLBACK_CODE, "26", "0042"), "PRO/XX/26/0042")

	def test_e_code_for_nie_mutuje_umowa_codes(self: "TestVolteoNaming") -> None:
		przed = dict(UMOWA_CODES)
		code_for("Fotowoltaika")
		code_for(None)
		code_for("nieznany rodzaj")
		self.assertEqual(UMOWA_CODES, przed)


if __name__ == "__main__":
	unittest.main()
