import copy
import unittest
from decimal import Decimal

from crm.czyste_powietrze.obliczenia import (
	CPDaneNiekompletne,
	CPNiedozwolonaKombinacja,
	CPPozycjaNieaktywna,
	baza_pracy,
	oblicz_oferte,
)
from crm.koszty.rdzen import zbuduj_snapshot_cp

KATALOG = {
	"pompa_ciepla": {
		"kategoria": "zrodlo",
		"jednostka": "szt",
		"cena_netto": "35200",
		"dotacja": {"podstawowy": "14080", "podwyzszony": "24640", "najwyzszy": "35200"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "3000",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "220",
		"koszt_staly": "3000",
		"aktywny": True,
	},
	# strop/dach: warianty materiałowe (patrz _WARIANTY_TERMO w obliczenia.py). Cena i dotacja
	# są CELOWO identyczne w obrębie każdej pary strop_*/dach_* na tym samym poziomie -- to
	# gwarancja produktowa (klient płaci i dostaje dotację tak samo niezależnie od materiału);
	# koszt_proenergy/prowizja różnią się per wariant. dach ma tylko piana/welna (bez
	# styropianu).
	"strop_piana": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "30",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "95",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"strop_welna": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "28",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "105",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"strop_styropian": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "25",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "120",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"dach_piana": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "30",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "95",
		"koszt_staly": "0",
		"aktywny": True,
	},
	"dach_welna": {
		"kategoria": "termo",
		"jednostka": "m2",
		"cena_netto": "220",
		"dotacja": {"podstawowy": "88", "podwyzszony": "154", "najwyzszy": "220"},
		"limit_dotacji": {"podstawowy": None, "podwyzszony": None, "najwyzszy": None},
		"prowizja": "28",
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
		"koszt_proenergy": "105",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		"nadprowizja_manager": "0",
		"nadprowizja_partner": "0",
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
		#   Brak "material" -> strop rozstrzyga się na domyślny wariant strop_piana (prowizja
		#   30, koszt_proenergy 95). prowizja: elewacja 130 x 10 = 1300 (na PEŁNEJ
		#   powierzchni), strop_piana 90 x 30 = 2700 -> 4000 (prowizja NIE jest redukowana,
		#   tylko dotacja).
		#   koszt: elewacja 130 x 220 + 3000 = 31600, strop_piana 90 x 95 = 8550 -> 40150.
		wejscie = _wejscie(standard="od80do140")
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"]["wybrana"] = True
		wejscie["prace"]["strop"]["wybrana"] = True
		wynik = self.policz(wejscie)
		self.assertEqual(wynik["wklad_wlasny"], Decimal("44304.00"))
		self.assertEqual(wynik["prowizja_handlowa"], Decimal("4000.00"))
		self.assertEqual(wynik["dotacja_ograniczona_o"], Decimal("1590.00"))
		self.assertEqual(wynik["wewnetrzne"]["koszt_calkowity"], Decimal("40150.00"))

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

	def test_s_dach_piana_cena_jak_strop_piana(self: "TestObliczenia") -> None:
		"""dach_piana i strop_piana wyceniają się KLIENTOWI identycznie (ta sama cena
		netto/dotacja dla tej samej powierzchni) mimo osobnych pozycji katalogowych -- różnią
		się wyłącznie kosztem/prowizją wewnętrzną, nigdy stroną publiczną wyceny. Powierzchnia
		musi być podana RĘCZNIE i identycznie dla obu prac -- mnozniki "strop" (0.9) i "dach"
		(1.3) różnią się, więc porównanie przez wspólne powierzchnia_m2 (automatyczne m2)
		porównywałoby różne powierzchnie, nie tę samą stawkę."""
		def policz_dla_pracy(kod: str) -> dict[str, object]:
			wejscie = _wejscie()
			wejscie["zrodlo_ciepla"] = None
			wejscie["prace"][kod] = {"wybrana": True, "m2": "100"}
			return self.policz(wejscie)

		wynik_dach = policz_dla_pracy("dach")
		wynik_strop = policz_dla_pracy("strop")
		self.assertEqual(wynik_dach["linie"][0]["kod"], "dach_piana")
		self.assertEqual(wynik_strop["linie"][0]["kod"], "strop_piana")
		self.assertEqual(wynik_dach["linie"][0]["netto"], Decimal("22000.00"))
		self.assertEqual(wynik_dach["linie"][0]["netto"], wynik_strop["linie"][0]["netto"])
		self.assertEqual(wynik_dach["linie"][0]["brutto"], wynik_strop["linie"][0]["brutto"])
		self.assertEqual(wynik_dach["dotacja_laczna"], wynik_strop["dotacja_laczna"])
		self.assertEqual(wynik_dach["wklad_wlasny"], wynik_strop["wklad_wlasny"])
		self.assertEqual(wynik_dach["wklad_wlasny"], Decimal("14960.00"))
		# Kod katalogowy różni się (rozstrzygnięty na domyślny wariant piana każdej pracy),
		# ale koszt/prowizja wewnętrzna są takie same między dach_piana i strop_piana -- to
		# zbieg wartości w tej fixturze (oba warianty piana mają identyczne stawki), nie
		# gwarancja produktowa; gwarancją jest wyłącznie identyczna cena/dotacja klienta
		# sprawdzona wyżej.
		self.assertEqual(
			wynik_dach["wewnetrzne"]["linie"][0]["koszt"], wynik_strop["wewnetrzne"]["linie"][0]["koszt"]
		)

	def test_s2_warianty_strop_i_dach_roznia_sie_tylko_kosztem_i_prowizja(
		self: "TestObliczenia",
	) -> None:
		"""Wełna i styropian kosztują/rozliczają się inaczej niż piana, ale cena i dotacja dla
		klienta pozostają identyczne w obrębie tej samej pracy (strop lub dach) -- to jest
		gwarancja produktowa tej zmiany."""
		def policz_wariant(kod: str, material: str) -> dict[str, object]:
			wejscie = _wejscie()
			wejscie["powierzchnia_m2"] = "100"
			wejscie["zrodlo_ciepla"] = None
			wejscie["prace"][kod] = {"wybrana": True, "m2": None, "material": material}
			return self.policz(wejscie)

		for kod, warianty in (
			("strop", ("strop_piana", "strop_welna", "strop_styropian")),
			("dach", ("dach_piana", "dach_welna")),
		):
			wyniki = [policz_wariant(kod, material) for material in warianty]
			for wynik in wyniki[1:]:
				self.assertEqual(wynik["linie"][0]["netto"], wyniki[0]["linie"][0]["netto"])
				self.assertEqual(wynik["linie"][0]["brutto"], wyniki[0]["linie"][0]["brutto"])
				self.assertEqual(wynik["wklad_wlasny"], wyniki[0]["wklad_wlasny"])
			kody_wewnetrzne = [w["wewnetrzne"]["linie"][0]["kod"] for w in wyniki]
			self.assertEqual(kody_wewnetrzne, list(warianty))
			koszty = {w["wewnetrzne"]["linie"][0]["koszt"] for w in wyniki}
			prowizje = {w["wewnetrzne"]["linie"][0]["prowizja"] for w in wyniki}
			# Koszty/prowizje różnią się między wariantami tej samej pracy -- inaczej test
			# byłby bez znaczenia (mógłby przejść nawet bez działających wariantów).
			self.assertGreater(len(koszty), 1)
			self.assertGreater(len(prowizje), 1)

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
		# Pułapka: gdy dotacja grupy przekracza jej brutto, wklad_wlasny jest przycinany do
		# zera (klamrowanie per grupa, patrz obliczenia.py ok. linii 439-441), więc
		# wklad_wlasny + dotacja_laczna PRZESTAJE być tożsame z sumą brutto linii. suma_brutto
		# musi więc pochodzić z linii, nigdy z tej sumy.
		suma_linii = sum((linia["brutto"] for linia in wynik["linie"]), Decimal("0"))
		self.assertEqual(wynik["suma_brutto"], suma_linii)
		self.assertNotEqual(wynik["suma_brutto"], wynik["wklad_wlasny"] + wynik["dotacja_laczna"])

	def test_wynik_i_linie_zawieraja_kwoty_decimal(self: "TestObliczenia") -> None:
		wynik = self.policz(_wejscie())
		self.assertEqual(
			set(wynik["linie"][0]),
			{"kod", "nazwa_kategorii", "grupa", "ilosc", "jednostka", "netto", "brutto"},
		)
		for kwota in ("wklad_wlasny", "prowizja_handlowa", "dotacja_laczna", "dotacja_ograniczona_o", "suma_brutto"):
			self.assertIsInstance(wynik[kwota], Decimal)
		self.assertIsInstance(wynik["wewnetrzne"]["koszt_calkowity"], Decimal)
		self.assertIsInstance(wynik["linie"][0]["brutto"], Decimal)

	def test_suma_brutto_rowna_sumie_linii(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wynik = self.policz(wejscie)
		suma_linii = sum((linia["brutto"] for linia in wynik["linie"]), Decimal("0"))
		self.assertEqual(wynik["suma_brutto"], suma_linii)
		self.assertEqual(wynik["suma_brutto"].as_tuple().exponent, -2)

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
		self.assertEqual([linia["kod"] for linia in wynik["linie"]], ["strop_piana"])

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

	def test_warianty_termo_koszt_i_prowizja_per_wariant(self: "TestObliczenia") -> None:
		"""Każdy z pięciu wariantów strop/dach, wybrany jawnie przez "material", generuje
		poprawny koszt i prowizję na linii wewnętrznej dla znanej powierzchni. strop ma
		mnoznik 0.9 (100 m2 budynku -> 90 m2 pracy), dach ma mnoznik 1.3 (100 m2 -> 130 m2)."""
		oczekiwane = {
			"strop_piana": ("strop", Decimal("90"), Decimal("8550.00"), Decimal("2700.00")),
			"strop_welna": ("strop", Decimal("90"), Decimal("9450.00"), Decimal("2520.00")),
			"strop_styropian": ("strop", Decimal("90"), Decimal("10800.00"), Decimal("2250.00")),
			"dach_piana": ("dach", Decimal("130"), Decimal("12350.00"), Decimal("3900.00")),
			"dach_welna": ("dach", Decimal("130"), Decimal("13650.00"), Decimal("3640.00")),
		}
		for material, (kod_bazowy, m2, koszt_oczekiwany, prowizja_oczekiwana) in oczekiwane.items():
			with self.subTest(material=material):
				wejscie = _wejscie()
				wejscie["powierzchnia_m2"] = "100"
				wejscie["zrodlo_ciepla"] = None
				wejscie["prace"][kod_bazowy] = {"wybrana": True, "m2": None, "material": material}
				wynik = self.policz(wejscie)
				linia = wynik["wewnetrzne"]["linie"][0]
				self.assertEqual(linia["kod"], material)
				self.assertEqual(linia["ilosc_rozliczeniowa"], m2)
				self.assertEqual(linia["koszt"], koszt_oczekiwany)
				self.assertEqual(linia["prowizja"], prowizja_oczekiwana)

	def test_material_domyslny_przy_braku_i_pustym_stringu(self: "TestObliczenia") -> None:
		"""Brak klucza "material" i pusty string "" oba rozstrzygają się na domyślny wariant
		(piana) -- literówka jest błędem (patrz test niżej), ale brak wyboru nie."""
		for wartosc_material in (None, ""):
			for kod_bazowy, domyslny in (("strop", "strop_piana"), ("dach", "dach_piana")):
				with self.subTest(kod_bazowy=kod_bazowy, wartosc_material=wartosc_material):
					wejscie = _wejscie()
					wejscie["powierzchnia_m2"] = "100"
					wejscie["zrodlo_ciepla"] = None
					praca: dict[str, object] = {"wybrana": True, "m2": None}
					if wartosc_material is not None:
						praca["material"] = wartosc_material
					wejscie["prace"][kod_bazowy] = praca
					wynik = self.policz(wejscie)
					self.assertEqual(wynik["linie"][0]["kod"], domyslny)

	def test_nieznany_material_rzuca_blad(self: "TestObliczenia") -> None:
		wejscie = _wejscie()
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["strop"] = {"wybrana": True, "m2": None, "material": "strop_bzdura"}
		with self.assertRaises(CPDaneNiekompletne):
			self.policz(wejscie)

	def test_dane_klienta_niezmienne_wzgledem_wariantu_stropu(self: "TestObliczenia") -> None:
		"""Najważniejsza gwarancja tej zmiany: netto, brutto, dotacja i wklad_wlasny są
		identyczne niezależnie od wybranego wariantu materiałowego stropu -- różni się
		wyłącznie koszt/prowizja wewnętrzna (sprawdzone osobno wyżej)."""
		def policz_wariant(material: str) -> dict[str, object]:
			wejscie = _wejscie(standard="powyzej140")
			wejscie["powierzchnia_m2"] = "100"
			wejscie["zrodlo_ciepla"] = None
			wejscie["prace"]["strop"] = {"wybrana": True, "m2": None, "material": material}
			return self.policz(wejscie)

		bazowy = policz_wariant("strop_piana")
		for material in ("strop_welna", "strop_styropian"):
			with self.subTest(material=material):
				wynik = policz_wariant(material)
				self.assertEqual(wynik["linie"][0]["netto"], bazowy["linie"][0]["netto"])
				self.assertEqual(wynik["linie"][0]["brutto"], bazowy["linie"][0]["brutto"])
				self.assertEqual(wynik["dotacja_laczna"], bazowy["dotacja_laczna"])
				self.assertEqual(wynik["wklad_wlasny"], bazowy["wklad_wlasny"])

	def test_baza_pracy_mapuje_warianty_i_zostawia_pozostale_kody(self: "TestObliczenia") -> None:
		self.assertEqual(baza_pracy("strop_piana"), "strop")
		self.assertEqual(baza_pracy("strop_welna"), "strop")
		self.assertEqual(baza_pracy("strop_styropian"), "strop")
		self.assertEqual(baza_pracy("dach_piana"), "dach")
		self.assertEqual(baza_pracy("dach_welna"), "dach")
		for kod_bez_wariantow in ("okna", "elewacja", "drzwi"):
			self.assertEqual(baza_pracy(kod_bez_wariantow), kod_bez_wariantow)

	# --- Nadprowizje Managera/Partnera (ops#47) ---------------------------------------

	def test_nadprowizja_drzwi_liczona_na_sztuki(self: "TestObliczenia") -> None:
		"""Drzwi rozliczają nadprowizję DOKŁADNIE jak prowizję -- za SZTUKĘ, nie za m2 --
		mimo że netto/dotacja liczą się od metrów kwadratowych (mieszana jednostka drzwi,
		patrz volteo-cp-drzwi-mieszana-jednostka)."""
		wejscie = _wejscie("podstawowy", "od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 2}
		katalog = _katalog()
		katalog["drzwi"]["nadprowizja_manager"] = "50"
		katalog["drzwi"]["nadprowizja_partner"] = "20"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		linia = next(l for l in wynik["wewnetrzne"]["linie"] if l["kod"] == "drzwi")
		# 2 szt. x 50 = 100.00 ; 2 szt. x 20 = 40.00 (NIE za m2 -- m2 drzwi to 2 x 2 = 4).
		self.assertEqual(linia["nadprowizja_manager"], Decimal("100.00"))
		self.assertEqual(linia["nadprowizja_partner"], Decimal("40.00"))
		self.assertEqual(linia["stawka_nadprowizji_manager"], Decimal("50.00"))
		self.assertEqual(linia["stawka_nadprowizji_partner"], Decimal("20.00"))
		# prowizja (2 x 200 = 400.00) + nadprowizja_manager (100.00) + nadprowizja_partner (40.00)
		self.assertEqual(linia["prowizja_pelna"], Decimal("540.00"))

	def test_nadprowizja_elewacja_liczona_na_pelnej_powierzchni(self: "TestObliczenia") -> None:
		"""Nadprowizja elewacji, tak jak jej prowizja, liczy się od PEŁNEJ powierzchni (100 m2)
		-- redukcja do 90% dotyczy WYŁĄCZNIE dotacji (okna zajmują resztę fasady), nie
		rozliczenia wewnętrznego ProEnergy."""
		wejscie = _wejscie(standard="powyzej140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "100"}
		katalog = _katalog()
		katalog["elewacja"]["nadprowizja_manager"] = "5"
		katalog["elewacja"]["nadprowizja_partner"] = "2"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		linia = wynik["wewnetrzne"]["linie"][0]
		self.assertEqual(linia["kod"], "elewacja")
		# 100 m2 (PEŁNA powierzchnia, nie 90 m2 dotowane) x stawka.
		self.assertEqual(linia["nadprowizja_manager"], Decimal("500.00"))
		self.assertEqual(linia["nadprowizja_partner"], Decimal("200.00"))

	def test_nadprowizja_wariant_stropu_bierze_stawke_z_wariantu(self: "TestObliczenia") -> None:
		"""Nadprowizja pochodzi z pozycji katalogowej WARIANTU (strop_welna), nie z bazowego
		kodu "strop" -- tak samo jak koszt/prowizja per wariant materiałowy."""
		wejscie = _wejscie()
		wejscie["powierzchnia_m2"] = "100"
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["strop"] = {"wybrana": True, "m2": None, "material": "strop_welna"}
		katalog = _katalog()
		katalog["strop_welna"]["nadprowizja_manager"] = "12"
		katalog["strop_welna"]["nadprowizja_partner"] = "6"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		linia = wynik["wewnetrzne"]["linie"][0]
		self.assertEqual(linia["kod"], "strop_welna")
		# mnoznik strop = 0.9 -> 100 x 0.9 = 90 m2.
		self.assertEqual(linia["nadprowizja_manager"], Decimal("1080.00"))
		self.assertEqual(linia["nadprowizja_partner"], Decimal("540.00"))

	def test_prowizje_ksztalt_i_suma(self: "TestObliczenia") -> None:
		"""wynik["prowizje"] jest publicznym podsumowaniem trzech strumieni prowizji --
		handlowiec (bez zmian, wsteczna zgodność), nadprowizja_manager, nadprowizja_partner
		-- i ich sumy."""
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		katalog = _katalog()
		katalog["pompa_ciepla"]["nadprowizja_manager"] = "100"
		katalog["pompa_ciepla"]["nadprowizja_partner"] = "40"
		katalog["grzejnik"]["nadprowizja_manager"] = "10"
		katalog["grzejnik"]["nadprowizja_partner"] = "4"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		self.assertEqual(
			set(wynik["prowizje"]), {"handlowiec", "nadprowizja_manager", "nadprowizja_partner", "suma"}
		)
		self.assertEqual(wynik["prowizje"]["handlowiec"], wynik["prowizja_handlowa"])
		# pompa: 1 x 100 = 100.00 ; grzejnik: 3 x 10 = 30.00 -> 130.00
		self.assertEqual(wynik["prowizje"]["nadprowizja_manager"], Decimal("130.00"))
		# pompa: 1 x 40 = 40.00 ; grzejnik: 3 x 4 = 12.00 -> 52.00
		self.assertEqual(wynik["prowizje"]["nadprowizja_partner"], Decimal("52.00"))
		self.assertEqual(
			wynik["prowizje"]["suma"],
			wynik["prowizje"]["handlowiec"]
			+ wynik["prowizje"]["nadprowizja_manager"]
			+ wynik["prowizje"]["nadprowizja_partner"],
		)

	def test_wewnetrzne_prowizja_pelna_i_pola_linii(self: "TestObliczenia") -> None:
		"""wewnetrzne["prowizja_pelna"] zgadza się z sumą prowizja_pelna po liniach, a każda
		linia niesie własne stawka_nadprowizji_*/nadprowizja_*/prowizja_pelna."""
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 3
		wejscie["prace"]["elewacja"] = {"wybrana": True, "m2": "50"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 1}
		katalog = _katalog()
		katalog["pompa_ciepla"]["nadprowizja_manager"] = "100"
		katalog["pompa_ciepla"]["nadprowizja_partner"] = "40"
		katalog["elewacja"]["nadprowizja_manager"] = "5"
		katalog["elewacja"]["nadprowizja_partner"] = "2"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		wewnetrzne = wynik["wewnetrzne"]
		for linia in wewnetrzne["linie"]:
			self.assertEqual(
				linia["prowizja_pelna"],
				linia["prowizja"] + linia["nadprowizja_manager"] + linia["nadprowizja_partner"],
			)
		suma_linii = sum((linia["prowizja_pelna"] for linia in wewnetrzne["linie"]), Decimal("0"))
		self.assertEqual(suma_linii, wewnetrzne["prowizja_pelna"])
		self.assertEqual(
			wewnetrzne["prowizja_pelna"],
			wewnetrzne["prowizja_handlowa"]
			+ wewnetrzne["nadprowizja_manager"]
			+ wewnetrzne["nadprowizja_partner"],
		)

	def test_zysk_rowny_marza_minus_prowizja_pelna(self: "TestObliczenia") -> None:
		"""Zmiana semantyczna tej zmiany (decyzja właściciela 2026-08-31): zysk = marza -
		prowizja_pelna (handlowiec + obie nadprowizje), nie tylko marza - prowizja_handlowa."""
		wejscie = _wejscie()
		wejscie["typ_grzejnikow"] = "grzejnik"
		wejscie["ilosc_grzejnikow"] = 10
		katalog = _katalog()
		katalog["pompa_ciepla"]["nadprowizja_manager"] = "200"
		katalog["pompa_ciepla"]["nadprowizja_partner"] = "80"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		wewnetrzne = wynik["wewnetrzne"]
		self.assertEqual(wewnetrzne["zysk"], wewnetrzne["marza"] - wewnetrzne["prowizja_pelna"])
		# z nadprowizjami > 0 zysk jest teraz NIŻSZY niż marza - prowizja_handlowa (stare
		# zachowanie) -- to jest właśnie ta zmiana semantyczna.
		self.assertNotEqual(wewnetrzne["zysk"], wewnetrzne["marza"] - wewnetrzne["prowizja_handlowa"])

	def test_nadprowizje_zerowe_nie_zmieniaja_zachowania_sprzed_zmiany(self: "TestObliczenia") -> None:
		"""Niezmiennik zgodności wstecznej: gdy obie nadprowizje są zerowe (stan seed na
		produkcji), zysk, prowizja_handlowa i zbudowany snapshot kosztów są identyczne z
		zachowaniem sprzed tej zmiany -- w tym golden check wklad_wlasny == 2816.00."""
		wejscie = _wejscie("najwyzszy")
		wejscie["typ_grzejnikow"] = None
		wynik = self.policz(wejscie)
		wewnetrzne = wynik["wewnetrzne"]
		self.assertEqual(wynik["wklad_wlasny"], Decimal("2816.00"))
		self.assertEqual(wewnetrzne["zysk"], wewnetrzne["marza"] - wewnetrzne["prowizja_handlowa"])
		self.assertEqual(wewnetrzne["nadprowizja_manager"], Decimal("0.00"))
		self.assertEqual(wewnetrzne["nadprowizja_partner"], Decimal("0.00"))
		self.assertEqual(wewnetrzne["prowizja_pelna"], wewnetrzne["prowizja_handlowa"])
		self.assertEqual(wynik["prowizje"]["suma"], wynik["prowizja_handlowa"])

		snapshot = zbuduj_snapshot_cp(wewnetrzne, {}, "2026-08-31 00:00:00")
		# Z nadprowizjami zerowymi snapshot niesie te same kwoty planu co przed tą zmianą:
		# prowizja_plan (teraz źródłowany z prowizja_pelna) == dawna prowizja_handlowa, a
		# zysk_plan pozostaje marza - prowizja_handlowa.
		self.assertEqual(snapshot["podsumowanie"]["prowizja_plan"], str(wewnetrzne["prowizja_handlowa"]))
		self.assertEqual(snapshot["podsumowanie"]["zysk_plan"], str(wewnetrzne["zysk"]))
		suma_linii = sum((Decimal(l["prowizja_plan"]) for l in snapshot["linie"]), Decimal("0.00"))
		self.assertEqual(suma_linii, Decimal(snapshot["podsumowanie"]["prowizja_plan"]))

	def test_snapshot_suma_prowizji_linii_zgadza_sie_z_podsumowaniem_gdy_nadprowizje_dodatnie(
		self: "TestObliczenia",
	) -> None:
		"""Ta sama właściwość co wyżej, ale z dodatnimi nadprowizjami na kilku liniach o
		różnych jednostkach rozliczeniowych (sztuka i m2) -- pilnuje, żeby zaokrąglanie per
		linia (w linie_wewnetrzne) nie rozjechało się z zaokrągleniem sumy całkowitej."""
		wejscie = _wejscie(standard="od80do140")
		wejscie["zrodlo_ciepla"] = None
		wejscie["prace"]["okna"] = {"wybrana": True, "m2": "10"}
		wejscie["prace"]["drzwi"] = {"wybrana": True, "ilosc": 2}
		katalog = _katalog()
		katalog["okna"]["nadprowizja_manager"] = "15"
		katalog["okna"]["nadprowizja_partner"] = "5"
		katalog["drzwi"]["nadprowizja_manager"] = "50"
		katalog["drzwi"]["nadprowizja_partner"] = "20"
		wynik = oblicz_oferte(wejscie, katalog, copy.deepcopy(LIMITY), copy.deepcopy(STALE))
		wewnetrzne = wynik["wewnetrzne"]

		snapshot = zbuduj_snapshot_cp(wewnetrzne, {}, "2026-08-31 00:00:00")
		suma_linii = sum((Decimal(l["prowizja_plan"]) for l in snapshot["linie"]), Decimal("0.00"))
		self.assertEqual(suma_linii, Decimal(snapshot["podsumowanie"]["prowizja_plan"]))


if __name__ == "__main__":
	unittest.main()
