# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_odpowiedz_filtr import czy_filtrowac, oczysc_docinfo, odfiltruj

TAJNE = {
	("CRM Deal", None): {"koszty"},
	("CRM Lead", None): {"cc"},
	("Wiersz", "CRM Deal"): {"cena_zakupu"},
	("Wiersz", None): {"cena_zakupu", "marza"},
}


def cb(doctype, parenttype):
	return TAJNE.get((doctype, parenttype))


class TestOdfiltruj(unittest.TestCase):
	def test_bez_doctype_nietkniety(self):
		d = {"koszty": 5}
		self.assertEqual(odfiltruj(d, cb), 0)
		self.assertEqual(d, {"koszty": 5})

	def test_dokument_na_szczycie(self):
		d = {"doctype": "CRM Deal", "koszty": "x", "name": "A"}
		self.assertEqual(odfiltruj(d, cb), 1)
		self.assertEqual(d, {"doctype": "CRM Deal", "koszty": None, "name": "A"})

	def test_pod_message(self):
		d = {"message": {"doctype": "CRM Deal", "koszty": 1}}
		self.assertEqual(odfiltruj(d, cb), 1)
		self.assertIsNone(d["message"]["koszty"])

	def test_docs_lista(self):
		d = {"docs": [{"doctype": "CRM Deal", "koszty": 1}, {"doctype": "CRM Lead", "cc": "u"}]}
		self.assertEqual(odfiltruj(d, cb), 2)

	def test_pod_data(self):
		d = {"data": {"doctype": "CRM Lead", "cc": "u"}}
		self.assertEqual(odfiltruj(d, cb), 1)

	def test_lista_dokumentow(self):
		l = [{"doctype": "CRM Deal", "koszty": 1}, {"doctype": "CRM Deal", "koszty": 2}]
		self.assertEqual(odfiltruj(l, cb), 2)

	def test_zagniezdzenie_5_poziomow(self):
		d = {"a": {"b": [{"c": {"d": {"doctype": "CRM Deal", "koszty": 1}}}]}}
		self.assertEqual(odfiltruj(d, cb), 1)
		self.assertIsNone(d["a"]["b"][0]["c"]["d"]["koszty"])

	def test_wiersze_potomne(self):
		d = {
			"doctype": "CRM Deal",
			"koszty": 1,
			"items": [{"doctype": "Wiersz", "parenttype": "CRM Deal", "cena_zakupu": 3, "marza": 4}],
		}
		self.assertEqual(odfiltruj(d, cb), 2)
		self.assertIsNone(d["items"][0]["cena_zakupu"])
		self.assertEqual(d["items"][0]["marza"], 4)

	def test_callback_dostaje_parenttype(self):
		wywolania = []

		def cb2(dt, pt):
			wywolania.append((dt, pt))

		odfiltruj({"doctype": "W", "parenttype": "P"}, cb2)
		self.assertEqual(wywolania, [("W", "P")])

	def test_parenttype_nie_str(self):
		wywolania = []

		def cb2(dt, pt):
			wywolania.append((dt, pt))

		odfiltruj({"doctype": "W", "parenttype": 5}, cb2)
		self.assertEqual(wywolania, [("W", None)])

	def test_doctype_nie_str_pomijany(self):
		for wartosc in (None, 7, ["CRM Deal"]):
			d = {"doctype": wartosc, "koszty": 1}
			self.assertEqual(odfiltruj(d, cb), 0)
			self.assertEqual(d["koszty"], 1)

	def test_nieznany_doctype(self):
		d = {"doctype": "Nieznany", "koszty": 1}
		self.assertEqual(odfiltruj(d, cb), 0)
		self.assertEqual(d["koszty"], 1)

	def test_wartosc_juz_none_nie_liczona(self):
		d = {"doctype": "CRM Deal", "koszty": None}
		self.assertEqual(odfiltruj(d, cb), 0)

	def test_wartosci_falsy_zerowane(self):
		d = {"doctype": "Wiersz", "cena_zakupu": 0, "marza": ""}
		self.assertEqual(odfiltruj(d, cb), 2)
		d = {"doctype": "Wiersz", "cena_zakupu": False}
		self.assertEqual(odfiltruj(d, cb), 1)

	def test_pole_lista_lub_slownik_w_calosci(self):
		d = {"doctype": "CRM Deal", "koszty": {"doctype": "X", "a": [1, 2]}}
		self.assertEqual(odfiltruj(d, cb), 1)
		self.assertIsNone(d["koszty"])
		d = {"doctype": "CRM Deal", "koszty": [1, 2]}
		self.assertEqual(odfiltruj(d, cb), 1)

	def test_brak_klucza_pola_nie_dodawany(self):
		d = {"doctype": "CRM Deal"}
		self.assertEqual(odfiltruj(d, cb), 0)
		self.assertNotIn("koszty", d)

	def test_callback_raz_na_pare(self):
		licznik = []

		def cb2(dt, pt):
			licznik.append((dt, pt))
			return {"koszty"}

		l = [{"doctype": "CRM Deal", "koszty": i} for i in range(5)]
		self.assertEqual(odfiltruj(l, cb2), 5)
		self.assertEqual(licznik, [("CRM Deal", None)])

	def test_gleboka_struktura(self):
		korzen = {"doctype": "CRM Deal", "koszty": 1}
		for _ in range(5000):
			korzen = {"w": korzen}
		self.assertEqual(odfiltruj(korzen, cb), 1)

	def test_typy_proste_na_szczycie(self):
		for x in ("a", 5, None, 1.5, True):
			self.assertEqual(odfiltruj(x, cb), 0)

	def test_tuple_odczyt(self):
		d = ({"doctype": "CRM Deal", "koszty": 1},)
		self.assertEqual(odfiltruj(d, cb), 1)


class TestCzyFiltrowac(unittest.TestCase):
	def test_json(self):
		self.assertTrue(czy_filtrowac("application/json", b'{"doctype": "X"}'))

	def test_json_charset_wielkosc_liter(self):
		self.assertTrue(czy_filtrowac("Application/JSON; charset=utf-8", b'{"doctype":"X"}'))

	def test_html(self):
		self.assertFalse(czy_filtrowac("text/html", b'"doctype"'))

	def test_none(self):
		self.assertFalse(czy_filtrowac(None, b'"doctype"'))

	def test_bez_doctype(self):
		self.assertFalse(czy_filtrowac("application/json", b'{"a": 1}'))

	def test_pusta_tresc(self):
		self.assertFalse(czy_filtrowac("application/json", b""))
		self.assertFalse(czy_filtrowac("application/json", None))


class TestOczyscDocinfo(unittest.TestCase):
	def test_czysci_wersje_i_komentarze(self):
		d = {"docinfo": {"versions": [{"data": "x"}], "comments": [1], "info_logs": {"a": 1}}}
		self.assertEqual(oczysc_docinfo(d), 3)
		self.assertEqual(d["docinfo"], {"versions": [], "comments": [], "info_logs": []})

	def test_puste_nie_liczone(self):
		d = {"docinfo": {"versions": [], "comments": {}, "views": None}}
		self.assertEqual(oczysc_docinfo(d), 0)

	def test_brak_docinfo(self):
		self.assertEqual(oczysc_docinfo({"message": 1}), 0)

	def test_docinfo_nie_slownik(self):
		self.assertEqual(oczysc_docinfo({"docinfo": [1]}), 0)

	def test_struktura_nie_slownik(self):
		self.assertEqual(oczysc_docinfo([{"docinfo": {"versions": [1]}}]), 0)
		self.assertEqual(oczysc_docinfo(None), 0)

	def test_klucze_spoza_listy_nietkniete(self):
		d = {"docinfo": {"attachments": [1], "shared": [2], "versions": [3], "name": "A"}}
		self.assertEqual(oczysc_docinfo(d), 1)
		self.assertEqual(d["docinfo"]["attachments"], [1])
		self.assertEqual(d["docinfo"]["shared"], [2])

	def test_zagniezdzone_nie_ruszane(self):
		d = {"message": {"docinfo": {"versions": [1]}}}
		self.assertEqual(oczysc_docinfo(d), 0)
		self.assertEqual(d["message"]["docinfo"]["versions"], [1])


if __name__ == "__main__":
	unittest.main()
