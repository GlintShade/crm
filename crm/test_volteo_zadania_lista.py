import unittest

from crm.volteo_zadania_lista import KLUCZ_KLIENTA, klient_zadania, nazwy_powiazan


class TestKlientZadania(unittest.TestCase):
	def test_a_klucz_pseudopola(self: "TestKlientZadania") -> None:
		self.assertEqual(KLUCZ_KLIENTA, "_klient")

	def test_b_szansa_z_nazwa(self: "TestKlientZadania") -> None:
		self.assertEqual(
			klient_zadania("CRM Deal", "PRO/PV/26/0001", {"PRO/PV/26/0001": "Jan Kowalski"}, {}),
			"Jan Kowalski",
		)

	def test_c_lead_z_nazwa(self: "TestKlientZadania") -> None:
		self.assertEqual(
			klient_zadania("CRM Lead", "CRM-LEAD-1", {}, {"CRM-LEAD-1": "Anna Nowak"}),
			"Anna Nowak",
		)

	def test_d_brak_powiazania(self: "TestKlientZadania") -> None:
		self.assertEqual(klient_zadania(None, None, {"x": "A"}, {"x": "B"}), "")
		self.assertEqual(klient_zadania("", "", {"x": "A"}, {"x": "B"}), "")
		self.assertEqual(klient_zadania("CRM Deal", None, {"x": "A"}, {}), "")

	def test_e_powiazanie_spoza_map(self: "TestKlientZadania") -> None:
		self.assertEqual(klient_zadania("CRM Deal", "PRO/1", {"PRO/2": "A"}, {}), "")
		self.assertEqual(klient_zadania("CRM Lead", "L-1", {}, {"L-2": "B"}), "")

	def test_f_nieznany_doctype(self: "TestKlientZadania") -> None:
		self.assertEqual(klient_zadania("Contact", "X", {"X": "A"}, {"X": "B"}), "")

	def test_g_pusta_nazwa_w_mapie(self: "TestKlientZadania") -> None:
		self.assertEqual(klient_zadania("CRM Deal", "PRO/1", {"PRO/1": ""}, {}), "")
		self.assertEqual(klient_zadania("CRM Deal", "PRO/1", {"PRO/1": None}, {}), "")
		self.assertEqual(klient_zadania("CRM Lead", "L-1", {}, {"L-1": "   "}), "")

	def test_h_szansa_nie_czyta_mapy_leadow(self: "TestKlientZadania") -> None:
		self.assertEqual(klient_zadania("CRM Deal", "X", {}, {"X": "Lead"}), "")


class TestNazwyPowiazan(unittest.TestCase):
	def test_a_rozdziela_szanse_i_leady(self: "TestNazwyPowiazan") -> None:
		wiersze = [
			{"reference_doctype": "CRM Deal", "reference_docname": "D1"},
			{"reference_doctype": "CRM Lead", "reference_docname": "L1"},
			{"reference_doctype": "CRM Deal", "reference_docname": "D2"},
		]
		self.assertEqual(nazwy_powiazan(wiersze), (["D1", "D2"], ["L1"]))

	def test_b_bez_duplikatow_w_kolejnosci_pierwszego_wystapienia(self: "TestNazwyPowiazan") -> None:
		wiersze = [
			{"reference_doctype": "CRM Deal", "reference_docname": "D2"},
			{"reference_doctype": "CRM Deal", "reference_docname": "D1"},
			{"reference_doctype": "CRM Deal", "reference_docname": "D2"},
			{"reference_doctype": "CRM Lead", "reference_docname": "L1"},
			{"reference_doctype": "CRM Lead", "reference_docname": "L1"},
		]
		self.assertEqual(nazwy_powiazan(wiersze), (["D2", "D1"], ["L1"]))

	def test_c_bez_pustych_i_obcych_doctype(self: "TestNazwyPowiazan") -> None:
		wiersze = [
			{"reference_doctype": "CRM Deal", "reference_docname": ""},
			{"reference_doctype": "CRM Deal", "reference_docname": None},
			{"reference_doctype": None, "reference_docname": "X"},
			{"reference_doctype": "Contact", "reference_docname": "C1"},
			{},
		]
		self.assertEqual(nazwy_powiazan(wiersze), ([], []))

	def test_d_pusta_lista(self: "TestNazwyPowiazan") -> None:
		self.assertEqual(nazwy_powiazan([]), ([], []))

	def test_e_nie_mutuje_wejscia(self: "TestNazwyPowiazan") -> None:
		wiersze = [{"reference_doctype": "CRM Deal", "reference_docname": "D1"}]
		kopia = [dict(w) for w in wiersze]
		nazwy_powiazan(wiersze)
		self.assertEqual(wiersze, kopia)


if __name__ == "__main__":
	unittest.main()
