import copy
import unittest
from decimal import Decimal

from crm.volteo_kalkulator_oze import (
	GRZEJNIKI_MAX,
	KLIMATYZACJA,
	KOCIOL,
	POMPA_CIEPLA,
	ROZBUDOWA,
	OZEBladMapowania,
	OZEBrakDoboru,
	OZEDaneNiekompletne,
	OZENiedozwolonaKombinacja,
	OZEPozycjaNieaktywna,
	cennik_z_wierszy,
	dobierz_moc_pompy,
	dobor_z_wierszy,
	oblicz_oferte,
	pozycje_dla,
	stale_z_singla,
	zsumuj_skladowe,
)

# --- Fikstura cennika, zbudowana z tych samych danych co SEED sekcji 1 planu --------------
# (nowy_kalkulator.md + korekty CEO 2026-10-04: Teta Mirror X 5,1 kW = 2700, nie 2500).

_POZYCJE: list[dict] = []
_SKLADOWE: list[dict] = []


def s(klucz: str, nazwa: str, typ: str, kwota: str, wspolna: bool = False) -> dict:
	return {"klucz": klucz, "nazwa": nazwa, "typ": typ, "kwota": kwota, "wspolna": wspolna}


def poz(kod: str, rodzaj: str, grupa: str, nazwa: str, skladowe: list[dict], **meta: object) -> None:
	wiersz = {
		"kod": kod,
		"nazwa": nazwa,
		"rodzaj": rodzaj,
		"grupa": grupa,
		"producent": meta.get("producent", ""),
		"model": meta.get("model", ""),
		"kolor": meta.get("kolor", ""),
		"moc_kw": meta.get("moc_kw", "0"),
		"ilosc": meta.get("ilosc", 1),
		"parametr": meta.get("parametr", ""),
		"opis": meta.get("opis", ""),
		"aktywny": meta.get("aktywny", True),
		"sort": meta.get("sort", 0),
	}
	_POZYCJE.append(wiersz)
	for skl in skladowe:
		_SKLADOWE.append({**skl, "parent": kod})


# Rozbudowa -- panele
_K_DOSTAWA_PANELE = "600"
for _n, (_panele, _konstrukcja, _montaz, _marza) in enumerate(
	[("400", "300", "300", "4000"), ("800", "600", "600", "5000"), ("1200", "900", "900", "6000"),
		("1600", "1200", "1200", "7000"), ("2000", "1500", "1500", "8000")],
	start=1,
):
	poz(
		f"roz_panele_{_n}", ROZBUDOWA, "panele", f"Panel PV x {_n}",
		[
			s("panele", "Panele", "Koszt", _panele),
			s("konstrukcja", "Konstrukcja", "Koszt", _konstrukcja),
			s("dostawa", "Dostawa", "Koszt", _K_DOSTAWA_PANELE, wspolna=True),
			s("montaz", "Montaż", "Koszt", _montaz),
			s("papiery_osd", "Papiery OSD", "Koszt", "300", wspolna=True),
			s("kilometrowka", "Kilometrówka", "Koszt", "500", wspolna=True),
			s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", _marza),
			s("bonus_liderski", "Bonus liderski", "Bonus liderski", "1500", wspolna=True),
		],
	)

# Rozbudowa -- panele + mikro
for _n, (_panele, _mikro, _konstrukcja, _montaz, _marza) in enumerate(
	[
		("400", "500", "300", "300", "4500"),
		("800", "1000", "600", "600", "5500"),
		("1200", "1500", "900", "900", "6500"),
		("1600", "2000", "1200", "1200", "7500"),
		("2000", "2500", "1500", "1500", "8500"),
	],
	start=1,
):
	poz(
		f"roz_panele_mikro_{_n}", ROZBUDOWA, "panele_mikro", f"Panel PV + mikrofalownik x {_n}",
		[
			s("panele", "Panele", "Koszt", _panele),
			s("mikro", "Mikro + osprzęt", "Koszt", _mikro),
			s("konstrukcja", "Konstrukcja", "Koszt", _konstrukcja),
			s("dostawa", "Dostawa", "Koszt", "600", wspolna=True),
			s("montaz", "Montaż", "Koszt", _montaz),
			s("papiery_osd", "Papiery OSD", "Koszt", "300", wspolna=True),
			s("kilometrowka", "Kilometrówka", "Koszt", "500", wspolna=True),
			s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", _marza),
			s("bonus_liderski", "Bonus liderski", "Bonus liderski", "1500", wspolna=True),
		],
	)

# Rozbudowa -- bateria (dostawa = 500, różne od paneli -- max() w testach to sprawdza)
for _m, (_bateria, _marza) in enumerate(
	[("3000", "6000"), ("6000", "7000"), ("9000", "8000"), ("12000", "9000")], start=1
):
	poz(
		f"roz_bateria_{_m}", ROZBUDOWA, "bateria", f"Moduł baterii x {_m}",
		[
			s("bateria", "Bateria", "Koszt", _bateria),
			s("dostawa", "Dostawa", "Koszt", "500", wspolna=True),
			s("montaz", "Montaż", "Koszt", "1000"),
			s("kilometrowka", "Kilometrówka", "Koszt", "500", wspolna=True),
			s("papiery_osd", "Papiery OSD", "Koszt", "300", wspolna=True),
			s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", _marza),
			s("bonus_liderski", "Bonus liderski", "Bonus liderski", "1500", wspolna=True),
		],
	)

_KLIMA_WSPOLNE = [
	s("montaz_akcesoria", "Montaż + akcesoria", "Koszt", "1500"),
	s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", "5000"),
	s("bonus_liderski", "Bonus liderski", "Bonus liderski", "1500"),
]

for _kod, _moc, _cena, _dodatkowe in [
	("klima_elis_x_2_6", "2.6", "1200", {}),
	("klima_elis_x_3_5", "3.5", "1300", {}),
	("klima_elis_x_5_1", "5.1", "1900", {}),
	("klima_elis_x_6_8", "6.8", "2600", {}),
]:
	poz(
		_kod, KLIMATYZACJA, "klima_chlodzenie", f"Rotenso Elis X (Czarny) {_moc} kW",
		[s("klimatyzacja", "Klimatyzacja (JZ+JW)", "Koszt", _cena), *_KLIMA_WSPOLNE],
		producent="Rotenso", model="Elis X", kolor="Czarny", moc_kw=_moc,
	)

# Jedna pozycja Roni X oznaczona nieaktywną -- do testu OZEPozycjaNieaktywna.
poz(
	"klima_roni_x_2_6", KLIMATYZACJA, "klima_chlodzenie", "Rotenso Roni X (Biały) 2.6 kW",
	[s("klimatyzacja", "Klimatyzacja (JZ+JW)", "Koszt", "1200"), *_KLIMA_WSPOLNE],
	producent="Rotenso", model="Roni X", kolor="Biały", moc_kw="2.6", aktywny=False,
)

for _kod, _moc, _cena in [("klima_teta_mirror_x_3_5", "3.5", "1700"), ("klima_teta_mirror_x_5_1", "5.1", "2700")]:
	poz(
		_kod, KLIMATYZACJA, "klima_dogrzewanie", f"Rotenso Teta Mirror X (Czarny) {_moc} kW",
		[s("klimatyzacja", "Klimatyzacja (JZ+JW)", "Koszt", _cena), *_KLIMA_WSPOLNE],
		producent="Rotenso", model="Teta Mirror X", kolor="Czarny", moc_kw=_moc,
	)

for _kod, _moc, _cena in [("klima_teta_x_3_5", "3.5", "1700"), ("klima_teta_x_5_1", "5.1", "2500")]:
	poz(
		_kod, KLIMATYZACJA, "klima_dogrzewanie", f"Rotenso Teta X (Biały) {_moc} kW",
		[s("klimatyzacja", "Klimatyzacja (JZ+JW)", "Koszt", _cena), *_KLIMA_WSPOLNE],
		producent="Rotenso", model="Teta X", kolor="Biały", moc_kw=_moc,
	)

poz(
	"klima_mira_x_3_5", KLIMATYZACJA, "klima_grzanie", "Rotenso Mira X (Biały) 3.5 kW",
	[s("klimatyzacja", "Klimatyzacja (JZ+JW)", "Koszt", "2900"), *_KLIMA_WSPOLNE],
	producent="Rotenso", model="Mira X", kolor="Biały", moc_kw="3.5",
)

_PC_WSPOLNE = [
	s("bufor", "Bufor", "Koszt", "2000"),
	s("montaz", "Montaż", "Koszt", "5500"),
	s("materialy_kotlowni", "Materiały kotłowni", "Koszt", "6000"),
	s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", "11000"),
	s("bonus_liderski", "Bonus liderski", "Bonus liderski", "3000"),
]

for _moc, _cena in [("6", "6700"), ("8", "7000"), ("10", "7300"), ("12", "9200"), ("14", "9520"), ("16", "9880")]:
	poz(
		f"pc_rotenso_mono_{_moc}", POMPA_CIEPLA, "pc_rotenso_mono", f"Rotenso Monoblok {_moc} kW",
		[s("pompa_ciepla", "Pompa ciepła", "Koszt", _cena), *_PC_WSPOLNE],
		producent="Rotenso", model="Monoblok", moc_kw=_moc,
	)

poz(
	"pc_midea_mono_4", POMPA_CIEPLA, "pc_midea_mono", "Midea Monoblok 4 kW",
	[s("pompa_ciepla", "Pompa ciepła", "Koszt", "10200"), *_PC_WSPOLNE],
	producent="Midea", model="Monoblok", moc_kw="4",
)

poz(
	"pc_midea_split_14", POMPA_CIEPLA, "pc_midea_split", "Midea Split 14 kW",
	[s("pompa_ciepla", "Pompa ciepła", "Koszt", "15500"), *_PC_WSPOLNE],
	producent="Midea", model="Split", moc_kw="14",
)

poz("cwu_pc_200", "Dodatek grzewczy", "cwu_pc", "Zasobnik CWU 200 l",
	[s("cwu", "Zasobnik CWU", "Koszt", "2500")])
poz("cwu_pc_300", "Dodatek grzewczy", "cwu_pc", "Zasobnik CWU 300 l",
	[s("cwu", "Zasobnik CWU", "Koszt", "3500")])
poz("cwu_kociol_200", "Dodatek grzewczy", "cwu_kociol", "Zasobnik CWU 200 l",
	[s("cwu", "Zasobnik CWU", "Koszt", "2000")])
poz("cwu_kociol_300", "Dodatek grzewczy", "cwu_kociol", "Zasobnik CWU 300 l",
	[s("cwu", "Zasobnik CWU", "Koszt", "3000")])

for _rozmiar, _cena in [
	("600x600", "920"), ("600x800", "970"), ("600x1000", "1020"), ("600x1200", "1120"), ("600x1600", "1420"),
]:
	poz(f"grzejnik_{_rozmiar}", "Dodatek grzewczy", "grzejnik", f"Grzejnik niskotemperaturowy {_rozmiar}",
		[s("grzejnik", "Grzejnik niskotemperaturowy", "Koszt", _cena)])

_KOCIOL_WSPOLNE_PELLET = [
	s("montaz", "Montaż", "Koszt", "4500"),
	s("materialy_kotlowni", "Materiały kotłowni", "Koszt", "4500"),
	s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", "11000"),
	s("bonus_liderski", "Bonus liderski", "Bonus liderski", "3000"),
]
for _moc, _cena in [("8", "7700"), ("12", "8200"), ("18", "9000")]:
	poz(f"kociol_pellet_{_moc}", KOCIOL, "kociol_pellet", f"Pereko QmPell Evo {_moc} kW",
		[s("kociol", "Kocioł", "Koszt", _cena), *_KOCIOL_WSPOLNE_PELLET],
		producent="Pereko", model="QmPell Evo", moc_kw=_moc)

_KOCIOL_WSPOLNE_DUO = [
	s("bufor", "Bufor", "Koszt", "2500"),
	s("montaz", "Montaż", "Koszt", "5000"),
	s("materialy_kotlowni", "Materiały kotłowni", "Koszt", "5000"),
	s("marza_proenergy", "Marża Proenergy", "Marża Proenergy", "11000"),
	s("bonus_liderski", "Bonus liderski", "Bonus liderski", "3000"),
]
for _moc, _cena in [("12", "13800"), ("15", "14200"), ("19", "14950")]:
	poz(f"kociol_duo_{_moc}", KOCIOL, "kociol_duo", f"Defro Firewood DUO {_moc} kW",
		[s("kociol", "Kocioł", "Koszt", _cena), *_KOCIOL_WSPOLNE_DUO],
		producent="Defro", model="Firewood DUO", moc_kw=_moc)

CENNIK = cennik_z_wierszy(_POZYCJE, _SKLADOWE)

_DOBOR_WIERSZE = []


def d(producent: str, typ: str, ogrzewanie: str, od_kw: str, do_kw: str, moc_kw: str) -> None:
	_DOBOR_WIERSZE.append(
		{
			"producent": producent, "typ": typ, "ogrzewanie": ogrzewanie,
			"od_kw": od_kw, "do_kw": do_kw, "moc_kw": moc_kw, "aktywny": True,
		}
	)


for _od, _do, _moc in [("0", "6", "6"), ("6.5", "8", "8"), ("8.5", "9.5", "10"), ("9.5", "10.5", "12"),
	("10.5", "12", "14"), ("12", "13.5", "16")]:
	d("Rotenso", "Monoblok", "Podłogówka", _od, _do, _moc)

for _od, _do, _moc in [("0", "3.5", "4"), ("4", "4.5", "6"), ("5", "5.5", "8"), ("6", "6.5", "10"),
	("7", "10", "12"), ("10.5", "11.5", "16")]:
	d("Midea", "Monoblok", "Grzejniki", _od, _do, _moc)

for _od, _do, _moc in [("0", "3.5", "4"), ("4", "5", "6"), ("5.5", "6", "8"), ("6.5", "7", "10"),
	("7.5", "10", "12"), ("10.5", "11", "14"), ("11.5", "12", "16")]:
	d("Midea", "Split", "Grzejniki", _od, _do, _moc)

DOBOR = dobor_z_wierszy(_DOBOR_WIERSZE)

STALE_DOKUMENT = {
	"vat_indyw": "8",
	"vat_biznes": "23",
	"narzut_max": "0",
	"pmt_oprocentowanie_mies": "1",
	"ppoz": "1000",
	"panel_moc_wp": "500",
}
STALE = stale_z_singla(STALE_DOKUMENT)


def wejscie_pc(**nadpisania: object) -> dict:
	baza = {
		"rodzaj": POMPA_CIEPLA,
		"typ_klienta": "indywidualny",
		"narzut": 0,
		"ulga_pct": 12,
		"okres_lat": 10,
		"wplata_wlasna": 0,
		"pompa": {
			"zapotrzebowanie": "5",
			"producent": "Rotenso",
			"typ": "Monoblok",
			"ogrzewanie": "Podłogówka",
			"cwu": "",
			"grzejniki": {},
		},
	}
	for klucz, wartosc in nadpisania.items():
		if klucz == "pompa":
			baza["pompa"] = {**baza["pompa"], **wartosc}
		else:
			baza[klucz] = wartosc
	return baza


class DobierzMocPompyTest(unittest.TestCase):
	def test_granice_rotenso_podlogowka(self) -> None:
		przypadki = {
			"6": "6", "8": "8", "9.5": "12", "10.5": "14", "12": "16", "13.5": "16",
		}
		for zapotrzebowanie, oczekiwana in przypadki.items():
			with self.subTest(zapotrzebowanie=zapotrzebowanie):
				moc = dobierz_moc_pompy(Decimal(zapotrzebowanie), "Rotenso", "Monoblok", "Podłogówka", DOBOR)
				self.assertEqual(moc, Decimal(oczekiwana))

	def test_poza_tabela_rzuca_brak_doboru(self) -> None:
		with self.assertRaises(OZEBrakDoboru) as kontekst:
			dobierz_moc_pompy(Decimal("14"), "Rotenso", "Monoblok", "Podłogówka", DOBOR)
		self.assertIn("Brak doboru", str(kontekst.exception))

	def test_ponizej_4_midea_mono_grzejniki(self) -> None:
		moc = dobierz_moc_pompy(Decimal("0"), "Midea", "Monoblok", "Grzejniki", DOBOR)
		self.assertEqual(moc, Decimal("4"))


class OblozOferteRozbudowaTest(unittest.TestCase):
	def _wejscie(self, **rozbudowa: object) -> dict:
		return {
			"rodzaj": ROZBUDOWA,
			"typ_klienta": "indywidualny",
			"narzut": 0,
			"ulga_pct": 0,
			"rozbudowa": {
				"panele": 0, "panele_mikro": 0, "bateria": 0,
				"istniejaca_pv_moc_kwp": 0, "ppoz_recznie": False,
				**rozbudowa,
			},
		}

	def test_2_panele_plus_1_bateria(self) -> None:
		wynik = oblicz_oferte(self._wejscie(panele=2, bateria=1), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"], Decimal("19900.00"))
		wspolne = [l for l in wynik["wewnetrzne"]["linie"] if l["klucz"].startswith("wspolne:")]
		self.assertEqual(len(wspolne), 4)
		po_klucz = {l["klucz"]: l["kwota"] for l in wspolne}
		self.assertEqual(po_klucz["wspolne:dostawa"], Decimal("600.00"))
		self.assertEqual(po_klucz["wspolne:kilometrowka"], Decimal("500.00"))
		self.assertEqual(po_klucz["wspolne:papiery_osd"], Decimal("300.00"))
		self.assertEqual(po_klucz["wspolne:bonus_liderski"], Decimal("1500.00"))

	def test_1_panel_1_mikro_1_bateria(self) -> None:
		wynik = oblicz_oferte(self._wejscie(panele=1, panele_mikro=1, bateria=1), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"], Decimal("23900.00"))

	def test_3_panele_samodzielnie(self) -> None:
		wynik = oblicz_oferte(self._wejscie(panele=3), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"], Decimal("11900.00"))

	def test_ppoz_prog_przekroczony(self) -> None:
		wynik = oblicz_oferte(
			self._wejscie(panele=2, istniejaca_pv_moc_kwp="6.0"), CENNIK, DOBOR, STALE
		)
		self.assertTrue(wynik["ppoz"])
		self.assertTrue(wynik["ppoz_prog"])
		self.assertEqual(wynik["netto"], Decimal("10900.00"))

	def test_ppoz_prog_nie_przekroczony(self) -> None:
		wynik = oblicz_oferte(
			self._wejscie(panele=2, istniejaca_pv_moc_kwp="5.5"), CENNIK, DOBOR, STALE
		)
		self.assertFalse(wynik["ppoz"])
		self.assertFalse(wynik["ppoz_prog"])
		self.assertEqual(wynik["netto"], Decimal("9900.00"))

	def test_zestaw_bez_producenta_modelu(self) -> None:
		wynik = oblicz_oferte(self._wejscie(panele=2, bateria=1), CENNIK, DOBOR, STALE)
		nazwy = {l["nazwa"] for l in wynik["linie"]}
		self.assertIn("Panel PV x 2", nazwy)
		self.assertIn("Moduł baterii x 1", nazwy)

	def test_brak_wyboru_jest_bledem(self) -> None:
		with self.assertRaises(OZEDaneNiekompletne):
			oblicz_oferte(self._wejscie(), CENNIK, DOBOR, STALE)


class OblozOferteKlimatyzacjaTest(unittest.TestCase):
	def _wejscie(self, kod: str, **nadpisania: object) -> dict:
		baza = {
			"rodzaj": KLIMATYZACJA,
			"typ_klienta": "indywidualny",
			"narzut": 0,
			"ulga_pct": 12,
			"klimatyzacja": {"kod": kod},
		}
		baza.update(nadpisania)
		return baza

	def test_elis_x_2_6_netto_i_ulga_zero(self) -> None:
		wynik = oblicz_oferte(self._wejscie("klima_elis_x_2_6"), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"], Decimal("9200.00"))
		self.assertEqual(wynik["ulga"], Decimal("0.00"))

	def test_elis_x_2_6_biznes_brutto(self) -> None:
		wynik = oblicz_oferte(
			self._wejscie("klima_elis_x_2_6", typ_klienta="biznesowy"), CENNIK, DOBOR, STALE
		)
		self.assertEqual(wynik["brutto"], Decimal("11316.00"))
		self.assertEqual(wynik["ulga"], Decimal("0.00"))
		self.assertEqual(wynik["raty"]["brutto"], Decimal("0.00"))

	def test_teta_mirror_x_5_1(self) -> None:
		wynik = oblicz_oferte(self._wejscie("klima_teta_mirror_x_5_1"), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"], Decimal("10700.00"))

	def test_pozycja_nieaktywna(self) -> None:
		with self.assertRaises(OZEPozycjaNieaktywna):
			oblicz_oferte(self._wejscie("klima_roni_x_2_6"), CENNIK, DOBOR, STALE)


class OblozOfertePompaCieplaTest(unittest.TestCase):
	def test_rotenso_mono_podlogowka_5_golden(self) -> None:
		wynik = oblicz_oferte(wejscie_pc(), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["pompa"], {"moc_kw": Decimal("6"), "kod": "pc_rotenso_mono_6"})
		self.assertEqual(wynik["netto"], Decimal("34200.00"))
		self.assertEqual(wynik["brutto"], Decimal("36936.00"))
		self.assertEqual(wynik["ulga"], Decimal("4432.32"))
		self.assertEqual(wynik["raty"]["brutto"], Decimal("529.92"))

	def test_6_5_z_cwu_200_i_grzejnikami(self) -> None:
		wynik = oblicz_oferte(
			wejscie_pc(pompa={"zapotrzebowanie": "6.5", "cwu": "200", "grzejniki": {"600x800": 2}}),
			CENNIK, DOBOR, STALE,
		)
		self.assertEqual(wynik["pompa"]["kod"], "pc_rotenso_mono_8")
		self.assertEqual(wynik["netto"], Decimal("38940.00"))

	def test_midea_split_mieszane_10_5(self) -> None:
		wynik = oblicz_oferte(
			wejscie_pc(
				pompa={"zapotrzebowanie": "10.5", "producent": "Midea", "typ": "Split", "ogrzewanie": "Mieszane"}
			),
			CENNIK, DOBOR, STALE,
		)
		self.assertEqual(wynik["pompa"]["kod"], "pc_midea_split_14")
		self.assertEqual(wynik["netto"], Decimal("43000.00"))

	def test_ponizej_4_midea_mono_grzejniki(self) -> None:
		wynik = oblicz_oferte(
			wejscie_pc(
				pompa={"zapotrzebowanie": "ponizej_4", "producent": "Midea", "typ": "Monoblok", "ogrzewanie": "Grzejniki"}
			),
			CENNIK, DOBOR, STALE,
		)
		self.assertEqual(wynik["pompa"]["kod"], "pc_midea_mono_4")
		self.assertEqual(wynik["netto"], Decimal("37700.00"))

	def test_14_kw_poza_tabela_rzuca_brak_doboru(self) -> None:
		with self.assertRaises(OZEBrakDoboru):
			oblicz_oferte(wejscie_pc(pompa={"zapotrzebowanie": "14"}), CENNIK, DOBOR, STALE)

	def test_rotenso_split_niedozwolona_kombinacja(self) -> None:
		with self.assertRaises(OZENiedozwolonaKombinacja):
			oblicz_oferte(
				wejscie_pc(pompa={"producent": "Rotenso", "typ": "Split"}), CENNIK, DOBOR, STALE
			)

	def test_grzejniki_powyzej_limitu(self) -> None:
		with self.assertRaises(OZENiedozwolonaKombinacja):
			oblicz_oferte(
				wejscie_pc(pompa={"grzejniki": {"600x600": GRZEJNIKI_MAX + 1}}), CENNIK, DOBOR, STALE
			)


class OblozOferteKociolTest(unittest.TestCase):
	def test_duo_15_z_cwu_300(self) -> None:
		wynik = oblicz_oferte(
			{
				"rodzaj": KOCIOL,
				"typ_klienta": "indywidualny",
				"narzut": 0,
				"ulga_pct": 0,
				"kociol": {"kod": "kociol_duo_15", "cwu": "300"},
			},
			CENNIK, DOBOR, STALE,
		)
		self.assertEqual(wynik["netto"], Decimal("43700.00"))


class NarzutLimitTest(unittest.TestCase):
	def test_narzut_ponad_limit_jest_bledem(self) -> None:
		stale_z_limitem = stale_z_singla({**STALE_DOKUMENT, "narzut_max": "500"})
		wejscie = {
			"rodzaj": KLIMATYZACJA,
			"typ_klienta": "indywidualny",
			"narzut": 1000,
			"ulga_pct": 0,
			"klimatyzacja": {"kod": "klima_elis_x_2_6"},
		}
		with self.assertRaises(OZEDaneNiekompletne):
			oblicz_oferte(wejscie, CENNIK, DOBOR, stale_z_limitem)

	def test_narzut_w_granicach_limitu_jest_ok(self) -> None:
		stale_z_limitem = stale_z_singla({**STALE_DOKUMENT, "narzut_max": "500"})
		wejscie = {
			"rodzaj": KLIMATYZACJA,
			"typ_klienta": "indywidualny",
			"narzut": 500,
			"ulga_pct": 0,
			"klimatyzacja": {"kod": "klima_elis_x_2_6"},
		}
		wynik = oblicz_oferte(wejscie, CENNIK, DOBOR, stale_z_limitem)
		self.assertEqual(wynik["netto"], Decimal("9700.00"))


class NiezmiennikiTest(unittest.TestCase):
	def test_koszt_marza_bonus_narzut_rowna_netto(self) -> None:
		wynik = oblicz_oferte(wejscie_pc(narzut=250), CENNIK, DOBOR, STALE)
		wew = wynik["wewnetrzne"]
		self.assertEqual(
			wew["koszt_calkowity"] + wew["marza_proenergy"] + wew["bonus_liderski"] + wew["narzut"],
			wynik["netto"],
		)

	def test_netto_plus_vat_rowna_brutto(self) -> None:
		wynik = oblicz_oferte(wejscie_pc(), CENNIK, DOBOR, STALE)
		self.assertEqual(wynik["netto"] + wynik["vat"], wynik["brutto"])

	def test_wejscie_niemutowane(self) -> None:
		wejscie = wejscie_pc(pompa={"zapotrzebowanie": "6.5", "cwu": "200", "grzejniki": {"600x800": 2}})
		kopia = copy.deepcopy(wejscie)
		cennik_kopia = copy.deepcopy(CENNIK)
		dobor_kopia = copy.deepcopy(DOBOR)
		stale_kopia = copy.deepcopy(STALE)
		oblicz_oferte(wejscie, CENNIK, DOBOR, STALE)
		self.assertEqual(wejscie, kopia)
		self.assertEqual(CENNIK, cennik_kopia)
		self.assertEqual(DOBOR, dobor_kopia)
		self.assertEqual(STALE, stale_kopia)


class MaperyTest(unittest.TestCase):
	def test_stale_z_singla_narzut_max_zero_daje_none(self) -> None:
		stale = stale_z_singla(STALE_DOKUMENT)
		self.assertIsNone(stale["narzut_max"])

	def test_stale_z_singla_brak_pola_jest_bledem_mapowania(self) -> None:
		niekompletny = dict(STALE_DOKUMENT)
		del niekompletny["ppoz"]
		with self.assertRaises(OZEBladMapowania):
			stale_z_singla(niekompletny)

	def test_cennik_z_wierszy_nieznana_skladowa_parent(self) -> None:
		with self.assertRaises(OZEBladMapowania):
			cennik_z_wierszy(
				[{"kod": "x", "nazwa": "X", "rodzaj": "Klimatyzacja", "grupa": "klima_chlodzenie",
					"producent": "", "model": "", "kolor": "", "moc_kw": "0", "ilosc": 1,
					"parametr": "", "opis": "", "aktywny": True, "sort": 0}],
				[{"parent": "nieznany", "klucz": "a", "nazwa": "A", "typ": "Koszt", "kwota": "1"}],
			)

	def test_pozycje_dla_nieznany_rodzaj(self) -> None:
		with self.assertRaises(OZEDaneNiekompletne):
			pozycje_dla({"rodzaj": "Coś innego"}, CENNIK, DOBOR)

	def test_zsumuj_skladowe_puste(self) -> None:
		wynik = zsumuj_skladowe([], CENNIK, ROZBUDOWA)
		self.assertEqual(wynik["linie"], [])
		self.assertEqual(wynik["koszt_calkowity"], Decimal("0"))


if __name__ == "__main__":
	unittest.main()
