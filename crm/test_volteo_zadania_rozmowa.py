import json
import unittest

from crm.volteo_zadania_rozmowa import (
	etykieta_zrodla,
	liczba_zmian_tresci,
	zmiany_tresci,
)


def _wersja(owner: str, creation: str, data: object) -> dict:
	return {"owner": owner, "creation": creation, "data": data}


def _dane_content(przed: str, po: str) -> dict:
	return {"changed": [["content", przed, po]], "added": [], "removed": []}


class TestZmianyTresci(unittest.TestCase):
	def test_a_pojedyncza_zmiana(self: "TestZmianyTresci") -> None:
		wynik = zmiany_tresci(
			[
				_wersja(
					"anna@proenergy.pro",
					"2026-11-16 10:00:00",
					json.dumps(_dane_content("<p>stara</p>", "<p>nowa</p>")),
				)
			]
		)
		self.assertEqual(
			wynik,
			[
				{
					"kto": "anna@proenergy.pro",
					"kiedy": "2026-11-16 10:00:00",
					"przed": "<p>stara</p>",
					"po": "<p>nowa</p>",
				}
			],
		)

	def test_b_dwie_zmiany_w_kolejnosci_rosnacej(self: "TestZmianyTresci") -> None:
		# Wejscie celowo w odwrotnej kolejnosci: wynik ma byc rosnacy po `creation`.
		wynik = zmiany_tresci(
			[
				_wersja("b@proenergy.pro", "2026-11-16 12:00:00", _dane_content("B", "C")),
				_wersja("a@proenergy.pro", "2026-11-16 09:00:00", _dane_content("A", "B")),
			]
		)
		self.assertEqual([z["przed"] for z in wynik], ["A", "B"])
		self.assertEqual([z["po"] for z in wynik], ["B", "C"])
		self.assertEqual([z["kto"] for z in wynik], ["a@proenergy.pro", "b@proenergy.pro"])

	def test_c_wersja_zmieniajaca_inne_pole_jest_pomijana(self: "TestZmianyTresci") -> None:
		wynik = zmiany_tresci(
			[
				_wersja(
					"a@proenergy.pro",
					"2026-11-16 09:00:00",
					{"changed": [["comment_by", "Anna", "Anna Nowak"]]},
				),
				_wersja("a@proenergy.pro", "2026-11-16 10:00:00", _dane_content("x", "y")),
			]
		)
		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["po"], "y")

	def test_d_wersja_z_content_i_innym_polem_zostawia_tylko_content(
		self: "TestZmianyTresci",
	) -> None:
		dane = {"changed": [["comment_by", "Anna", "Anna Nowak"], ["content", "x", "y"]]}
		wynik = zmiany_tresci([_wersja("a@proenergy.pro", "2026-11-16 10:00:00", dane)])
		self.assertEqual(len(wynik), 1)
		self.assertEqual((wynik[0]["przed"], wynik[0]["po"]), ("x", "y"))

	def test_e_data_jako_slownik_i_jako_string(self: "TestZmianyTresci") -> None:
		dane = _dane_content("x", "y")
		jako_slownik = zmiany_tresci([_wersja("a@proenergy.pro", "2026-11-16 10:00:00", dane)])
		jako_string = zmiany_tresci([_wersja("a@proenergy.pro", "2026-11-16 10:00:00", json.dumps(dane))])
		self.assertEqual(jako_slownik, jako_string)
		self.assertEqual(len(jako_slownik), 1)

	def test_f_zepsuty_json_jest_pomijany_bez_wyjatku(self: "TestZmianyTresci") -> None:
		wynik = zmiany_tresci(
			[
				_wersja("a@proenergy.pro", "2026-11-16 09:00:00", "{to nie jest json"),
				_wersja("a@proenergy.pro", "2026-11-16 09:30:00", ""),
				_wersja("a@proenergy.pro", "2026-11-16 09:45:00", None),
				_wersja("a@proenergy.pro", "2026-11-16 10:00:00", json.dumps(_dane_content("x", "y"))),
			]
		)
		self.assertEqual(len(wynik), 1)

	def test_g_brak_klucza_changed_albo_zly_ksztalt_sa_pomijane(self: "TestZmianyTresci") -> None:
		wynik = zmiany_tresci(
			[
				_wersja("a@proenergy.pro", "2026-11-16 09:00:00", {"added": []}),
				_wersja("a@proenergy.pro", "2026-11-16 09:10:00", {"changed": "nie lista"}),
				_wersja("a@proenergy.pro", "2026-11-16 09:20:00", {"changed": [["content"]]}),
				_wersja("a@proenergy.pro", "2026-11-16 09:30:00", {"changed": ["content", "x", "y"]}),
				_wersja("a@proenergy.pro", "2026-11-16 09:40:00", json.dumps([1, 2, 3])),
			]
		)
		self.assertEqual(wynik, [])

	def test_h_pusta_lista_i_brak_wejscia(self: "TestZmianyTresci") -> None:
		self.assertEqual(zmiany_tresci([]), [])
		self.assertEqual(zmiany_tresci(None), [])

	def test_i_nie_mutuje_wejscia(self: "TestZmianyTresci") -> None:
		wejscie = [
			_wersja("b@proenergy.pro", "2026-11-16 12:00:00", _dane_content("B", "C")),
			_wersja("a@proenergy.pro", "2026-11-16 09:00:00", _dane_content("A", "B")),
		]
		kopia = json.dumps(wejscie)
		zmiany_tresci(wejscie)
		self.assertEqual(json.dumps(wejscie), kopia)


class TestLiczbaZmianTresci(unittest.TestCase):
	def test_a_liczy_tylko_zmiany_tresci(self: "TestLiczbaZmianTresci") -> None:
		wersje = [
			_wersja("a@proenergy.pro", "2026-11-16 09:00:00", _dane_content("A", "B")),
			_wersja("a@proenergy.pro", "2026-11-16 09:30:00", {"changed": [["comment_by", "x", "y"]]}),
			_wersja("a@proenergy.pro", "2026-11-16 10:00:00", _dane_content("B", "C")),
			_wersja("a@proenergy.pro", "2026-11-16 11:00:00", "zepsute"),
		]
		self.assertEqual(liczba_zmian_tresci(wersje), 2)

	def test_b_pusta_lista_daje_zero(self: "TestLiczbaZmianTresci") -> None:
		self.assertEqual(liczba_zmian_tresci([]), 0)


class TestEtykietaZrodla(unittest.TestCase):
	def test_a_z_tytulem(self: "TestEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla("Zadzwonic do klienta"), "Zadanie: Zadzwonic do klienta")

	def test_b_bez_tytulu(self: "TestEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla(None), "Zadanie")
		self.assertEqual(etykieta_zrodla(""), "Zadanie")
		self.assertEqual(etykieta_zrodla("   "), "Zadanie")

	def test_c_tytul_jest_przycinany_z_bialych_znakow(self: "TestEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla("  Umowa  "), "Zadanie: Umowa")


if __name__ == "__main__":
	unittest.main()
