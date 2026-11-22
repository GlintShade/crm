# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_kategorie import (
	KATEGORIE,
	Teren,
	kategoria_leada,
	kategorie_leada,
	kategorie_leadow,
	moze_widziec,
	moze_zapisac,
	okreg_kampanii,
	sortuj_handlowcow,
	teren_z_wiersza,
	waliduj_teren,
)

GORZOW = (52.7368, 15.2288)
MIEDZYRZECZ = (52.4447, 15.5780)  # ok. 40 km od Gorzowa
ZIELONA = (51.9356, 15.5062)  # ok. 90 km od Gorzowa
PILA = (53.1510, 16.7383)


def teren(handlowiec, kategoria, srodek=None, promien=0, okreg=""):
	return Teren(
		handlowiec=handlowiec,
		nazwa_handlowca=handlowiec,
		kategoria=kategoria,
		lat=srodek[0] if srodek else None,
		lng=srodek[1] if srodek else None,
		promien_km=promien,
		okreg=okreg,
	)


class TestRole(unittest.TestCase):
	def test_widzenie(self):
		for rola in ("System Manager", "Volteo Core Admin", "Volteo Backend", "Volteo Call Center"):
			self.assertTrue(moze_widziec([rola]))
		self.assertFalse(moze_widziec(["Volteo D2D Sales"]))
		self.assertFalse(moze_widziec([]))

	def test_zapis(self):
		self.assertTrue(moze_zapisac(["Volteo Core Admin"]))
		self.assertTrue(moze_zapisac(["System Manager", "x"]))
		self.assertFalse(moze_zapisac(["Volteo Backend", "Volteo Call Center"]))


class TestOkregKampanii(unittest.TestCase):
	def test_formaty(self):
		self.assertEqual(okreg_kampanii("Wrocław 27.10"), "Wrocław")
		self.assertEqual(okreg_kampanii("GORZÓW"), "Gorzów")
		self.assertEqual(okreg_kampanii("Trójmiasto 3.11"), "Trójmiasto")
		self.assertEqual(okreg_kampanii("Szczecin, 27.10"), "Szczecin")
		self.assertEqual(okreg_kampanii("[S][KAMPANIA LEADOWA][WROCŁAW][27.10.2026]"), "Wrocław")

	def test_brak(self):
		self.assertEqual(okreg_kampanii("Kraków 3.11"), "")
		self.assertEqual(okreg_kampanii(""), "")
		self.assertEqual(okreg_kampanii(None), "")


class TestKategoriaLeada(unittest.TestCase):
	def test_w_promieniu(self):
		t = [teren("a", "Standard", GORZOW, 70)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "", t), ("Standard", "a"))

	def test_poza_promieniem(self):
		t = [teren("a", "Standard", GORZOW, 50)]
		self.assertIsNone(kategoria_leada(*ZIELONA, "", "", t))

	def test_wyzsza_kategoria_wygrywa(self):
		t = [teren("a", "Standard", GORZOW, 100), teren("b", "Priorytet", ZIELONA, 100)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "", t), ("Priorytet", "b"))
		t = [teren("a", "Nie umawiać", GORZOW, 100), teren("b", "Standard", ZIELONA, 100)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "", t), ("Standard", "b"))

	def test_remis_blizszy_srodek(self):
		t = [teren("daleki", "Priorytet", ZIELONA, 100), teren("bliski", "Priorytet", GORZOW, 100)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "", t), ("Priorytet", "bliski"))

	def test_wlasciciel_nie_umawiac(self):
		t = [teren("w", "Nie umawiać"), teren("p", "Priorytet", GORZOW, 100)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "w", t), ("Nie umawiać", "w"))

	def test_wlasciciel_inny_nie_zmienia(self):
		t = [teren("w", "Standard"), teren("p", "Priorytet", GORZOW, 100)]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "", "w", t), ("Priorytet", "p"))

	def test_lead_bez_wspolrzednych_z_kampania(self):
		t = [teren("a", "Priorytet", GORZOW, 50, okreg="Gorzów")]
		self.assertEqual(kategoria_leada(None, None, "GORZÓW", "", t), ("Priorytet", "a"))
		self.assertEqual(kategoria_leada(0, 0, "Gorzów 3.11", "", t), ("Priorytet", "a"))
		self.assertIsNone(kategoria_leada(None, None, "Wrocław 3.11", "", t))
		self.assertIsNone(kategoria_leada(None, None, "", "", t))

	def test_teren_bez_srodka_dziala_przez_okreg(self):
		t = [teren("a", "Standard", okreg="Szczecin")]
		self.assertEqual(kategoria_leada(*PILA, "Szczecin 3.11", "", t), ("Standard", "a"))
		self.assertIsNone(kategoria_leada(*PILA, "", "", t))

	def test_kampania_wygrywa_z_promieniem_wg_kategorii(self):
		t = [teren("a", "Standard", GORZOW, 100), teren("b", "Priorytet", okreg="Wrocław")]
		self.assertEqual(kategoria_leada(*MIEDZYRZECZ, "Wrocław 1.11", "", t), ("Priorytet", "b"))

	def test_brak_terenow(self):
		self.assertIsNone(kategoria_leada(*GORZOW, "Gorzów", "x", []))

	def test_nakladajace_sie_tereny_daja_obie_kategorie(self):
		t = [teren("a", "Standard", GORZOW, 100), teren("b", "Priorytet", GORZOW, 70)]
		self.assertEqual(
			kategorie_leada(*MIEDZYRZECZ, "", "", t), {"Priorytet": "b", "Standard": "a"}
		)
		self.assertEqual(list(kategorie_leada(*MIEDZYRZECZ, "", "", t)), ["Priorytet", "Standard"])

	def test_poza_mniejszym_terenem_zostaje_druga_kategoria(self):
		t = [teren("a", "Standard", GORZOW, 100), teren("b", "Priorytet", GORZOW, 30)]
		self.assertEqual(kategorie_leada(*MIEDZYRZECZ, "", "", t), {"Standard": "a"})

	def test_w_kategorii_wygrywa_blizszy_srodek(self):
		t = [teren("daleki", "Standard", ZIELONA, 100), teren("bliski", "Standard", GORZOW, 100)]
		self.assertEqual(kategorie_leada(*MIEDZYRZECZ, "", "", t), {"Standard": "bliski"})

	def test_nie_umawiac_wlasciciela_wyklucza_inne(self):
		t = [teren("w", "Nie umawiać", GORZOW, 70), teren("p", "Priorytet", GORZOW, 70)]
		self.assertEqual(kategorie_leada(*MIEDZYRZECZ, "", "w", t), {"Nie umawiać": "w"})


class TestKategorieLeadow(unittest.TestCase):
	def test_slownik(self):
		t = [teren("a", "Priorytet", GORZOW, 70)]
		leady = [
			{"name": "L1", "custom_lat": MIEDZYRZECZ[0], "custom_lng": MIEDZYRZECZ[1]},
			{"name": "L2", "custom_lat": ZIELONA[0], "custom_lng": ZIELONA[1]},
			{"name": "L3", "custom_kampania_fb": "x", "lead_owner": "a"},
		]
		self.assertEqual(kategorie_leadow(leady, t), {"L1": {"Priorytet": "a"}})


class TestTerenZWiersza(unittest.TestCase):
	def test_bez_kategorii(self):
		self.assertIsNone(teren_z_wiersza({"name": "a", "custom_kategoria_handlowca": ""}))
		self.assertIsNone(teren_z_wiersza({"name": "a"}))

	def test_zero_zero_to_brak_srodka(self):
		t = teren_z_wiersza(
			{
				"name": "a@x",
				"full_name": "A B",
				"custom_kategoria_handlowca": "Standard",
				"custom_teren_lat": 0,
				"custom_teren_lng": 0.0,
				"custom_teren_promien_km": 0,
				"custom_okreg_kampanii": "Gorzów",
			}
		)
		self.assertEqual((t.lat, t.lng, t.okreg, t.handlowiec), (None, None, "Gorzów", "a@x"))

	def test_pelny(self):
		t = teren_z_wiersza(
			{
				"name": "a@x",
				"custom_kategoria_handlowca": "Priorytet",
				"custom_teren_lat": "52.7368",
				"custom_teren_lng": 15.2288,
				"custom_teren_promien_km": 70,
			}
		)
		self.assertEqual((t.lat, t.lng, t.promien_km), (52.7368, 15.2288, 70))


class TestWaliduj(unittest.TestCase):
	def test_poprawne(self):
		self.assertEqual(
			waliduj_teren(
				{
					"kategoria": "Priorytet",
					"teren_lat": 52.7,
					"teren_lng": 15.2,
					"promien_km": 70,
					"okreg": "Gorzów",
				}
			),
			[],
		)
		self.assertEqual(waliduj_teren({}), [])
		self.assertEqual(waliduj_teren({"kategoria": "Standard", "okreg": "Szczecin"}), [])

	def test_kategoria(self):
		self.assertEqual(len(waliduj_teren({"kategoria": "Zły"})), 1)
		for k in KATEGORIE:
			self.assertEqual(waliduj_teren({"kategoria": k}), [])

	def test_okreg(self):
		self.assertEqual(len(waliduj_teren({"okreg": "Kraków"})), 1)

	def test_promien_przy_srodku(self):
		base = {"teren_lat": 52.7, "teren_lng": 15.2}
		self.assertEqual(len(waliduj_teren({**base, "promien_km": 0})), 1)
		self.assertEqual(len(waliduj_teren({**base, "promien_km": 301})), 1)
		self.assertEqual(len(waliduj_teren({**base, "promien_km": 300})), 0)
		self.assertEqual(len(waliduj_teren({**base, "promien_km": 1})), 0)

	def test_poza_polska(self):
		self.assertEqual(len(waliduj_teren({"teren_lat": 40, "teren_lng": 15.2, "promien_km": 10})), 1)

	def test_bez_srodka_promien_ignorowany(self):
		self.assertEqual(waliduj_teren({"teren_lat": 0, "teren_lng": 0, "promien_km": 0}), [])


class TestSortujHandlowcow(unittest.TestCase):
	def test_kolejnosc_kategorii_i_nazwy(self):
		wpisy = [
			{"user": "a", "full_name": "Zofia", "kategoria": ""},
			{"user": "b", "full_name": "Ola", "kategoria": "Nie umawiać"},
			{"user": "c", "full_name": "marek", "kategoria": "Standard"},
			{"user": "d", "full_name": "Jan", "kategoria": "Priorytet"},
			{"user": "e", "full_name": "Adam", "kategoria": "Standard"},
			{"user": "f", "full_name": "Ewa", "kategoria": "Priorytet"},
			{"user": "g", "full_name": "Basia"},
		]
		self.assertEqual([w["user"] for w in sortuj_handlowcow(wpisy)], ["f", "d", "e", "c", "b", "g", "a"])

	def test_nie_zmienia_wejscia(self):
		wpisy = [{"full_name": "B", "kategoria": ""}, {"full_name": "A", "kategoria": "Priorytet"}]
		sortuj_handlowcow(wpisy)
		self.assertEqual(wpisy[0]["full_name"], "B")


if __name__ == "__main__":
	unittest.main()
