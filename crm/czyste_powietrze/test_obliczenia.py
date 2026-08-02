import copy
import unittest
from decimal import Decimal

from crm.czyste_powietrze.obliczenia import CPDaneNiekompletne, CPPozycjaNieaktywna, oblicz_oferte

KATALOG = {
	"pompa_ciepla": {
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "35200",
		"dotacja": {"podstawowy": "14080", "podwyzszony": "24640", "najwyzszy": "35200"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "3000",
		"koszt_proenergy": "26500",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"pellet": {
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "25000",
		"dotacja": {"podstawowy": "8200", "podwyzszony": "14350", "najwyzszy": "20500"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "2000",
		"koszt_proenergy": "19000",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"zgazowujacy": {
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "34000",
		"dotacja": {"podstawowy": "8200", "podwyzszony": "14350", "najwyzszy": "20500"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "2000",
		"koszt_proenergy": "29000",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"cwu": {
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "20500",
		"dotacja": {"podstawowy": "8200", "podwyzszony": "14350", "najwyzszy": "20500"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "3000",
		"koszt_proenergy": "8000",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"grzejnik": {
		"kategoria": "co",
		"jednostka": "szt",
		"cena_netto": "1800",
		"dotacja": {"podstawowy": "720", "podwyzszony": "1260", "najwyzszy": "1800"},
		"limit_dotacji": {"podstawowy": "8200", "podwyzszony": "14350", "najwyzszy": "20500"},
		"prowizja": "100",
		"koszt_proenergy": "770",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"grzejnik_co": {
		"kategoria": "co",
		"jednostka": "szt",
		"cena_netto": "2200",
		"dotacja": {"podstawowy": "880", "podwyzszony": "1540", "najwyzszy": "2200"},
		"limit_dotacji": {"podstawowy": "8200", "podwyzszony": "14350", "najwyzszy": "20500"},
		"prowizja": "100",
		"koszt_proenergy": "900",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"elewacja": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "300",
		"dotacja": {"podstawowy": "110", "podwyzszony": "193", "najwyzszy": "275"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "10",
		"koszt_proenergy": "220",
		"koszt_staly": "3000",
		"aktywny": True,
	},
	"strop": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "10",
		"koszt_proenergy": "120",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"dach": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "300",
		"dotacja": {"podstawowy": "110", "podwyzszony": "193", "najwyzszy": "275"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "10",
		"koszt_proenergy": "220",
		"koszt_staly": "0",
		"aktywny": False,
	},
	"okna": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "1500",
		"dotacja": {"podstawowy": "528", "podwyzszony": "924", "najwyzszy": "1320"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "100",
		"koszt_proenergy": "1080",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"drzwi": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "2750",
		"dotacja": {"podstawowy": "1100", "podwyzszony": "1925", "najwyzszy": "2750"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "200",
		"koszt_proenergy": "4500",
		"koszt_staly": "0",
		"aktywny": True,
	},
}

LIMITY = {
	("podstawowy", "do80"): {"status": "do_ustalenia", "kwota": None},
	("podstawowy", "od80do140"): {"status": "kwota", "kwota": "19200"},
	("podstawowy", "powyzej140"): {"status": "kwota", "kwota": "33200"},
	("podwyzszony", "do80"): {"status": "do_ustalenia", "kwota": None},
	("podwyzszony", "od80do140"): {"status": "kwota", "kwota": "33600"},
	("podwyzszony", "powyzej140"): {"status": "kwota", "kwota": "58100"},
	("najwyzszy", "do80"): {"status": "do_ustalenia", "kwota": None},
	("najwyzszy", "od80do140"): {"status": "nie_dotyczy", "kwota": None},
	("najwyzszy", "powyzej140"): {"status": "kwota", "kwota": "83000"},
}

STALE = {
	"vat_mnoznik": "1.08",
	"mnozniki": {"elewacja": "1.4", "strop": "0.9", "dach": "1.3", "okna": "0.15"},
	"m2_na_drzwi": "2",
}


def _katalog() -> dict[str, dict[str, object]]:
	return copy.deepcopy(KATALOG)


def _wejscie(poziom: str = "podstawowy", standard: str = "powyzej140") -> dict[str, object]:
	return {
		"poziom": poziom,
		"standard": standard,
		"zrodlo_ciepla": "pompa_ciepla",
		"typ_grzejnikow": None,
		"ilosc_grzejnikow": 0,
		"powierzchnia_m2": "120",
		"prace": {
			"elewacja": {"wybrana": False, "m2": None},
			"strop": {"wybrana": False, "m2": None},
			"dach": {"wybrana": False, "m2": None},
			"okna": {"wybrana": False, "m2": None},
			"drzwi": {"wybrana": False, "ilosc": 0},
		},
	}


class TestObliczenia(unittest.TestCase):
	def policz(self: "TestObliczenia", wejscie: dict[str, object]) -> dict[str, object]:
		return oblicz_oferte(wejscie, _katalog(), copy.deepcopy(LIMITY), copy.deepcopy(STALE))

	def test_a_pompa_najwyzszy(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie("najwyzszy"))
		self.assertEqual(wynik["wklad_wlasny"], Decimal("2816.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("3000.00"))

	def test_b_pompa_podstawowy(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie())
		self.assertEqual(wynik["wklad_wlasny"], Decimal("23936.00"))

	def test_c_pompa_i_dziesiec_grzejnikow(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 10
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("36176.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("4000.00"))
		self.assertEqual(wynik["wewnetrzne"]["koszt_calkowity"], Decimal("34200.00"))

	def test_d_limit_grzejnikow(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 15
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("44896.00"))
		self.assertEqual(wynik["linie"][1]["dotacja"], Decimal("8200.00"))

	def test_e_wspolny_limit_termo_i_koszt_staly(self: "TestObliczenia") -> None:
		wejscie = _wejscie(standard="od80do140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("47544.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("2300.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("4120.00"))
		self.assertEqual(wynik["wewnetrzne"]["koszt_calkowity"], Decimal("44600.00"))

	def test_f_do_ustalenia_z_praca(self: "TestObliczenia") -> None:
		wejscie = _wejscie(standard="do80")
		wejscie["prace"]["elewacja"]["wybrana"] = True
		with self.assertRaises(CPDaneNiekompletne):
			self.policz(wejscie)

	def test_g_do_ustalenia_bez_pracy(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie(standard="do80"))
		self.assertEqual(wynik["wklad_wlasny"], Decimal("23936.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("0.00"))

	def test_h_nie_dotyczy_bez_limitu(self: "TestObliczenia") -> None:
		wejscie = _wejscie("najwyzszy", "od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("8232.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("0.00"))

	def test_i_nieaktywna_pozycja(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["prace"]["dach"]["wybrana"] = True
		with self.assertRaises(CPPozycjaNieaktywna):
			self.policz(wejscie)

	def test_manualna_powierzchnia_i_drzwi_liczone_na_sztuki(self: "TestObliczenia") -> None:
		wejscie = _wejscie("najwyzszy", "od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "30"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 2}
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["linie"][0]["netto"], Decimal("45000.00"))
		self.assertEqual(wynik["linie"][1]["netto"], Decimal("11000.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("3400.00"))

	def test_brak_wpisu_limitu(self: "TestObliczenia") -> None:
		limity = copy.deepcopy(LIMITY)
		del limity[("podstawowy", "powyzej140")]
		with self.assertRaises(CPDaneNiekompletne):
			oblicz_oferte(_wejscie(), _katalog(), limity, copy.deepcopy(STALE))

	def test_nieznane_dane_wejsciowe(self: "TestObliczenia") -> None:
		for pole, wartosc in (("poziom", "nieznany"), ("standard", "nieznany")):
			wejscie = _wejscie()
			wejscie[pole] = wartosc
			with self.assertRaises(CPDaneNiekompletne):
				self.policz(wejscie)

		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "nieznane_zrodlo"
		with self.assertRaises(CPDaneNiekompletne):
			self.policz(wejscie)

	def test_nieznana_praca_i_brak_wartosci_liczbowej(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["prace"]["nieznana"] = {"wybrana": True}
		with self.assertRaises(CPDaneNiekompletne):
			self.policz(wejscie)

		wejscie = _wejscie()
		wejscie["powierzchnia_m2"] = "nie-liczba"
		with self.assertRaises(CPDaneNiekompletne):
			self.policz(wejscie)

	def test_dotacja_nie_moze_zmniejszyc_wkladu_ponizej_zera(self: "TestObliczenia") -> None:
		katalog = _katalog()
		katalog["pompa_ciepla"]["dotacja"]["podstawowy"] = "50000"
		wynik = oblicz_oferte(_wejscie(), katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		self.assertEqual(wynik["wklad_wlasny"], Decimal("0.00"))

	def test_wynik_i_linie_zawieraja_kwoty_decimal(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie())
		self.assertEqual(
			set(wynik["linie"][0]),
			{"kod", "nazwa_kategorii", "ilosc", "jednostka", "netto", "brutto", "dotacja"},
		)
		for kwota in ("wklad_wlasny", "prowizja_handlowa", "dotacja_laczna", "dotacja_ograniczona_o"):
			self.assertIsInstance(wynik[kwota], Decimal)
		self.assertIsInstance(wynik["wewnetrzne"]["koszt_calkowity"], Decimal)
		self.assertIsInstance(wynik["linie"][0]["brutto"], Decimal)

	def test_zaokraglanie_half_up(self: "TestObliczenia") -> None:
		katalog = _katalog()
		pompa = katalog["pompa_ciepla"]
		pompa["cena_netto"] = "0.005"
		pompa["dotacja"]["podstawowy"] = "0"
		pompa["prowizja"] = "0"
		pompa["koszt_proenergy"] = "0"
		wynik = oblicz_oferte(_wejscie(), katalog, copy.deepcopy(LIMITY), {**STALE, "vat_mnoznik": "1"})
		self.assertEqual(wynik["wklad_wlasny"], Decimal("0.01"))
		self.assertEqual(wynik["linie"][0]["netto"], Decimal("0.01"))


if __name__ == "__main__":
	unittest.main()
