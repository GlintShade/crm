import unittest

from crm.volteo_grupy_filtrow import (
	KLUCZ_GRUP,
	MAX_GRUP,
	MAX_WARUNKOW_W_GRUPIE,
	klucze_z_grup,
	waliduj_grupy,
	wydziel_grupy,
)


class TestWydzielGrupy(unittest.TestCase):
	def test_a_brak_klucza_daje_puste_grupy_i_filtry_bez_zmian(self: "TestWydzielGrupy") -> None:
		filtry = {"status": "Odłożony", "custom_cc": "@me"}
		filtry_bez_grup, grupy = wydziel_grupy(filtry)
		self.assertEqual(filtry_bez_grup, filtry)
		self.assertEqual(grupy, [])

	def test_b_nie_mutuje_oryginalnego_slownika(self: "TestWydzielGrupy") -> None:
		filtry = {"status": "Odłożony", KLUCZ_GRUP: [{"a": 1}]}
		kopia = dict(filtry)
		wydziel_grupy(filtry)
		self.assertEqual(filtry, kopia)

	def test_c_wydziela_grupy_i_usuwa_klucz_z_reszty(self: "TestWydzielGrupy") -> None:
		filtry = {
			"custom_cc": "@me",
			KLUCZ_GRUP: [
				{"status": "Odłożony", "custom_kolejny_kontakt": ["<=", "@dzis"]},
				{"status": ["in", ["Nowy", "Próba kontaktu"]]},
			],
		}
		filtry_bez_grup, grupy = wydziel_grupy(filtry)
		self.assertEqual(filtry_bez_grup, {"custom_cc": "@me"})
		self.assertNotIn(KLUCZ_GRUP, filtry_bez_grup)
		self.assertEqual(len(grupy), 2)
		self.assertEqual(grupy[0]["status"], "Odłożony")

	def test_d_pusta_lista_grup_w_kluczu(self: "TestWydzielGrupy") -> None:
		filtry = {"status": "Lead", KLUCZ_GRUP: []}
		filtry_bez_grup, grupy = wydziel_grupy(filtry)
		self.assertEqual(filtry_bez_grup, {"status": "Lead"})
		self.assertEqual(grupy, [])

	def test_e_klucz_z_wartoscia_none(self: "TestWydzielGrupy") -> None:
		filtry = {"status": "Lead", KLUCZ_GRUP: None}
		filtry_bez_grup, grupy = wydziel_grupy(filtry)
		self.assertEqual(filtry_bez_grup, {"status": "Lead"})
		self.assertEqual(grupy, [])

	def test_f_puste_lub_zle_wejscie(self: "TestWydzielGrupy") -> None:
		self.assertEqual(wydziel_grupy(None), ({}, []))
		self.assertEqual(wydziel_grupy({}), ({}, []))
		self.assertEqual(wydziel_grupy([]), ({}, []))


class TestWaliduGrupy(unittest.TestCase):
	def test_a_brak_grup_nie_rzuca(self: "TestWaliduGrupy") -> None:
		waliduj_grupy(None)
		waliduj_grupy([])

	def test_b_poprawne_grupy_nie_rzucaja(self: "TestWaliduGrupy") -> None:
		waliduj_grupy(
			[
				{"status": "Odłożony", "custom_kolejny_kontakt": ["<=", "@dzis"]},
				{"status": ["in", ["Nowy", "Próba kontaktu"]]},
			]
		)

	def test_c_nie_lista_rzuca(self: "TestWaliduGrupy") -> None:
		with self.assertRaises(ValueError):
			waliduj_grupy({"status": "Lead"})
		with self.assertRaises(ValueError):
			waliduj_grupy("Lead")

	def test_d_za_duzo_grup_rzuca(self: "TestWaliduGrupy") -> None:
		waliduj_grupy([{"status": "Lead"}] * MAX_GRUP)
		with self.assertRaises(ValueError):
			waliduj_grupy([{"status": "Lead"}] * (MAX_GRUP + 1))

	def test_e_element_nie_slownik_rzuca(self: "TestWaliduGrupy") -> None:
		with self.assertRaises(ValueError):
			waliduj_grupy([{"status": "Lead"}, ["status", "=", "Lead"]])
		with self.assertRaises(ValueError):
			waliduj_grupy(["nie slownik"])

	def test_f_zagniezdzenie_rzuca(self: "TestWaliduGrupy") -> None:
		with self.assertRaises(ValueError):
			waliduj_grupy([{"status": "Lead", KLUCZ_GRUP: [{"status": "Won"}]}])

	def test_g_za_duzo_warunkow_w_grupie_rzuca(self: "TestWaliduGrupy") -> None:
		grupa_maks = {f"pole_{i}": i for i in range(MAX_WARUNKOW_W_GRUPIE)}
		waliduj_grupy([grupa_maks])
		grupa_za_duzo = {f"pole_{i}": i for i in range(MAX_WARUNKOW_W_GRUPIE + 1)}
		with self.assertRaises(ValueError):
			waliduj_grupy([grupa_za_duzo])

	def test_h_komunikaty_sa_stringami(self: "TestWaliduGrupy") -> None:
		try:
			waliduj_grupy([{"status": "Lead"}] * (MAX_GRUP + 1))
		except ValueError as e:
			self.assertIsInstance(str(e), str)
			self.assertGreater(len(str(e)), 0)
		else:
			self.fail("ValueError nie zostal rzucony")


class TestKluczeZGrup(unittest.TestCase):
	def test_a_puste_wejscie(self: "TestKluczeZGrup") -> None:
		self.assertEqual(klucze_z_grup(None), [])
		self.assertEqual(klucze_z_grup([]), [])

	def test_b_zbiera_unikalne_klucze_z_zachowaniem_kolejnosci(self: "TestKluczeZGrup") -> None:
		grupy = [
			{"status": "Odłożony", "custom_kolejny_kontakt": ["<=", "@dzis"]},
			{"status": ["in", ["Nowy", "Próba kontaktu"]], "custom_cc": "@me"},
		]
		self.assertEqual(klucze_z_grup(grupy), ["status", "custom_kolejny_kontakt", "custom_cc"])

	def test_c_pomija_elementy_niebedace_mapowaniem(self: "TestKluczeZGrup") -> None:
		grupy = [{"status": "Lead"}, "nie slownik", ["a", "b"]]
		self.assertEqual(klucze_z_grup(grupy), ["status"])


if __name__ == "__main__":
	unittest.main()
