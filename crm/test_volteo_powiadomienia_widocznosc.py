import unittest

from crm.volteo_powiadomienia_widocznosc import (
	PTYPY_ODCZYTU,
	czy_adresat,
	czy_widzi_wszystkie,
	decyzja_dokumentu,
)

A = "a@x.pl"
B = "b@x.pl"


class TestCzyWidziWszystkie(unittest.TestCase):
	def test_administrator(self: "TestCzyWidziWszystkie") -> None:
		self.assertTrue(czy_widzi_wszystkie("Administrator", []))

	def test_system_manager(self: "TestCzyWidziWszystkie") -> None:
		self.assertTrue(czy_widzi_wszystkie(A, ["Sales User", "System Manager"]))

	def test_backoffice_nie_jest_wyjatkiem(self: "TestCzyWidziWszystkie") -> None:
		self.assertFalse(czy_widzi_wszystkie(A, ["Volteo Backend", "Volteo Core Admin"]))

	def test_brak_roli(self: "TestCzyWidziWszystkie") -> None:
		self.assertFalse(czy_widzi_wszystkie(A, None))


class TestCzyAdresat(unittest.TestCase):
	def test_ten_sam(self: "TestCzyAdresat") -> None:
		self.assertTrue(czy_adresat(A, A))

	def test_inny(self: "TestCzyAdresat") -> None:
		self.assertFalse(czy_adresat(A, B))

	def test_puste_to_user(self: "TestCzyAdresat") -> None:
		self.assertFalse(czy_adresat(A, None))
		self.assertFalse(czy_adresat(A, ""))


class TestDecyzjaDokumentu(unittest.TestCase):
	def test_adresat_bez_opinii(self: "TestDecyzjaDokumentu") -> None:
		self.assertIsNone(decyzja_dokumentu(A, ["Sales User"], "read", "N1", A))

	def test_nie_adresat_odmowa(self: "TestDecyzjaDokumentu") -> None:
		for ptype in sorted(PTYPY_ODCZYTU):
			self.assertIs(decyzja_dokumentu(A, ["Sales User"], ptype, "N1", B), False)

	def test_ptypy_odczytu_dla_adresata_i_wyjatkow(self: "TestDecyzjaDokumentu") -> None:
		for ptype in sorted(PTYPY_ODCZYTU):
			self.assertIsNone(decyzja_dokumentu(A, ["Sales User"], ptype, "N1", A))
			self.assertIsNone(decyzja_dokumentu(A, ["System Manager"], ptype, "N1", B))
			self.assertIsNone(decyzja_dokumentu("Administrator", [], ptype, "N1", B))

	def test_zapis_i_usuwanie_bez_opinii(self: "TestDecyzjaDokumentu") -> None:
		for ptype in ("write", "delete", "create", "submit"):
			self.assertIsNone(decyzja_dokumentu(A, ["Sales User"], ptype, "N1", B))

	def test_niezapisany_dokument_bez_opinii(self: "TestDecyzjaDokumentu") -> None:
		self.assertIsNone(decyzja_dokumentu(A, ["Sales User"], "read", None, B))
		self.assertIsNone(decyzja_dokumentu(A, ["Sales User"], "read", "", B))

	def test_system_manager_bez_opinii(self: "TestDecyzjaDokumentu") -> None:
		self.assertIsNone(decyzja_dokumentu(A, ["System Manager"], "read", "N1", B))

	def test_administrator_bez_opinii(self: "TestDecyzjaDokumentu") -> None:
		self.assertIsNone(decyzja_dokumentu("Administrator", [], "read", "N1", B))

	def test_backoffice_odmowa(self: "TestDecyzjaDokumentu") -> None:
		self.assertIs(decyzja_dokumentu(A, ["Volteo Backend"], "read", "N1", B), False)

	def test_brak_to_user_odmowa(self: "TestDecyzjaDokumentu") -> None:
		self.assertIs(decyzja_dokumentu(A, ["Sales User"], "read", "N1", None), False)

	def test_nigdy_true(self: "TestDecyzjaDokumentu") -> None:
		for user in (A, "Administrator"):
			for role in ([], ["Sales User"], ["System Manager"], ["Volteo Backend"]):
				for ptype in ("read", "write", "create", "delete", "share"):
					for nazwa in (None, "N1"):
						for to_user in (None, A, B):
							self.assertIsNot(decyzja_dokumentu(user, role, ptype, nazwa, to_user), True)


if __name__ == "__main__":
	unittest.main()
