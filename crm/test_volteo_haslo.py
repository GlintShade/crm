import ast
import unittest
from pathlib import Path

from crm.volteo_haslo import KONTA_TECHNICZNE, czy_konto_osobiste, czy_wymusic_haslo

USER = "handlowiec@example.com"

# Stan bazowy: osobiste konto bez hasła, NDA podpisane, nic nie zwalnia.
BAZA = dict(
	user=USER,
	ma_haslo=False,
	wymaga_nda=False,
	logowanie_haslem_wylaczone=False,
	ldap_wlaczone=False,
	ma_sso=False,
)


def decyzja(**zmiany) -> bool:
	return czy_wymusic_haslo(**{**BAZA, **zmiany})


class TestVolteoHaslo(unittest.TestCase):
	def test_a_konto_bez_hasla_po_nda_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertTrue(decyzja())

	def test_b_pusty_user_nie_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(user=None))
		self.assertFalse(decyzja(user=""))

	def test_c_gosc_i_administrator_nie_wymuszaja(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(user="Guest"))
		self.assertFalse(decyzja(user="Administrator"))

	def test_d_konto_z_haslem_nie_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(ma_haslo=True))

	def test_e_niepodpisane_nda_nie_wymusza(self: "TestVolteoHaslo") -> None:
		# Wariant B: najpierw NDA, dopiero potem hasło.
		self.assertFalse(decyzja(wymaga_nda=True))

	def test_f_wylaczone_logowanie_haslem_nie_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(logowanie_haslem_wylaczone=True))

	def test_g_ldap_nie_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(ldap_wlaczone=True))

	def test_h_sso_nie_wymusza(self: "TestVolteoHaslo") -> None:
		self.assertFalse(decyzja(ma_sso=True))

	def test_i_flaga_boot_ignoruje_nda(self: "TestVolteoHaslo") -> None:
		# `volteo_wymaga_hasla` w boot liczy ten sam predykat z wymaga_nda=False:
		# konto bez hasła, które dopiero podpisze NDA, dostaje True.
		self.assertTrue(decyzja(wymaga_nda=False))
		self.assertFalse(decyzja(wymaga_nda=False, ma_haslo=True))

	def test_j_konto_osobiste(self: "TestVolteoHaslo") -> None:
		self.assertTrue(czy_konto_osobiste(USER))
		self.assertFalse(czy_konto_osobiste(None))
		self.assertFalse(czy_konto_osobiste(""))
		for konto in KONTA_TECHNICZNE:
			self.assertFalse(czy_konto_osobiste(konto))

	def test_k_modul_nie_importuje_frappe(self: "TestVolteoHaslo") -> None:
		zrodlo = Path(__file__).with_name("volteo_haslo.py").read_text(encoding="utf-8")
		for wezel in ast.walk(ast.parse(zrodlo)):
			if isinstance(wezel, ast.Import):
				nazwy = [alias.name for alias in wezel.names]
			elif isinstance(wezel, ast.ImportFrom):
				nazwy = [wezel.module or ""]
			else:
				continue
			for nazwa in nazwy:
				self.assertNotEqual(nazwa.split(".")[0], "frappe")


if __name__ == "__main__":
	unittest.main()
