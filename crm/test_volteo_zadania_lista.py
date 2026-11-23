import unittest

from crm.volteo_zadania_lista import (
	KLUCZ_DW,
	KLUCZ_KLIENTA,
	KLUCZ_ROLA_JA,
	filtr_dw,
	klient_zadania,
	nazwy_powiazan,
	polacz_filtr_name,
	tekst_filtra_klienta,
	uklad_paska_z_klientem,
	zawez_nazwy_zadan,
)


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


class TestTekstFiltraKlienta(unittest.TestCase):
	def test_a_like_z_procentami(self: "TestTekstFiltraKlienta") -> None:
		self.assertEqual(tekst_filtra_klienta(["LIKE", "%Kowalski%"]), "Kowalski")

	def test_b_male_litery_i_krotka(self: "TestTekstFiltraKlienta") -> None:
		self.assertEqual(tekst_filtra_klienta(["like", "%Jan Kowalski%"]), "Jan Kowalski")
		self.assertEqual(tekst_filtra_klienta(("Like", "%x%")), "x")

	def test_c_zwykly_string(self: "TestTekstFiltraKlienta") -> None:
		self.assertEqual(tekst_filtra_klienta("  Nowak "), "Nowak")
		self.assertEqual(tekst_filtra_klienta("%Nowak%"), "Nowak")

	def test_d_pusty_tekst_daje_none(self: "TestTekstFiltraKlienta") -> None:
		self.assertIsNone(tekst_filtra_klienta(""))
		self.assertIsNone(tekst_filtra_klienta("  "))
		self.assertIsNone(tekst_filtra_klienta(["LIKE", "%%"]))
		self.assertIsNone(tekst_filtra_klienta(["LIKE", "% %"]))

	def test_e_nieobslugiwany_ksztalt_daje_none(self: "TestTekstFiltraKlienta") -> None:
		self.assertIsNone(tekst_filtra_klienta(None))
		self.assertIsNone(tekst_filtra_klienta(5))
		self.assertIsNone(tekst_filtra_klienta(["=", "Kowalski"]))
		self.assertIsNone(tekst_filtra_klienta(["in", ["a"]]))
		self.assertIsNone(tekst_filtra_klienta(["LIKE"]))
		self.assertIsNone(tekst_filtra_klienta(["LIKE", "a", "b"]))
		self.assertIsNone(tekst_filtra_klienta(["LIKE", 5]))
		self.assertIsNone(tekst_filtra_klienta([1, "x"]))
		self.assertIsNone(tekst_filtra_klienta({"a": 1}))


class TestZawezNazwyZadan(unittest.TestCase):
	def test_a_przeciecie_liczby_z_tekstami(self: "TestZawezNazwyZadan") -> None:
		self.assertEqual(zawez_nazwy_zadan([1, 2, 3], "in", {"2", "3", "9"}), [2, 3])

	def test_b_przeciecie_liczby_z_liczbami(self: "TestZawezNazwyZadan") -> None:
		self.assertEqual(zawez_nazwy_zadan([1, 2, 3], "in", {1}), [1])

	def test_c_roznica(self: "TestZawezNazwyZadan") -> None:
		self.assertEqual(zawez_nazwy_zadan([1, 2, 3], "not in", {"2"}), [1, 3])

	def test_d_pusty_wynik_i_kolejnosc(self: "TestZawezNazwyZadan") -> None:
		self.assertEqual(zawez_nazwy_zadan([3, 1], "in", {"7"}), [])
		self.assertEqual(zawez_nazwy_zadan([3, 1, 2], "in", {"1", "3"}), [3, 1])

	def test_e_nie_mutuje_wejscia(self: "TestZawezNazwyZadan") -> None:
		nazwy = [1, 2]
		zawez_nazwy_zadan(nazwy, "in", {"1"})
		self.assertEqual(nazwy, [1, 2])


class TestUkladPaskaZKlientem(unittest.TestCase):
	def test_a_wstawia_po_title(self: "TestUkladPaskaZKlientem") -> None:
		uklad = ["title", "priority", "assigned_to", "status", "due_date"]
		self.assertEqual(
			uklad_paska_z_klientem(uklad, "CRM Task"),
			["title", "_klient", "priority", "assigned_to", "status", "due_date"],
		)

	def test_b_uklad_z_klientem_bez_zmian(self: "TestUkladPaskaZKlientem") -> None:
		uklad = ["_klient", "title", "status"]
		wynik = uklad_paska_z_klientem(uklad, "CRM Task")
		self.assertEqual(wynik, uklad)
		self.assertIsNot(wynik, uklad)

	def test_c_inny_doctype_bez_zmian(self: "TestUkladPaskaZKlientem") -> None:
		self.assertEqual(uklad_paska_z_klientem(["title", "status"], "CRM Lead"), ["title", "status"])

	def test_d_brak_title_daje_poczatek(self: "TestUkladPaskaZKlientem") -> None:
		self.assertEqual(uklad_paska_z_klientem(["status"], "CRM Task"), ["_klient", "status"])

	def test_e_pusty_uklad_i_brak_mutacji(self: "TestUkladPaskaZKlientem") -> None:
		self.assertEqual(uklad_paska_z_klientem([], "CRM Task"), ["_klient"])
		uklad = ["title"]
		uklad_paska_z_klientem(uklad, "CRM Task")
		self.assertEqual(uklad, ["title"])


class TestDoWiadomosciFiltr(unittest.TestCase):
	def test_klucze(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual((KLUCZ_DW, KLUCZ_ROLA_JA), ("_dw", "_rola_ja"))

	def test_filtr_dw_ksztalty(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(filtr_dw("a@x"), ("in", ["a@x"]))
		self.assertEqual(filtr_dw(["=", "a@x"]), ("in", ["a@x"]))
		self.assertEqual(filtr_dw(["!=", "a@x"]), ("not in", ["a@x"]))
		self.assertEqual(filtr_dw(["IN", ["a@x", " b@x ", ""]]), ("in", ["a@x", "b@x"]))
		self.assertEqual(filtr_dw(["not in", ["a@x"]]), ("not in", ["a@x"]))

	def test_filtr_dw_nieobslugiwane(self: "TestDoWiadomosciFiltr") -> None:
		for wartosc in (None, "", [], ["in", []], ["like", "%a%"], ["in", "a@x"], {"a": 1}, 5, ["in", [1, None]]):
			self.assertIsNone(filtr_dw(wartosc), wartosc)

	def test_polacz_bez_istniejacego(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(polacz_filtr_name(None, "in", [3, 4]), ("in", [3, 4]))
		self.assertEqual(polacz_filtr_name(None, "not in", [3]), ("not in", [3]))

	def test_polacz_in_in(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(polacz_filtr_name(("in", {"3", 5}), "in", [3, 4]), ("in", [3]))

	def test_polacz_in_notin(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(polacz_filtr_name(("in", {3, 5}), "not in", ["3"]), ("in", [5]))

	def test_polacz_notin_in(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(polacz_filtr_name(("not in", {3}), "in", [3, 4]), ("in", [4]))

	def test_polacz_notin_notin(self: "TestDoWiadomosciFiltr") -> None:
		self.assertEqual(polacz_filtr_name(("not in", {3}), "not in", [3, 4]), ("not in", [3, 4]))

	def test_polacz_nie_mutuje(self: "TestDoWiadomosciFiltr") -> None:
		nazwy, zbior = [3, 4], {3}
		polacz_filtr_name(("in", zbior), "in", nazwy)
		self.assertEqual((nazwy, zbior), ([3, 4], {3}))


if __name__ == "__main__":
	unittest.main()
