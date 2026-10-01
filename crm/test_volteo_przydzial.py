import unittest

from crm.volteo_przydzial import normalizuj_wartosci_geo


class TestNormalizujWartosciGeo(unittest.TestCase):
	def test_a_puste_wejscie_daje_puste_liste(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(normalizuj_wartosci_geo(None), [])
		self.assertEqual(normalizuj_wartosci_geo(""), [])
		self.assertEqual(normalizuj_wartosci_geo([]), [])
		self.assertEqual(normalizuj_wartosci_geo(()), [])

	def test_b_pojedynczy_string_zgodnosc_wsteczna(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(normalizuj_wartosci_geo("mazowieckie"), ["mazowieckie"])

	def test_c_pojedynczy_string_jest_przycinany(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(normalizuj_wartosci_geo("  mazowieckie  "), ["mazowieckie"])

	def test_d_string_samych_spacji_daje_puste(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(normalizuj_wartosci_geo("   "), [])

	def test_e_lista_wielu_wartosci(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(
			normalizuj_wartosci_geo(["mazowieckie", "slaskie"]),
			["mazowieckie", "slaskie"],
		)

	def test_f_krotka_dziala_tak_samo_jak_lista(self: "TestNormalizujWartosciGeo") -> None:
		self.assertEqual(
			normalizuj_wartosci_geo(("mazowieckie", "slaskie")),
			["mazowieckie", "slaskie"],
		)

	def test_g_duplikaty_usuniete_zachowana_kolejnosc_pierwszego(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(
			normalizuj_wartosci_geo(["slaskie", "mazowieckie", "slaskie", "mazowieckie"]),
			["slaskie", "mazowieckie"],
		)

	def test_h_elementy_przycinane_przed_porownaniem_duplikatow(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(
			normalizuj_wartosci_geo(["mazowieckie", " mazowieckie ", "mazowieckie\t"]),
			["mazowieckie"],
		)

	def test_i_puste_i_biale_elementy_listy_pomijane(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(
			normalizuj_wartosci_geo(["mazowieckie", "", "   ", "slaskie"]),
			["mazowieckie", "slaskie"],
		)

	def test_j_nieserializowalny_element_rzuca_value_error(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		with self.assertRaises(ValueError):
			normalizuj_wartosci_geo(["mazowieckie", 42])

	def test_k_nieobslugiwany_typ_wejscia_rzuca_value_error(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		with self.assertRaises(ValueError):
			normalizuj_wartosci_geo({"wojewodztwo": "mazowieckie"})
		with self.assertRaises(ValueError):
			normalizuj_wartosci_geo(42)

	def test_l_nie_mutuje_argumentu_listy(self: "TestNormalizujWartosciGeo") -> None:
		wejscie = ["mazowieckie", "slaskie"]
		kopia = list(wejscie)
		normalizuj_wartosci_geo(wejscie)
		self.assertEqual(wejscie, kopia)

	def test_m_json_string_listy_jest_dekodowany(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(
			normalizuj_wartosci_geo('["mazowieckie", "slaskie"]'),
			["mazowieckie", "slaskie"],
		)

	def test_n_json_string_listy_z_bialymi_znakami_wokol(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(
			normalizuj_wartosci_geo('  ["mazowieckie", "slaskie"]  '),
			["mazowieckie", "slaskie"],
		)

	def test_o_json_string_pustej_listy_daje_puste(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		self.assertEqual(normalizuj_wartosci_geo("[]"), [])

	def test_p_niepoprawny_json_rzuca_value_error(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		with self.assertRaises(ValueError):
			normalizuj_wartosci_geo("[abc")

	def test_q_json_string_z_nie_stringiem_w_srodku_rzuca_value_error(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		with self.assertRaises(ValueError):
			normalizuj_wartosci_geo('["mazowieckie", 42]')

	def test_r_goly_string_bez_nawiasu_nie_jest_traktowany_jako_json(
		self: "TestNormalizujWartosciGeo",
	) -> None:
		# Pułapka naprawiona w QA (2026-10-01): frappe.parse_json na gołym
		# stringu RZUCA JSONDecodeError (to zwykłe json.loads na każdym
		# stringu, nie tylko na kształcie JSON) -- ta funkcja nie używa
		# frappe.parse_json w ogóle i rozpoznaje JSON wyłącznie po "["
		# na początku, więc zwykła nazwa województwa/powiatu (zgodność
		# wsteczna) nigdy nie trafia do json.loads i nigdy nie rzuca.
		self.assertEqual(normalizuj_wartosci_geo("mazowieckie"), ["mazowieckie"])
		self.assertEqual(normalizuj_wartosci_geo("powiat warszawski zachodni"), [
			"powiat warszawski zachodni",
		])


if __name__ == "__main__":
	unittest.main()
