import copy
import unittest
from decimal import Decimal

from crm.czyste_powietrze.obliczenia import (
	CPDaneNiekompletne,
	CPNiedozwolonaKombinacja,
	CPPozycjaNieaktywna,
	oblicz_oferte,
)

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
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "10",
		"koszt_proenergy": "120",
		"koszt_staly": "0",
		"aktywny": True,
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
	("podstawowy", "do80"): {"status": "brak_dotacji", "kwota": None},
	("podstawowy", "od80do140"): {"status": "kwota", "kwota": "19200"},
	("podstawowy", "powyzej140"): {"status": "kwota", "kwota": "33200"},
	("podwyzszony", "do80"): {"status": "brak_dotacji", "kwota": None},
	("podwyzszony", "od80do140"): {"status": "kwota", "kwota": "33600"},
	("podwyzszony", "powyzej140"): {"status": "kwota", "kwota": "58100"},
	("najwyzszy", "do80"): {"status": "niedozwolone", "kwota": None},
	("najwyzszy", "od80do140"): {"status": "niedozwolone", "kwota": None},
	("najwyzszy", "powyzej140"): {"status": "kwota", "kwota": "83000"},
}

STALE = {
	"vat_mnoznik": "1.08",
	# "elewacja" 1.4 -> 1.3: zmiana wprowadzona równolegle z tą zmianą (nowy seed).
	# "okna" (0.15) zostaje w danych, ale nie jest już czytane w ścieżce automatycznej --
	# zastąpione przez mnoznik_okna_od_elewacji niżej (powierzchnia okien liczy się teraz
	# od fasady, nie od powierzchni użytkowej).
	"mnozniki": {"elewacja": "1.3", "strop": "0.9", "dach": "1.3", "okna": "0.15"},
	"m2_na_drzwi": "2",
	"mnoznik_okna_od_elewacji": "0.10",
	"udzial_dotacji_elewacja": "0.90",
}


def _katalog() -> dict[str, dict[str, object]]:
	return copy.deepcopy(KATALOG)


def _wejscie(poziom: str = "podstawowy", standard: str = "powyzej140") -> dict[str, object]:
	return {
		"poziom": poziom,
		"standard": standard,
		"zrodlo_ciepla": "pompa_ciepla",
		"cwu": False,
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
		grupa_co = next(g for g in wynik["grupy"] if g["kod"] == "co")
		self.assertEqual(grupa_co["dotacja"], Decimal("8200.00"))

	def test_e_wspolny_limit_termo_i_koszt_staly(self: "TestObliczenia") -> None:
		# Wartości poniżej przeliczone dla mnoznik_elewacja=1.3 (nie 1.4) i redukcji dotacji
		# elewacji do 90% powierzchni:
		#   m2 elewacji = 100 x 1.3 = 130; m2 stropu = 100 x 0.9 = 90 (bez zmian).
		#   netto_elewacja = 130 x 300 = 39000; brutto = 39000 x 1.08 = 42120.
		#   netto_strop = 90 x 220 = 19800; brutto = 19800 x 1.08 = 21384.
		#   brutto_termo = 42120 + 21384 = 63504.
		#   dotacja_elewacja (90% x 130 = 117 m2 dotowane) = 117 x 110 = 12870.
		#   dotacja_strop (bez redukcji) = 90 x 88 = 7920.
		#   dotacja_termo_surowa = 12870 + 7920 = 20790, ograniczona limitem kwotowym 19200
		#   -> dotacja_ograniczona_o = 20790 - 19200 = 1590.
		#   wklad_termo = 63504 - 19200 = 44304 = wklad_wlasny (brak zrodla/co).
		#   prowizja: elewacja 130 x 10 = 1300 (na PEŁNEJ powierzchni), strop 90 x 10 = 900
		#   -> 2200 (prowizja NIE jest redukowana, tylko dotacja).
		#   koszt: elewacja 130 x 220 + 3000 = 31600, strop 90 x 120 = 10800 -> 42400.
		wejscie = _wejscie(standard="od80do140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("44304.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("2200.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("1590.00"))
		self.assertEqual(wynik["wewnetrzne"]["koszt_calkowity"], Decimal("42400.00"))

	def test_f_do_ustalenia_z_praca(self: "TestObliczenia") -> None:
		wejscie = _wejscie(standard="do80")
		wejscie["prace"]["elewacja"]["wybrana"] = True
		limity = copy.deepcopy(LIMITY)
		limity[("podstawowy", "do80")] = {"status": "do_ustalenia", "kwota": None}
		with self.assertRaises(CPDaneNiekompletne):
			oblicz_oferte(wejscie, _katalog(), limity, copy.deepcopy(STALE))

	def test_g_do_ustalenia_bez_pracy(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie(standard="do80"))
		self.assertEqual(wynik["wklad_wlasny"], Decimal("23936.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("0.00"))

	def test_h_niedozwolona_kombinacja(self: "TestObliczenia") -> None:
		wejscie = _wejscie("najwyzszy", "od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		with self.assertRaises(CPNiedozwolonaKombinacja):
			self.policz(wejscie)

	def test_i_nieaktywna_pozycja(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["prace"]["okna"]["wybrana"] = True
		katalog = _katalog()
		katalog["okna"]["aktywny"] = False
		with self.assertRaises(CPPozycjaNieaktywna):
			oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))

	def test_m_piec_i_cwu(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "pellet"
		wejscie["cwu"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("32740.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("5000.00"))
		self.assertEqual(wynik["wewnetrzne"]["koszt_calkowity"], Decimal("27000.00"))

	def test_n_pompa_i_cwu_niedozwolone(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["cwu"] = True
		with self.assertRaises(CPNiedozwolonaKombinacja):
			self.policz(wejscie)

	def test_o_piec_i_grzejniki_niedozwolone(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "pellet"
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 5
		with self.assertRaises(CPNiedozwolonaKombinacja):
			self.policz(wejscie)

	def test_p_najwyzszy_do80_niedozwolone_bez_prac(self: "TestObliczenia") -> None:
		with self.assertRaises(CPNiedozwolonaKombinacja):
			self.policz(_wejscie("najwyzszy", "do80"))

	def test_q_najwyzszy_od80do140_niedozwolone_bez_prac(self: "TestObliczenia") -> None:
		with self.assertRaises(CPNiedozwolonaKombinacja):
			self.policz(_wejscie("najwyzszy", "od80do140"))

	def test_r_brak_dotacji_dla_termo(self: "TestObliczenia") -> None:
		# m2 elewacji = 100 x mnoznik_elewacja(1.3) = 130 (było 140 przy mnożniku 1.4).
		# netto = 130 x 300 = 39000; brutto = 39000 x 1.08 = 42120.
		# dotacja wymuszona na 0 (status "brak_dotacji"), więc redukcja do 90% jest tu bez
		# znaczenia -- linia["_dotacja"] jest nadpisywana na _ZERO niezależnie od wejścia.
		# wklad_wlasny = brutto_termo - 0 = 42120.
		wejscie = _wejscie(standard="do80")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("42120.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("0.00"))
		grupa_termo = next(g for g in wynik["grupy"] if g["kod"] == "termo")
		self.assertEqual(grupa_termo["dotacja"], Decimal("0.00"))

	def test_s_dach_stawki_jak_strop(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["dach"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("19448.00"))

	def test_t_piec_i_zero_grzejnikow(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "pellet"
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 0
		wynik = self.policz(wejscie)
		self.assertEqual([linia["kod"] for linia in wynik["linie"]], ["pellet"])

	def test_manualna_powierzchnia_i_drzwi_liczone_na_sztuki(self: "TestObliczenia") -> None:
		wejscie = _wejscie("podstawowy", "od80do140")
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
			{"kod", "nazwa_kategorii", "grupa", "ilosc", "jednostka", "netto", "brutto"},
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

	def test_wewnetrzne_linie_ilosc_i_kolejnosc_zgodna_z_liniami(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 1}
		wynik = self.policz(wejscie)
		kody_publiczne = [linia["kod"] for linia in wynik["linie"]]
		kody_wewnetrzne = [linia["kod"] for linia in wynik["wewnetrzne"]["linie"]]
		self.assertEqual(kody_wewnetrzne, kody_publiczne)
		self.assertEqual(len(wynik["wewnetrzne"]["linie"]), len(wynik["linie"]))

	def test_wewnetrzne_linie_koszt_i_prowizja_spojne(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 1}
		wynik = self.policz(wejscie)
		for linia in wynik["wewnetrzne"]["linie"]:
			self.assertEqual(
				linia["koszt"],
				linia["ilosc_rozliczeniowa"] * linia["koszt_jednostkowy"] + linia["koszt_staly"],
			)
			self.assertEqual(linia["prowizja"], linia["ilosc_rozliczeniowa"] * linia["stawka_prowizji"])

	def test_zysk_rowny_marza_minus_prowizja(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 10
		wynik = self.policz(wejscie)
		wewnetrzne = wynik["wewnetrzne"]
		self.assertEqual(wewnetrzne["prowizja_handlowa"], wynik["prowizja_handlowa"])
		self.assertEqual(wewnetrzne["zysk"], wewnetrzne["marza"] - wewnetrzne["prowizja_handlowa"])

	def test_drzwi_ilosc_rozliczeniowa_w_sztukach(self: "TestObliczenia") -> None:
		wejscie = _wejscie("podstawowy", "od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 2}
		wynik = self.policz(wejscie)
		linia_drzwi = next(l for l in wynik["wewnetrzne"]["linie"] if l["kod"] == "drzwi")
		self.assertEqual(linia_drzwi["ilosc_rozliczeniowa"], Decimal("2"))
		self.assertEqual(linia_drzwi["jednostka_rozliczeniowa"], "szt")
		# 2 szt. x koszt_proenergy=4500 + koszt_staly=0 = 9000
		self.assertEqual(linia_drzwi["koszt"], Decimal("9000.00"))
		# 2 szt. x prowizja=200 = 400
		self.assertEqual(linia_drzwi["prowizja"], Decimal("400.00"))

	def test_elewacja_koszt_staly_nie_skaluje_sie_z_powierzchnia(self: "TestObliczenia") -> None:
		def policz_dla_m2(m2: str) -> dict[str, object]:
			wejscie = _wejscie(standard="powyzej140")
			wejscie["zrodlo_ciepla"] = None
			wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": m2}
			return self.policz(wejscie)

		wynik_a = policz_dla_m2("100")
		wynik_b = policz_dla_m2("150")
		linia_a = wynik_a["wewnetrzne"]["linie"][0]
		linia_b = wynik_b["wewnetrzne"]["linie"][0]
		self.assertEqual(linia_a["koszt_staly"], linia_b["koszt_staly"])
		# koszt_jednostkowy=220, delta m2=50 -> delta kosztu wyłącznie z jednostkowego składnika
		self.assertEqual(linia_b["koszt"] - linia_a["koszt"], Decimal("11000.00"))

	def test_wynik_linie_nie_zawieraja_danych_kosztowych(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "10"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 1}
		wynik = self.policz(wejscie)
		zakazane_klucze = {
			"koszt",
			"prowizja",
			"stawka_prowizji",
			"koszt_jednostkowy",
			"koszt_staly",
			"ilosc_rozliczeniowa",
			"jednostka_rozliczeniowa",
			# "dotacja" per pozycja jest wymyślona, gdy wiąże limit grupy -- usunięta
			# w ramach przejścia na wynik["grupy"] (dotacja per grupa zakresu prac).
			"dotacja",
		}
		for linia in wynik["linie"]:
			for klucz in linia:
				self.assertFalse(klucz.startswith("_"), f"Klucz prywatny {klucz} przeciekł do wynik['linie']")
				self.assertNotIn(klucz, zakazane_klucze)

	def test_grupy_sumuja_sie_dokladnie_do_dotacji_lacznej(self: "TestObliczenia") -> None:
		"""Właściwość, na której opiera się cała ta zmiana: trzy kwoty grupowe muszą się
		sumować DOKŁADNIE do dotacja_laczna, niezależnie od tego, czy limit grupy zadziałał."""
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 15  # wiąże limit grupy "co"
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wynik = self.policz(wejscie)
		suma_grup = sum((grupa["dotacja"] for grupa in wynik["grupy"]), Decimal("0"))
		self.assertEqual(suma_grup, wynik["dotacja_laczna"])

	def test_grupy_limit_termo_wiaze(self: "TestObliczenia") -> None:
		"""Przypadek, w którym wiąże limit grupy termomodernizacji (dotacja_ograniczona_o > 0)."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertGreater(wynik["dotacja_ograniczona_o"], Decimal("0.00"))
		self.assertEqual(len(wynik["grupy"]), 1)
		grupa_termo = wynik["grupy"][0]
		self.assertEqual(grupa_termo["kod"], "termo")
		suma_grup = sum((grupa["dotacja"] for grupa in wynik["grupy"]), Decimal("0"))
		self.assertEqual(suma_grup, wynik["dotacja_laczna"])

	def test_grupy_cwu_bez_grzejnikow_trafia_do_co(self: "TestObliczenia") -> None:
		"""cwu ma kategoria=zrodlo w katalogu (bo tak liczy się jej limit), ale w prezentacji
		bez grzejników musi trafić do grupy "co", a "zrodlo" musi zostać z samym pelletem
		(cwu wymaga wybranego źródła pellet/zgazowujący, więc "zrodlo" zawsze współistnieje)."""
		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "pellet"
		wejscie["cwu"] = True
		wynik = self.policz(wejscie)
		grupy_wg_kodu = {grupa["kod"]: grupa for grupa in wynik["grupy"]}
		self.assertIn("co", grupy_wg_kodu)
		self.assertIn("zrodlo", grupy_wg_kodu)
		self.assertNotIn("termo", grupy_wg_kodu)

		pellet_pozycja = KATALOG["pellet"]
		cwu_pozycja = KATALOG["cwu"]
		# "zrodlo" zawiera wyłącznie pellet (cwu przeniesione do "co").
		self.assertEqual(grupy_wg_kodu["zrodlo"]["netto"], Decimal(pellet_pozycja["cena_netto"]))
		self.assertEqual(
			grupy_wg_kodu["zrodlo"]["dotacja"], Decimal(pellet_pozycja["dotacja"]["podstawowy"])
		)
		# "co" zawiera wyłącznie cwu (brak grzejników w tym wejściu).
		self.assertEqual(grupy_wg_kodu["co"]["netto"], Decimal(cwu_pozycja["cena_netto"]))
		self.assertEqual(grupy_wg_kodu["co"]["dotacja"], Decimal(cwu_pozycja["dotacja"]["podstawowy"]))

		suma_grup = sum((grupa["dotacja"] for grupa in wynik["grupy"]), Decimal("0"))
		self.assertEqual(suma_grup, wynik["dotacja_laczna"])

	def test_elewacja_dotacja_liczona_od_90_procent_powierzchni(self: "TestObliczenia") -> None:
		"""Dotacja na elewację obejmuje tylko 90% powierzchni (okna zajmują resztę fasady),
		ale netto/brutto/prowizja/koszt liczą się od PEŁNEJ powierzchni -- klient płaci za
		całą ścianę, fundusz dotuje tylko jej część."""
		wejscie = _wejscie(standard="powyzej140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "100"}
		wynik = self.policz(wejscie)
		linia_wew = wynik["wewnetrzne"]["linie"][0]
		linia_pub = wynik["linie"][0]
		self.assertEqual(linia_wew["kod"], "elewacja")
		# netto/brutto liczone od PEŁNEJ powierzchni (100 m2 x 300 zł, x1.08 VAT).
		self.assertEqual(linia_pub["netto"], Decimal("30000.00"))
		self.assertEqual(linia_pub["brutto"], Decimal("32400.00"))
		# prowizja/koszt też liczone od pełnej powierzchni (100 m2), nie zredukowane.
		self.assertEqual(linia_wew["prowizja"], Decimal("1000.00"))
		self.assertEqual(linia_wew["koszt"], Decimal("25000.00"))
		# dotacja pełnej powierzchni byłaby 100 x 110 = 11000; przy 90% powierzchni
		# (90 m2 dotowane) -> 90 x 110 = 9900 -- limit kwotowy (33200) tego nie ogranicza.
		grupa_termo = next(g for g in wynik["grupy"] if g["kod"] == "termo")
		self.assertEqual(grupa_termo["dotacja"], Decimal("9900.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("0.00"))

	def test_okna_powierzchnia_automatyczna_liczona_od_elewacji(self: "TestObliczenia") -> None:
		"""Automatyczna powierzchnia okien pochodzi teraz od powierzchni fasady, nie od
		powierzchni użytkowej: 100 m2 x mnoznik_elewacja(1.3) x mnoznik_okna_od_elewacji(0.10)
		= 13 m2 (dawniej byłoby 100 x mnoznik_okna(0.15) = 15 m2 -- ta ścieżka jest martwa)."""
		wejscie = _wejscie(standard="powyzej140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"]["wybrana"] = True
		wynik = self.policz(wejscie)
		linia = next(l for l in wynik["wewnetrzne"]["linie"] if l["kod"] == "okna")
		self.assertEqual(linia["ilosc_rozliczeniowa"], Decimal("13"))
		linia_pub = next(l for l in wynik["linie"] if l["kod"] == "okna")
		self.assertEqual(linia_pub["netto"], Decimal("19500.00"))  # 13 m2 x 1500 zł

	def test_okna_manualne_m2_nadpisuje_automatyczna_powierzchnie(self: "TestObliczenia") -> None:
		wejscie = _wejscie(standard="powyzej140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "20"}
		wynik = self.policz(wejscie)
		linia = next(l for l in wynik["wewnetrzne"]["linie"] if l["kod"] == "okna")
		self.assertEqual(linia["ilosc_rozliczeniowa"], Decimal("20"))

	def test_okna_automat_niezalezny_od_recznego_m2_elewacji(self: "TestObliczenia") -> None:
		"""Baza dla automatycznej powierzchni okien to ZAWSZE wyliczona powierzchnia fasady
		(powierzchnia_m2 x mnoznik_elewacja), niezależnie od ręcznej korekty m2 samej
		elewacji -- świadoma decyzja produktowa (patrz komentarz w obliczenia.py przy
		wyliczeniu powierzchnia_elewacji)."""
		wejscie = _wejscie(standard="powyzej140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "999"}
		wejscie["prace"]["okna"]["wybrana"] = True
		wynik = self.policz(wejscie)
		linia = next(l for l in wynik["wewnetrzne"]["linie"] if l["kod"] == "okna")
		self.assertEqual(linia["ilosc_rozliczeniowa"], Decimal("13"))

	def test_kazda_linia_ma_pole_grupa_a_cwu_trafia_do_co(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["zrodlo_ciepla"] = "pellet"
		wejscie["cwu"] = True
		wynik = self.policz(wejscie)
		for linia in wynik["linie"]:
			self.assertIn("grupa", linia)
		cwu_linia = next(l for l in wynik["linie"] if l["kod"] == "cwu")
		self.assertEqual(cwu_linia["grupa"], "co")
		self.assertEqual(cwu_linia["nazwa_kategorii"], "zrodlo")
		pellet_linia = next(l for l in wynik["linie"] if l["kod"] == "pellet")
		self.assertEqual(pellet_linia["grupa"], "zrodlo")
		self.assertEqual(pellet_linia["nazwa_kategorii"], "zrodlo")

	def test_grupy_suma_dotacji_zgodna_z_dotacja_laczna_przy_redukcji_elewacji(
		self: "TestObliczenia",
	) -> None:
		"""Redukcja dotacji elewacji do 90% powierzchni nie psuje telescopującej sumy grup:
		suma wynik["grupy"][*]["dotacja"] musi się nadal zgadzać co do grosza z
		dotacja_laczna, tak jak przed tą zmianą."""
		wejscie = _wejscie(standard="powyzej140")
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "77"}
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		suma_grup = sum((grupa["dotacja"] for grupa in wynik["grupy"]), Decimal("0"))
		self.assertEqual(suma_grup, wynik["dotacja_laczna"])

	def test_drzwi_zero_ilosc_nie_daje_linii(self: "TestObliczenia") -> None:
		"""Wybrane "drzwi" z ilością 0 nie generują pozycji na wycenie -- zerowa ilość i
		tak wnosi zero do wszystkich sum, więc pominięcie usuwa tylko szum z dokumentu
		(a dalej -- z BOM-u szansy, patrz crm/api/czyste_powietrze.py)."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "10"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 0}
		wynik = self.policz(wejscie)
		self.assertEqual([linia["kod"] for linia in wynik["linie"]], ["okna"])

	def test_elewacja_zero_m2_nie_daje_linii(self: "TestObliczenia") -> None:
		"""Praca liczona w m2 (nie tylko drzwi) z jawnym ręcznym m2=0 też nie daje linii --
		ten sam warunek (m2 == 0) pokrywa oba przypadki, zgodnie z komentarzem w
		obliczenia.py przy pętli prac termo."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "0"}
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual([linia["kod"] for linia in wynik["linie"]], ["strop"])

	def test_praca_z_dodatnia_iloscia_nadal_daje_linie(self: "TestObliczenia") -> None:
		"""Strażnik przed nadmiernym pomijaniem: dodatnia ilość (drzwi i m2) musi nadal
		wygenerować swoją linię."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "10"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 2}
		wynik = self.policz(wejscie)
		self.assertEqual({linia["kod"] for linia in wynik["linie"]}, {"okna", "drzwi"})

	def test_wszystkie_prace_termo_zerowe_grupa_znika(self: "TestObliczenia") -> None:
		"""Gdy każda wybrana praca termo ma zerową ilość/powierzchnię, grupa
		"Termomodernizacja" w ogóle nie pojawia się w wynik["grupy"] -- tak samo jak grupa
		bez żadnej wybranej pracy -- a suma grup nadal zgadza się dokładnie z
		dotacja_laczna (właściwość telescopującego sumowania, patrz
		test_grupy_sumuja_sie_dokladnie_do_dotacji_lacznej)."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "0"}
		wejscie["prace"]["strop"] = {"wybrana": True, "m2": "0"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 0}
		wynik = self.policz(wejscie)
		self.assertNotIn("termo", {grupa["kod"] for grupa in wynik["grupy"]})
		suma_grup = sum((grupa["dotacja"] for grupa in wynik["grupy"]), Decimal("0"))
		self.assertEqual(suma_grup, wynik["dotacja_laczna"])

	def test_golden_pompa_najwyzszy_powyzej140(self: "TestObliczenia") -> None:
		"""Golden check projektu: pompa ciepła + najwyzszy + powyzej140 -> wklad_wlasny 2816.00,
		niezmienione tą zmianą (przegrupowanie dotyczy wyłącznie prezentacji, nie liczb)."""
		wynik = self.policz(_wejscie("najwyzszy"))
		self.assertEqual(wynik["wklad_wlasny"], Decimal("2816.00"))


if __name__ == "__main__":
	unittest.main()
