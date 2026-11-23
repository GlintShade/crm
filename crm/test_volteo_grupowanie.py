import unittest

from crm.volteo_grupowanie import (
	LIMIT_LEADOW,
	czy_ponad_limit,
	etykieta_pustej,
	filtr_grupy,
	klucz_wartosci,
	lista_pol,
	pole,
	uloz_grupy,
	zlicz,
)


class TestAllowlista(unittest.TestCase):
	def test_pola_per_doctype(self: "TestAllowlista") -> None:
		self.assertEqual(len(lista_pol("CRM Deal")), 9)
		self.assertEqual(len(lista_pol("CRM Lead")), 15)
		self.assertEqual(len(lista_pol("CRM Task")), 6)
		self.assertEqual(lista_pol("CRM Contact"), [])

	def test_pole_spoza_listy(self: "TestAllowlista") -> None:
		self.assertIsNone(pole("CRM Deal", "custom_cena_netto"))
		self.assertIsNone(pole("CRM Task", "_klient"))
		self.assertIsNone(pole("CRM Deal", None))
		self.assertEqual(pole("CRM Deal", "status")["kind"], "status")

	def test_limit_tylko_leady(self: "TestAllowlista") -> None:
		self.assertEqual(LIMIT_LEADOW, 2000)
		self.assertFalse(czy_ponad_limit("CRM Lead", 2000))
		self.assertTrue(czy_ponad_limit("CRM Lead", 2001))
		self.assertFalse(czy_ponad_limit("CRM Deal", 50000))
		self.assertFalse(czy_ponad_limit("CRM Task", 50000))


class TestLiczniki(unittest.TestCase):
	def test_klucze(self: "TestLiczniki") -> None:
		self.assertEqual(klucz_wartosci("data", None), "")
		self.assertEqual(klucz_wartosci("data", ""), "")
		self.assertEqual(klucz_wartosci("dzien", "2026-11-23 10:30:00"), "2026-11-23")
		self.assertEqual(klucz_wartosci("miesiac", "2026-11-23 10:30:00.123"), "2026-11")
		self.assertEqual(klucz_wartosci("select", "A"), "A")

	def test_zlicz_skleja_znaczniki_czasu_i_puste(self: "TestLiczniki") -> None:
		wiersze = [
			{"wartosc": "2026-11-23 09:00:00", "n": 2},
			{"wartosc": "2026-11-23 15:00:00", "n": 3},
			{"wartosc": None, "n": 4},
			{"wartosc": "", "n": 1},
		]
		self.assertEqual(zlicz("dzien", wiersze), {"2026-11-23": 5, "": 5})
		self.assertEqual(sum(zlicz("dzien", wiersze).values()), 10)


class TestUlozGrupy(unittest.TestCase):
	def test_etapy_w_kolejnosci_procesu(self: "TestUlozGrupy") -> None:
		liczniki = {
			"Przegrana": 2,
			"Montaż": 1,
			"Lead": 5,
			"Dokumentacja": 3,
			"Stary etap": 1,
			"Umowa Podpisana": 4,
			"": 7,
		}
		grupy = uloz_grupy("CRM Deal", "status", liczniki)
		self.assertEqual(
			[g["klucz"] for g in grupy],
			["Lead", "Umowa Podpisana", "Montaż", "Dokumentacja", "Stary etap", "Przegrana", ""],
		)
		self.assertTrue(grupy[-1]["pusta"])
		self.assertEqual(grupy[-1]["etykieta"], "Brak wartości")

	def test_alfabetycznie_i_pusta_ostatnia(self: "TestUlozGrupy") -> None:
		grupy = uloz_grupy("CRM Lead", "custom_powiat", {"żywiecki": 1, "": 3, "Bielski": 2, "arkadia": 1})
		self.assertEqual([g["klucz"] for g in grupy], ["arkadia", "Bielski", "żywiecki", ""])

	def test_czytelna_nazwa_pustej(self: "TestUlozGrupy") -> None:
		self.assertEqual(uloz_grupy("CRM Lead", "lead_owner", {"": 2})[0]["etykieta"], "Bez handlowca")
		self.assertEqual(
			uloz_grupy("CRM Task", "assigned_to", {"": 2})[0]["etykieta"], "Bez osoby odpowiedzialnej"
		)
		self.assertEqual(etykieta_pustej("CRM Lead", "custom_powiat"), "Brak wartości")

	def test_puste_grupy_ukryte_i_pokazane(self: "TestUlozGrupy") -> None:
		opcje = ["Backlog", "Todo", "In Progress", "Done"]
		bez = uloz_grupy("CRM Task", "status", {"Todo": 2}, opcje=opcje)
		self.assertEqual([g["klucz"] for g in bez], ["Todo"])
		z = uloz_grupy("CRM Task", "status", {"Todo": 2, "Done": 0}, opcje=opcje, pokaz_puste=True)
		self.assertEqual(
			[(g["klucz"], g["licznik"]) for g in z],
			[("Backlog", 0), ("Todo", 2), ("In Progress", 0), ("Done", 0)],
		)

	def test_puste_nie_dodaje_grupy_pustej_wartosci_bez_rekordow(self: "TestUlozGrupy") -> None:
		z = uloz_grupy("CRM Task", "status", {"Todo": 2}, opcje=["Todo"], pokaz_puste=True)
		self.assertNotIn("", [g["klucz"] for g in z])

	def test_daty_chronologicznie(self: "TestUlozGrupy") -> None:
		grupy = uloz_grupy("CRM Deal", "creation", {"2026-11": 1, "2026-02": 4, "2025-12": 2})
		self.assertEqual([g["klucz"] for g in grupy], ["2025-12", "2026-02", "2026-11"])

	def test_etykiety_uzytkownikow(self: "TestUlozGrupy") -> None:
		grupy = uloz_grupy(
			"CRM Lead",
			"lead_owner",
			{"b@x.pl": 1, "a@x.pl": 1},
			etykiety={"b@x.pl": "Adam Nowak", "a@x.pl": "Zofia Lis"},
		)
		self.assertEqual([g["etykieta"] for g in grupy], ["Adam Nowak", "Zofia Lis"])

	def test_pole_spoza_allowlisty(self: "TestUlozGrupy") -> None:
		with self.assertRaises(ValueError):
			uloz_grupy("CRM Deal", "custom_cena_netto", {"1": 1})


class TestFiltrGrupy(unittest.TestCase):
	def test_rownosc(self: "TestFiltrGrupy") -> None:
		self.assertEqual(filtr_grupy("CRM Deal", "status", "Lead"), ["status", "=", "Lead"])

	def test_pusta(self: "TestFiltrGrupy") -> None:
		self.assertEqual(filtr_grupy("CRM Lead", "lead_owner", ""), ["lead_owner", "is", "not set"])

	def test_dzien(self: "TestFiltrGrupy") -> None:
		self.assertEqual(
			filtr_grupy("CRM Lead", "custom_termin_spotkania", "2026-11-23"),
			["custom_termin_spotkania", "between", ["2026-11-23", "2026-11-23"]],
		)

	def test_miesiac_w_tym_luty_przestepny(self: "TestFiltrGrupy") -> None:
		self.assertEqual(
			filtr_grupy("CRM Deal", "creation", "2024-02"),
			["creation", "between", ["2024-02-01", "2024-02-29"]],
		)
		self.assertEqual(
			filtr_grupy("CRM Deal", "creation", "2026-11"),
			["creation", "between", ["2026-11-01", "2026-11-30"]],
		)

	def test_odrzuca_zle_dane(self: "TestFiltrGrupy") -> None:
		for args in (
			("CRM Deal", "custom_cena_netto", "1"),
			("CRM Deal", "creation", "2026-13"),
			("CRM Deal", "creation", "2026-11-01"),
			("CRM Lead", "custom_kolejny_kontakt", "jutro"),
			("CRM Lead", "lead_owner", ["a"]),
		):
			with self.assertRaises(ValueError, msg=str(args)):
				filtr_grupy(*args)


if __name__ == "__main__":
	unittest.main()
