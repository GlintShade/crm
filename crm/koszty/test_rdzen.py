import copy
import unittest
from decimal import Decimal

from crm.koszty.rdzen import (
	aktualizuj_po_edycji_zestawu,
	bilans,
	czy_zmieniona_korekta,
	czy_zmieniony_plan,
	dopasuj_linie_do_wierszy,
	etykieta_wyswietlana,
	nierozdzielona_marza,
	policz_zmiany_planu,
	policz_zmiany_skladnikow,
	scal_snapshot,
	widok_kosztow,
	zbuduj_snapshot_cp,
	zbuduj_snapshot_oze,
	zmien_koszty_planowane,
	zmien_plan_laczny,
	zmien_skladniki_marzy,
)

WEWNETRZNE = {
	"koszt_calkowity": Decimal("29500.00"),
	"marza": Decimal("6700.00"),
	"prowizja_handlowa": Decimal("3000.00"),
	# "prowizja_pelna" = suma prowizji handlowca + obu nadprowizji (Manager/Partner) --
	# w tej fixturze nadprowizje są zerowe (patrz linie niżej: prowizja_pelna == prowizja
	# na każdej linii), więc prowizja_pelna == prowizja_handlowa. Test niezerowego
	# przypadku (nadprowizje > 0) żyje w crm/czyste_powietrze/test_obliczenia.py, bo tylko
	# tam rdzeń kalkulatora faktycznie liczy stawki -- ten moduł tylko przenosi gotowe
	# kwoty do kształtu snapshotu.
	"prowizja_pelna": Decimal("7200.00"),
	"zysk": Decimal("3700.00"),
	"linie": [
		{
			"kod": "pompa_ciepla",
			"ilosc_rozliczeniowa": Decimal("1"),
			"jednostka_rozliczeniowa": "szt",
			"netto": Decimal("35200.00"),
			"koszt": Decimal("26500.00"),
			"koszt_jednostkowy": Decimal("26500.00"),
			"koszt_staly": Decimal("0.00"),
			"stawka_prowizji": Decimal("3000.00"),
			"prowizja": Decimal("3000.00"),
			"prowizja_pelna": Decimal("3000.00"),
		},
		{
			"kod": "strop_piana",
			"ilosc_rozliczeniowa": Decimal("140"),
			"jednostka_rozliczeniowa": "m2",
			"netto": Decimal("30800.00"),
			"koszt": Decimal("16300.00"),
			"koszt_jednostkowy": Decimal("95.00"),
			"koszt_staly": Decimal("3000.00"),
			"stawka_prowizji": Decimal("30.00"),
			"prowizja": Decimal("4200.00"),
			"prowizja_pelna": Decimal("4200.00"),
		},
	],
}

NAZWY = {"pompa_ciepla": "Pompa ciepła", "strop_piana": "Strop (piana PUR)"}


def _snapshot() -> dict:
	return zbuduj_snapshot_cp(copy.deepcopy(WEWNETRZNE), dict(NAZWY), "2026-08-19 10:00:00")


class ZbudujSnapshotCpTest(unittest.TestCase):
	def test_ksztalt_i_wersja(self):
		snap = _snapshot()
		self.assertEqual(snap["wersja"], 1)
		self.assertEqual(snap["linia_produktowa"], "cp")
		self.assertEqual(snap["utworzono"], "2026-08-19 10:00:00")
		self.assertIsNone(snap["zmodyfikowano"])
		self.assertIsNone(snap["zmodyfikowal"])
		self.assertEqual(snap["skladniki_marzy"], [])
		self.assertEqual(snap["dodatkowe"], [])
		self.assertIsNone(snap["podsumowanie_rzeczywiste"])
		self.assertEqual(len(snap["linie"]), 2)

	def test_pola_linii(self):
		snap = _snapshot()
		linia = snap["linie"][0]
		self.assertEqual(linia["klucz"], "pompa_ciepla")
		self.assertEqual(linia["etykieta"], "Pompa ciepła")
		self.assertEqual(linia["ilosc"], "1")
		self.assertEqual(linia["jednostka"], "szt")
		self.assertEqual(linia["netto"], "35200.00")
		self.assertEqual(linia["prowizja_plan"], "3000.00")
		self.assertEqual(linia["koszt_plan"], "26500.00")
		self.assertIsNone(linia["koszt_rzeczywisty"])

	def test_etykieta_fallback_na_kod_gdy_brak_nazwy(self):
		wewnetrzne = copy.deepcopy(WEWNETRZNE)
		nazwy = {"pompa_ciepla": "Pompa ciepła"}  # brak "strop_piana"
		snap = zbuduj_snapshot_cp(wewnetrzne, nazwy, "2026-08-19 10:00:00")
		self.assertEqual(snap["linie"][1]["etykieta"], "strop_piana")

	def test_etykieta_fallback_gdy_nazwa_pusta(self):
		wewnetrzne = copy.deepcopy(WEWNETRZNE)
		nazwy = {"pompa_ciepla": "", "strop_piana": "Strop (piana PUR)"}
		snap = zbuduj_snapshot_cp(wewnetrzne, nazwy, "2026-08-19 10:00:00")
		self.assertEqual(snap["linie"][0]["etykieta"], "pompa_ciepla")

	def test_kwoty_sa_stringami_z_dwoma_miejscami(self):
		snap = _snapshot()
		for linia in snap["linie"]:
			for pole in ("netto", "prowizja_plan", "koszt_plan"):
				wartosc = linia[pole]
				self.assertIsInstance(wartosc, str)
				self.assertEqual(len(wartosc.split(".")[-1]), 2)
		for pole in ("netto", "koszt_plan", "marza_plan", "prowizja_plan", "zysk_plan"):
			self.assertIsInstance(snap["podsumowanie"][pole], str)

	def test_podsumowanie_rowna_sie_wewnetrznym_sumom(self):
		snap = _snapshot()
		self.assertEqual(snap["podsumowanie"]["koszt_plan"], "29500.00")
		self.assertEqual(snap["podsumowanie"]["marza_plan"], "6700.00")
		# prowizja_plan nosi teraz PEŁNĄ prowizję (wewnetrzne["prowizja_pelna"]), nie samą
		# prowizję handlowca (wewnetrzne["prowizja_handlowa"] zostaje 3000.00, ale nie jest
		# już czytane przez zbuduj_snapshot_cp) -- w tej fixturze nadprowizje są zerowe, ale
		# suma dwóch linii (3000.00 + 4200.00) i tak różni się od pojedynczej wartości
		# prowizja_handlowa, bo ta ostatnia w tej ręcznie zbudowanej fixturze nigdy nie była
		# sumą linii (patrz komentarz przy WEWNETRZNE wyżej).
		self.assertEqual(snap["podsumowanie"]["prowizja_plan"], "7200.00")
		self.assertEqual(snap["podsumowanie"]["zysk_plan"], "3700.00")

	def test_prowizja_plan_linii_sumuje_sie_do_podsumowania(self):
		"""Właściwość, na której opiera się mapowanie prowizja_plan w tym module: suma
		prowizja_plan wszystkich linii musi się zgadzać dokładnie z podsumowanie.prowizja_plan."""
		snap = _snapshot()
		suma_linii = sum((Decimal(l["prowizja_plan"]) for l in snap["linie"]), Decimal("0.00"))
		self.assertEqual(suma_linii, Decimal(snap["podsumowanie"]["prowizja_plan"]))

	def test_netto_to_suma_linii_netto(self):
		snap = _snapshot()
		suma = sum((Decimal(l["netto"]) for l in snap["linie"]), Decimal("0.00"))
		self.assertEqual(Decimal(snap["podsumowanie"]["netto"]), suma)
		self.assertEqual(snap["podsumowanie"]["netto"], "66000.00")

	def test_nie_mutuje_wejscia(self):
		wewnetrzne = copy.deepcopy(WEWNETRZNE)
		nazwy = dict(NAZWY)
		wewnetrzne_kopia = copy.deepcopy(wewnetrzne)
		nazwy_kopia = dict(nazwy)
		zbuduj_snapshot_cp(wewnetrzne, nazwy, "2026-08-19 10:00:00")
		self.assertEqual(wewnetrzne, wewnetrzne_kopia)
		self.assertEqual(nazwy, nazwy_kopia)


class ScalSnapshotHappyPathTest(unittest.TestCase):
	def test_happy_path_ustawia_koszt_rzeczywisty_i_liczy_podsumowanie(self):
		snap = _snapshot()
		nowy = scal_snapshot(
			snap,
			{"pompa_ciepla": "27000,00"},
			[],
			"2026-08-19 11:00:00",
			"admin@proenergy.pro",
		)
		self.assertEqual(nowy["zmodyfikowano"], "2026-08-19 11:00:00")
		self.assertEqual(nowy["zmodyfikowal"], "admin@proenergy.pro")
		linia = next(l for l in nowy["linie"] if l["klucz"] == "pompa_ciepla")
		self.assertEqual(linia["koszt_rzeczywisty"], "27000.00")
		# druga linia nieporuszona -> nadal None (fallback na plan)
		druga = next(l for l in nowy["linie"] if l["klucz"] == "strop_piana")
		self.assertIsNone(druga["koszt_rzeczywisty"])

		# koszt_rzeczywisty_total = 27000.00 (pompa, edytowana) + 16300.00 (strop, plan)
		podsumowanie = nowy["podsumowanie_rzeczywiste"]
		self.assertEqual(podsumowanie["koszt_rzeczywisty"], "43300.00")
		self.assertEqual(podsumowanie["pozycje_wg_planu"], 1)
		# marza = netto(66000.00) - koszt(43300.00)
		self.assertEqual(podsumowanie["marza_rzeczywista"], "22700.00")
		# zysk = marza - prowizja_plan(7200.00, teraz PEŁNA prowizja, nie tylko handlowca)
		self.assertEqual(podsumowanie["zysk_rzeczywisty"], "15500.00")

	def test_nie_mutuje_zapisanego_snapshotu(self):
		snap = _snapshot()
		snap_kopia = copy.deepcopy(snap)
		scal_snapshot(snap, {"pompa_ciepla": 100}, [], "2026-08-19 11:00:00", "admin@proenergy.pro")
		self.assertEqual(snap, snap_kopia)

	def test_plan_pola_przezywaja_scalenie_bez_zmian(self):
		snap = _snapshot()
		nowy = scal_snapshot(snap, {}, [], "2026-08-19 11:00:00", "admin@proenergy.pro")
		self.assertEqual(nowy["wersja"], snap["wersja"])
		self.assertEqual(nowy["linia_produktowa"], snap["linia_produktowa"])
		self.assertEqual(nowy["utworzono"], snap["utworzono"])
		self.assertEqual(nowy["podsumowanie"], snap["podsumowanie"])
		for stara, nowa in zip(snap["linie"], nowy["linie"], strict=True):
			self.assertEqual(stara["klucz"], nowa["klucz"])
			self.assertEqual(stara["etykieta"], nowa["etykieta"])
			self.assertEqual(stara["ilosc"], nowa["ilosc"])
			self.assertEqual(stara["jednostka"], nowa["jednostka"])
			self.assertEqual(stara["netto"], nowa["netto"])
			self.assertEqual(stara["prowizja_plan"], nowa["prowizja_plan"])
			self.assertEqual(stara["koszt_plan"], nowa["koszt_plan"])


class ScalSnapshotWalidacjaTest(unittest.TestCase):
	def test_nieznany_klucz_odrzucony(self):
		snap = _snapshot()
		with self.assertRaises(ValueError) as kontekst:
			scal_snapshot(snap, {"nieistniejaca_pozycja": "100"}, [], "2026-08-19", "admin")
		self.assertIn("nieistniejaca_pozycja", str(kontekst.exception))

	def test_ujemna_kwota_odrzucona(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {"pompa_ciepla": "-1"}, [], "2026-08-19", "admin")

	def test_smieciowy_string_odrzucony(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {"pompa_ciepla": "abc"}, [], "2026-08-19", "admin")

	def test_nan_odrzucony(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {"pompa_ciepla": float("nan")}, [], "2026-08-19", "admin")

	def test_nieskonczonosc_odrzucona(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {"pompa_ciepla": float("inf")}, [], "2026-08-19", "admin")

	def test_przecinek_dziesietny_sparsowany(self):
		snap = _snapshot()
		nowy = scal_snapshot(snap, {"pompa_ciepla": "1 234,56"}, [], "2026-08-19", "admin")
		linia = next(l for l in nowy["linie"] if l["klucz"] == "pompa_ciepla")
		self.assertEqual(linia["koszt_rzeczywisty"], "1234.56")

	def test_spacja_nierozdzielajaca_sparsowana(self):
		snap = _snapshot()
		nowy = scal_snapshot(snap, {"pompa_ciepla": "1\xa0234.56"}, [], "2026-08-19", "admin")
		linia = next(l for l in nowy["linie"] if l["klucz"] == "pompa_ciepla")
		self.assertEqual(linia["koszt_rzeczywisty"], "1234.56")

	def test_none_czysci_koszt_rzeczywisty(self):
		snap = _snapshot()
		z_edycja = scal_snapshot(snap, {"pompa_ciepla": "27000"}, [], "2026-08-19", "admin")
		wyczyszczony = scal_snapshot(z_edycja, {"pompa_ciepla": None}, [], "2026-08-19", "admin")
		linia = next(l for l in wyczyszczony["linie"] if l["klucz"] == "pompa_ciepla")
		self.assertIsNone(linia["koszt_rzeczywisty"])
		# fallback na plan -> pozycja liczy się znowu wg planu
		self.assertEqual(wyczyszczony["podsumowanie_rzeczywiste"]["pozycje_wg_planu"], 2)

	def test_linie_pominiete_w_mapie_zachowuja_zapisany_koszt(self):
		snap = _snapshot()
		z_edycja = scal_snapshot(snap, {"pompa_ciepla": "27000"}, [], "2026-08-19", "admin")
		# druga edycja nie wspomina "pompa_ciepla" -> ma zostać nietknięta
		nowy = scal_snapshot(z_edycja, {"strop_piana": "16000"}, [], "2026-08-19", "admin")
		pompa = next(l for l in nowy["linie"] if l["klucz"] == "pompa_ciepla")
		self.assertEqual(pompa["koszt_rzeczywisty"], "27000.00")


class ScalSnapshotDodatkoweTest(unittest.TestCase):
	def test_pusta_nazwa_odrzucona(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {}, [{"nazwa": "  ", "kwota": "100"}], "2026-08-19", "admin")

	def test_za_dluga_nazwa_odrzucona(self):
		snap = _snapshot()
		with self.assertRaises(ValueError):
			scal_snapshot(snap, {}, [{"nazwa": "x" * 141, "kwota": "100"}], "2026-08-19", "admin")

	def test_nazwa_dokladnie_140_znakow_ok(self):
		snap = _snapshot()
		nowy = scal_snapshot(snap, {}, [{"nazwa": "x" * 140, "kwota": "100"}], "2026-08-19", "admin")
		self.assertEqual(len(nowy["dodatkowe"]), 1)

	def test_nowy_wpis_dostaje_id_autora_i_znacznik_czasu(self):
		snap = _snapshot()
		nowy = scal_snapshot(
			snap,
			{},
			[{"nazwa": "Dojazd", "kwota": "250.50"}],
			"2026-08-19 12:00:00",
			"admin@proenergy.pro",
		)
		wpis = nowy["dodatkowe"][0]
		self.assertEqual(wpis["id"], "d-1")
		self.assertEqual(wpis["nazwa"], "Dojazd")
		self.assertEqual(wpis["kwota"], "250.50")
		self.assertEqual(wpis["autor"], "admin@proenergy.pro")
		self.assertEqual(wpis["utworzono"], "2026-08-19 12:00:00")

	def test_kolejny_nowy_wpis_dostaje_kolejny_numer(self):
		snap = _snapshot()
		pierwszy = scal_snapshot(snap, {}, [{"nazwa": "Dojazd", "kwota": "100"}], "2026-08-19", "admin")
		drugi = scal_snapshot(
			pierwszy,
			{},
			pierwszy["dodatkowe"] + [{"nazwa": "Materiały dodatkowe", "kwota": "50"}],
			"2026-08-19", "admin",
		)
		self.assertEqual([w["id"] for w in drugi["dodatkowe"]], ["d-1", "d-2"])

	def test_edycja_istniejacego_wpisu_zachowuje_autora_i_utworzono(self):
		snap = _snapshot()
		pierwszy = scal_snapshot(
			snap, {}, [{"nazwa": "Dojazd", "kwota": "100"}], "2026-08-19 09:00:00", "rep@proenergy.pro"
		)
		wpis = pierwszy["dodatkowe"][0]
		edytowany = scal_snapshot(
			pierwszy,
			{},
			[{"id": wpis["id"], "nazwa": "Dojazd (poprawiony)", "kwota": "120"}],
			"2026-08-19 10:00:00",
			"admin@proenergy.pro",
		)
		nowy_wpis = edytowany["dodatkowe"][0]
		self.assertEqual(nowy_wpis["id"], wpis["id"])
		self.assertEqual(nowy_wpis["nazwa"], "Dojazd (poprawiony)")
		self.assertEqual(nowy_wpis["kwota"], "120.00")
		# autor/utworzono ZACHOWANE ze starego wpisu, nie z edytora
		self.assertEqual(nowy_wpis["autor"], "rep@proenergy.pro")
		self.assertEqual(nowy_wpis["utworzono"], "2026-08-19 09:00:00")

	def test_zduplikowane_stare_id_w_nowej_liscie_odrzucone(self):
		snap = _snapshot()
		pierwszy = scal_snapshot(snap, {}, [{"nazwa": "Dojazd", "kwota": "100"}], "2026-08-19", "admin")
		wpis = pierwszy["dodatkowe"][0]
		with self.assertRaises(ValueError) as kontekst:
			scal_snapshot(
				pierwszy,
				{},
				[
					{"id": wpis["id"], "nazwa": "Dojazd A", "kwota": "100"},
					{"id": wpis["id"], "nazwa": "Dojazd B", "kwota": "200"},
				],
				"2026-08-19",
				"admin",
			)
		self.assertIn(wpis["id"], str(kontekst.exception))

	def test_dwa_nowe_wpisy_bez_id_w_jednym_wywolaniu_sa_ok(self):
		snap = _snapshot()
		nowy = scal_snapshot(
			snap,
			{},
			[{"nazwa": "Dojazd", "kwota": "100"}, {"nazwa": "Transport", "kwota": "50"}],
			"2026-08-19",
			"admin",
		)
		self.assertEqual([w["id"] for w in nowy["dodatkowe"]], ["d-1", "d-2"])
		self.assertEqual(nowy["dodatkowe"][0]["nazwa"], "Dojazd")
		self.assertEqual(nowy["dodatkowe"][1]["nazwa"], "Transport")

	def test_pominiecie_wpisu_w_nowej_liscie_usuwa_go(self):
		snap = _snapshot()
		pierwszy = scal_snapshot(snap, {}, [{"nazwa": "Dojazd", "kwota": "100"}], "2026-08-19", "admin")
		drugi = scal_snapshot(pierwszy, {}, [], "2026-08-19", "admin")
		self.assertEqual(drugi["dodatkowe"], [])

	def test_dodatkowe_wliczane_do_kosztu_rzeczywistego(self):
		snap = _snapshot()
		nowy = scal_snapshot(snap, {}, [{"nazwa": "Dojazd", "kwota": "500"}], "2026-08-19", "admin")
		# koszt_rzeczywisty_total = 26500.00 (pompa plan) + 16300.00 (strop plan) + 500.00 (dodatkowe)
		self.assertEqual(nowy["podsumowanie_rzeczywiste"]["koszt_rzeczywisty"], "43300.00")
		self.assertEqual(nowy["podsumowanie_rzeczywiste"]["pozycje_wg_planu"], 2)


class ScalSnapshotPvKsztaltTest(unittest.TestCase):
	def test_prowizja_plan_none_daje_zysk_rowny_marzy(self):
		snap = _snapshot()
		snap_pv = copy.deepcopy(snap)
		snap_pv["linia_produktowa"] = "pv"
		snap_pv["podsumowanie"] = {**snap_pv["podsumowanie"], "prowizja_plan": None}
		nowy = scal_snapshot(snap_pv, {}, [], "2026-08-19", "admin")
		podsumowanie = nowy["podsumowanie_rzeczywiste"]
		self.assertEqual(podsumowanie["marza_rzeczywista"], podsumowanie["zysk_rzeczywisty"])
		self.assertEqual(nowy["linia_produktowa"], "pv")


WEWNETRZNE_OZE = {
	"koszt_calkowity": Decimal("20200.00"),
	"marza_proenergy": Decimal("11000.00"),
	"bonus_liderski": Decimal("3000.00"),
	"narzut": Decimal("0.00"),
	"marza": Decimal("14000.00"),
	"zysk": Decimal("14000.00"),
	"linie": [
		{"klucz": "pc_rotenso_mono_6:pompa_ciepla", "etykieta": "Pompa ciepła (Rotenso Monoblok 6 kW)",
			"typ": "Koszt", "kwota": Decimal("6700.00")},
		{"klucz": "wspolne:bufor", "etykieta": "Bufor", "typ": "Koszt", "kwota": Decimal("2000.00")},
		{"klucz": "pc_rotenso_mono_6:montaz", "etykieta": "Montaż (Rotenso Monoblok 6 kW)",
			"typ": "Koszt", "kwota": Decimal("5500.00")},
		{"klucz": "pc_rotenso_mono_6:materialy_kotlowni", "etykieta": "Materiały kotłowni (Rotenso Monoblok 6 kW)",
			"typ": "Koszt", "kwota": Decimal("6000.00")},
		{"klucz": "pc_rotenso_mono_6:marza_proenergy", "etykieta": "Marża Proenergy (Rotenso Monoblok 6 kW)",
			"typ": "Marża Proenergy", "kwota": Decimal("11000.00")},
		{"klucz": "pc_rotenso_mono_6:bonus_liderski", "etykieta": "Bonus liderski (Rotenso Monoblok 6 kW)",
			"typ": "Bonus liderski", "kwota": Decimal("3000.00")},
	],
	"pozycje": [
		{"kod": "pc_rotenso_mono_6", "nazwa": "Rotenso Monoblok 6 kW", "ilosc": 1,
			"netto": Decimal("34200.00"), "koszt": Decimal("20200.00"),
			"marza": Decimal("11000.00"), "bonus": Decimal("3000.00")},
	],
}


class ZbudujSnapshotOzeTest(unittest.TestCase):
	def test_ksztalt_i_wersja(self):
		snap = zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05 10:00:00")
		self.assertEqual(snap["wersja"], 1)
		self.assertEqual(snap["linia_produktowa"], "oze")
		self.assertEqual(snap["utworzono"], "2026-10-05 10:00:00")
		self.assertIsNone(snap["zmodyfikowano"])
		self.assertIsNone(snap["zmodyfikowal"])
		self.assertIsNone(snap["podsumowanie_rzeczywiste"])
		self.assertEqual(snap["dodatkowe"], [])

	def test_tylko_linie_typu_koszt_trafiaja_do_linie(self):
		snap = zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05")
		# 4 linie typu Koszt (pompa, bufor wspólny, montaż, materiały kotłowni) -- marża i
		# bonus liderski (2 linie typu nie-Koszt) są odfiltrowane, zostają wyłącznie w
		# skladniki_marzy.
		self.assertEqual(len(snap["linie"]), 4)
		for linia in snap["linie"]:
			self.assertIsNone(linia["ilosc"])
			self.assertIsNone(linia["jednostka"])
			self.assertIsNone(linia["netto"])
			self.assertIsNone(linia["prowizja_plan"])
			self.assertIsNone(linia["koszt_rzeczywisty"])
		pompa = next(l for l in snap["linie"] if l["klucz"] == "pc_rotenso_mono_6:pompa_ciepla")
		self.assertEqual(pompa["koszt_plan"], "6700.00")
		self.assertEqual(pompa["etykieta"], "Pompa ciepła (Rotenso Monoblok 6 kW)")

	def test_skladniki_marzy(self):
		snap = zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05")
		po_klucz = {s["klucz"]: s["kwota"] for s in snap["skladniki_marzy"]}
		self.assertEqual(po_klucz["marza_proenergy"], "11000.00")
		self.assertEqual(po_klucz["bonus_liderski"], "3000.00")
		self.assertEqual(po_klucz["narzut"], "0.00")

	def test_podsumowanie(self):
		snap = zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05")
		podsumowanie = snap["podsumowanie"]
		# netto = koszt_calkowity(20200) + marza_proenergy(11000) + bonus_liderski(3000)
		# + narzut(0) = 34200.
		self.assertEqual(podsumowanie["netto"], "34200.00")
		self.assertEqual(podsumowanie["koszt_plan"], "20200.00")
		self.assertEqual(podsumowanie["marza_plan"], "14000.00")
		self.assertIsNone(podsumowanie["prowizja_plan"])
		# prowizja_plan is None -- zysk_plan == marza_plan, dokładnie jak w snapshotach PV
		# (patrz ScalSnapshotPvKsztaltTest powyżej i docstring zbuduj_snapshot_oze).
		self.assertEqual(podsumowanie["zysk_plan"], podsumowanie["marza_plan"])

	def test_narzut_niezerowy_wchodzi_do_netto_i_marzy_ale_nie_do_zysku_wewnetrznego(self):
		wewnetrzne = copy.deepcopy(WEWNETRZNE_OZE)
		wewnetrzne["narzut"] = Decimal("500.00")
		snap = zbuduj_snapshot_oze(wewnetrzne, "2026-10-05")
		podsumowanie = snap["podsumowanie"]
		self.assertEqual(podsumowanie["netto"], "34700.00")
		self.assertEqual(podsumowanie["marza_plan"], "14500.00")
		# zysk_plan snapshotu WCIĄŻ równe marza_plan (14500), mimo że wewnetrzne["zysk"]
		# (podgląd na żywo w kalkulatorze, nigdy nie czytany przez tę funkcję) wykluczałby
		# narzut -- patrz docstring zbuduj_snapshot_oze.
		self.assertEqual(podsumowanie["zysk_plan"], "14500.00")

	def test_wejscie_niemutowane(self):
		wewnetrzne = copy.deepcopy(WEWNETRZNE_OZE)
		kopia = copy.deepcopy(wewnetrzne)
		zbuduj_snapshot_oze(wewnetrzne, "2026-10-05")
		self.assertEqual(wewnetrzne, kopia)

	def test_scal_snapshot_na_snapshocie_oze(self):
		snap = zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05")
		nowy = scal_snapshot(snap, {}, [{"nazwa": "Dojazd", "kwota": "100"}], "2026-10-05", "admin")
		self.assertEqual(nowy["linia_produktowa"], "oze")
		self.assertEqual(nowy["dodatkowe"][0]["nazwa"], "Dojazd")
		# koszt_rzeczywisty_total = suma koszt_plan 4 linii (6700+2000+5500+6000=20200) + 100 dodatkowe.
		self.assertEqual(nowy["podsumowanie_rzeczywiste"]["koszt_rzeczywisty"], "20300.00")


class ScalSnapshotStabilnoscTest(unittest.TestCase):
	def test_dwukrotne_zastosowanie_tych_samych_wejsc_jest_stabilne(self):
		snap = _snapshot()
		pierwszy = scal_snapshot(
			snap,
			{"pompa_ciepla": "27000"},
			[{"nazwa": "Dojazd", "kwota": "250"}],
			"2026-08-19 11:00:00",
			"admin@proenergy.pro",
		)
		drugi = scal_snapshot(
			pierwszy,
			{"pompa_ciepla": "27000"},
			pierwszy["dodatkowe"],
			"2026-08-19 12:00:00",
			"admin@proenergy.pro",
		)
		# Same koszty/dodatkowe -> ten sam podsumowanie_rzeczywiste, poza znacznikiem czasu.
		self.assertEqual(
			drugi["podsumowanie_rzeczywiste"],
			pierwszy["podsumowanie_rzeczywiste"],
		)
		self.assertEqual(drugi["linie"], pierwszy["linie"])
		self.assertEqual(drugi["dodatkowe"], pierwszy["dodatkowe"])
		self.assertEqual(drugi["zmodyfikowano"], "2026-08-19 12:00:00")

	def test_nie_mutuje_wejsciowych_argumentow(self):
		snap = _snapshot()
		koszty = {"pompa_ciepla": "27000"}
		koszty_kopia = dict(koszty)
		dodatkowe = [{"nazwa": "Dojazd", "kwota": "250"}]
		dodatkowe_kopia = copy.deepcopy(dodatkowe)
		scal_snapshot(snap, koszty, dodatkowe, "2026-08-19", "admin")
		self.assertEqual(koszty, koszty_kopia)
		self.assertEqual(dodatkowe, dodatkowe_kopia)


if __name__ == "__main__":
	unittest.main()


def _snapshot_oze() -> dict:
	return zbuduj_snapshot_oze(copy.deepcopy(WEWNETRZNE_OZE), "2026-10-05 10:00:00")


class AktualizujPoEdycjiZestawuTest(unittest.TestCase):
	def test_none_i_pusty_snapshot_daja_none(self):
		self.assertIsNone(aktualizuj_po_edycji_zestawu(None, "1000", "a@x.pl", "2026-10-15 10:00:00", ""))
		self.assertIsNone(aktualizuj_po_edycji_zestawu({}, "1000", "a@x.pl", "2026-10-15 10:00:00", ""))

	def test_oze_bez_prowizji_zysk_rowny_marzy(self):
		snap = _snapshot_oze()
		koszt = Decimal(snap["podsumowanie"]["koszt_plan"])
		nowy = aktualizuj_po_edycji_zestawu(snap, "50000", "a@x.pl", "2026-10-15 10:00:00", "aneks")
		self.assertEqual(nowy["podsumowanie"]["netto"], "50000.00")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], str(Decimal("50000.00") - koszt))
		self.assertEqual(nowy["podsumowanie"]["zysk_plan"], nowy["podsumowanie"]["marza_plan"])
		self.assertIsNone(nowy["podsumowanie"]["prowizja_plan"])

	def test_z_prowizja_zysk_pomniejszony(self):
		snap = _snapshot()
		koszt = Decimal(snap["podsumowanie"]["koszt_plan"])
		prowizja = Decimal(snap["podsumowanie"]["prowizja_plan"])
		nowy = aktualizuj_po_edycji_zestawu(snap, Decimal("70000"), "a@x.pl", "2026-10-15 10:00:00", "")
		marza = Decimal("70000.00") - koszt
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], str(marza))
		self.assertEqual(nowy["podsumowanie"]["zysk_plan"], str(marza - prowizja))

	def test_zachowuje_linie_dodatkowe_i_skladniki(self):
		snap = scal_snapshot(
			_snapshot(), {"pompa_ciepla": "27000"}, [{"nazwa": "Dojazd", "kwota": "250"}], "2026-08-19", "adm"
		)
		nowy = aktualizuj_po_edycji_zestawu(snap, "60000", "a@x.pl", "2026-10-15 10:00:00", "x")
		self.assertEqual(nowy["linie"], snap["linie"])
		self.assertEqual(nowy["dodatkowe"], snap["dodatkowe"])
		self.assertEqual(nowy["skladniki_marzy"], snap["skladniki_marzy"])
		self.assertEqual(nowy["utworzono"], snap["utworzono"])

	def test_przelicza_podsumowanie_rzeczywiste_gdy_istnialo(self):
		snap = scal_snapshot(_snapshot(), {"pompa_ciepla": "27000"}, [], "2026-08-19", "adm")
		nowy = aktualizuj_po_edycji_zestawu(snap, "60000", "a@x.pl", "2026-10-15 10:00:00", "")
		rz = nowy["podsumowanie_rzeczywiste"]
		koszt = Decimal(rz["koszt_rzeczywisty"])
		self.assertEqual(rz["marza_rzeczywista"], str(Decimal("60000.00") - koszt))

	def test_podsumowanie_rzeczywiste_none_zostaje_none(self):
		nowy = aktualizuj_po_edycji_zestawu(_snapshot_oze(), "50000", "a@x.pl", "2026-10-15 10:00:00", "")
		self.assertIsNone(nowy["podsumowanie_rzeczywiste"])

	def test_edycja_reczna_i_znaczniki(self):
		snap = _snapshot_oze()
		przed = snap["podsumowanie"]["netto"]
		nowy = aktualizuj_po_edycji_zestawu(snap, "50000", "a@x.pl", "2026-10-15 10:00:00", "  aneks 1  ")
		self.assertEqual(
			nowy["edycja_reczna"],
			{
				"kiedy": "2026-10-15 10:00:00",
				"kto": "a@x.pl",
				"powod": "aneks 1",
				"netto_przed": przed,
				"netto_pierwotne": przed,
			},
		)
		self.assertEqual(nowy["zmodyfikowano"], "2026-10-15 10:00:00")
		self.assertEqual(nowy["zmodyfikowal"], "a@x.pl")

	def test_netto_pierwotne_z_pierwszej_edycji_zachowane(self):
		snap = _snapshot_oze()
		pierwotne = snap["podsumowanie"]["netto"]
		p1 = aktualizuj_po_edycji_zestawu(snap, "50000", "a@x.pl", "2026-10-15 10:00:00", "a")
		p2 = aktualizuj_po_edycji_zestawu(p1, "55000", "b@x.pl", "2026-10-16 10:00:00", "b")
		self.assertEqual(p2["edycja_reczna"]["netto_przed"], "50000.00")
		self.assertEqual(p2["edycja_reczna"]["netto_pierwotne"], pierwotne)
		self.assertEqual(p2["edycja_reczna"]["kto"], "b@x.pl")

	def test_nie_mutuje_wejscia(self):
		snap = _snapshot_oze()
		kopia = copy.deepcopy(snap)
		nowy = aktualizuj_po_edycji_zestawu(snap, "50000", "a@x.pl", "2026-10-15 10:00:00", "")
		self.assertEqual(snap, kopia)
		self.assertIsNot(nowy, snap)
		self.assertIsNot(nowy["linie"], snap["linie"])

	def test_edycja_reczna_przezywa_scal_snapshot(self):
		edytowany = aktualizuj_po_edycji_zestawu(_snapshot_oze(), "50000", "a@x.pl", "2026-10-15", "p")
		klucz = edytowany["linie"][0]["klucz"]
		po_kosztach = scal_snapshot(edytowany, {klucz: "100"}, [], "2026-10-16", "adm")
		self.assertEqual(po_kosztach["edycja_reczna"], edytowany["edycja_reczna"])
		self.assertEqual(po_kosztach["podsumowanie"]["netto"], "50000.00")


T0 = "2026-11-13 10:00:00"


def _pv_snapshot() -> dict:
	"""Snapshot w kształcie silnika PV: linie bez ilości/netto, suma planu = suma linii."""
	linie = [
		{
			"klucz": klucz,
			"etykieta": klucz,
			"ilosc": None,
			"jednostka": None,
			"netto": None,
			"prowizja_plan": None,
			"koszt_plan": kwota,
			"koszt_rzeczywisty": None,
		}
		for klucz, kwota in (("k_falownik", "5000.00"), ("k_bateria", "12000.00"), ("k_montaz_pv", "3000.00"))
	]
	return {
		"wersja": 1,
		"linia_produktowa": "pv",
		"utworzono": "2026-10-01 09:00:00",
		"zmodyfikowano": None,
		"zmodyfikowal": None,
		"linie": linie,
		"skladniki_marzy": [{"klucz": "narzut", "etykieta": "Narzut", "kwota": "1000.00"}],
		"dodatkowe": [],
		"podsumowanie": {
			"netto": "30000.00",
			"koszt_plan": "20000.00",
			"marza_plan": "10000.00",
			"prowizja_plan": None,
			"zysk_plan": "10000.00",
		},
		"podsumowanie_rzeczywiste": None,
	}


def _linia(snap: dict, klucz: str) -> dict:
	return next(linia for linia in snap["linie"] if linia["klucz"] == klucz)


class ZmienKosztyPlanowaneTest(unittest.TestCase):
	def test_zmiana_jednej_linii(self):
		snap = _pv_snapshot()
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13 000,50"}, None, T0, "adm")
		linia = _linia(nowy, "k_bateria")
		self.assertEqual(linia["koszt_plan"], "13000.50")
		self.assertEqual(linia["koszt_plan_pierwotny"], "12000.00")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "21000.50")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], "8999.50")
		self.assertEqual(nowy["podsumowanie"]["zysk_plan"], "8999.50")
		self.assertEqual(nowy["podsumowanie"]["netto"], "30000.00")
		self.assertNotIn("koszt_plan_pierwotny", _linia(nowy, "k_falownik"))
		self.assertEqual(nowy["zmodyfikowal"], "adm")

	def test_kilka_linii(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {"k_falownik": 4000, "k_montaz_pv": "3500"}, None, T0, "adm")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "19500.00")

	def test_przywrocenie_none(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, None, T0, "adm")
		p2 = zmien_koszty_planowane(p1, {"k_bateria": None}, None, T0, "adm")
		self.assertEqual(_linia(p2, "k_bateria")["koszt_plan"], "12000.00")
		self.assertNotIn("koszt_plan_pierwotny", _linia(p2, "k_bateria"))
		self.assertEqual(p2["podsumowanie"]["koszt_plan"], "20000.00")

	def test_none_dla_nigdy_niezmienianej_nic_nie_robi(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": None, "k_falownik": "6000"}, None, T0, "adm")
		self.assertEqual(_linia(nowy, "k_bateria"), _linia(_pv_snapshot(), "k_bateria"))
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "21000.00")

	def test_wartosc_rowna_pierwotnej_dziala_jak_przywrocenie(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, None, T0, "adm")
		p2 = zmien_koszty_planowane(p1, {"k_bateria": "12000"}, None, T0, "adm")
		self.assertNotIn("koszt_plan_pierwotny", _linia(p2, "k_bateria"))
		self.assertEqual(p2["podsumowanie"]["koszt_plan"], "20000.00")

	def test_pierwotny_nie_jest_nadpisywany_przy_kolejnej_zmianie(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, None, T0, "adm")
		p2 = zmien_koszty_planowane(p1, {"k_bateria": "14000"}, None, T0, "adm")
		self.assertEqual(_linia(p2, "k_bateria")["koszt_plan_pierwotny"], "12000.00")
		self.assertEqual(p2["podsumowanie"]["koszt_plan"], "22000.00")

	def test_suma_wyzsza_daje_dodatnia_korekte(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {}, "21 500", T0, "adm")
		korekta = _linia(nowy, "korekta_sumy_plan")
		self.assertEqual(korekta["koszt_plan"], "1500.00")
		self.assertEqual(korekta["etykieta"], "Korekta sumy kosztów planowanych")
		for pole in ("ilosc", "jednostka", "netto", "prowizja_plan", "koszt_rzeczywisty"):
			self.assertIsNone(korekta[pole])
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "21500.00")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], "8500.00")

	def test_suma_nizsza_daje_ujemna_korekte(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {}, "18000", T0, "adm")
		self.assertEqual(_linia(nowy, "korekta_sumy_plan")["koszt_plan"], "-2000.00")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "18000.00")

	def test_suma_rowna_sumie_linii_nie_tworzy_korekty(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, "21000", T0, "adm")
		self.assertFalse([l for l in nowy["linie"] if l["klucz"] == "korekta_sumy_plan"])

	def test_zmiana_linii_i_sumy_wygrywa_suma(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, "20500", T0, "adm")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "20500.00")
		self.assertEqual(_linia(nowy, "korekta_sumy_plan")["koszt_plan"], "-500.00")

	def test_zmiana_linii_przy_istniejacej_korekcie_zostawia_korekte(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {}, "21500", T0, "adm")
		p2 = zmien_koszty_planowane(p1, {"k_bateria": "13000"}, None, T0, "adm")
		self.assertEqual(_linia(p2, "korekta_sumy_plan")["koszt_plan"], "1500.00")
		self.assertEqual(p2["podsumowanie"]["koszt_plan"], "22500.00")

	def test_ponowna_suma_przy_istniejacej_korekcie_przelicza_korekte(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {}, "21500", T0, "adm")
		p2 = zmien_koszty_planowane(p1, {}, "20000", T0, "adm")
		self.assertFalse([l for l in p2["linie"] if l["klucz"] == "korekta_sumy_plan"])
		p3 = zmien_koszty_planowane(p1, {}, "23000", T0, "adm")
		self.assertEqual(_linia(p3, "korekta_sumy_plan")["koszt_plan"], "3000.00")

	def test_none_na_kluczu_korekty_usuwa_korekte(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {}, "21500", T0, "adm")
		p2 = zmien_koszty_planowane(p1, {"korekta_sumy_plan": None}, None, T0, "adm")
		self.assertFalse([l for l in p2["linie"] if l["klucz"] == "korekta_sumy_plan"])
		self.assertEqual(p2["podsumowanie"]["koszt_plan"], "20000.00")

	def test_kwota_na_kluczu_korekty_odrzucona(self):
		with self.assertRaises(ValueError):
			zmien_koszty_planowane(_pv_snapshot(), {"korekta_sumy_plan": "100"}, None, T0, "adm")

	def test_snapshot_oze(self):
		snap = _snapshot_oze()
		klucz = snap["linie"][0]["klucz"]
		przed = Decimal(snap["podsumowanie"]["koszt_plan"])
		stary = Decimal(snap["linie"][0]["koszt_plan"])
		nowy = zmien_koszty_planowane(snap, {klucz: stary + 100}, None, T0, "adm")
		self.assertEqual(Decimal(nowy["podsumowanie"]["koszt_plan"]), przed + 100)
		self.assertEqual(nowy["linia_produktowa"], "oze")

	def test_cp_odrzucony(self):
		with self.assertRaisesRegex(ValueError, "Czystego Powietrza"):
			zmien_koszty_planowane(_snapshot(), {"pompa_ciepla": "1"}, None, T0, "adm")

	def test_pusty_snapshot_odrzucony(self):
		with self.assertRaises(ValueError):
			zmien_koszty_planowane(None, {}, None, T0, "adm")

	def test_nieznany_klucz(self):
		with self.assertRaisesRegex(ValueError, "Nieznana pozycja"):
			zmien_koszty_planowane(_pv_snapshot(), {"nie_ma": "1"}, None, T0, "adm")

	def test_kwoty_niepoprawne(self):
		for zla in ("-1", "abc", "", float("inf"), True, None.__class__):
			with self.assertRaises(ValueError):
				zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": zla}, None, T0, "adm")
		with self.assertRaises(ValueError):
			zmien_koszty_planowane(_pv_snapshot(), {}, "-5", T0, "adm")
		with self.assertRaises(ValueError):
			zmien_koszty_planowane(_pv_snapshot(), {}, "xyz", T0, "adm")

	def test_zachowuje_edycje_reczna(self):
		snap = aktualizuj_po_edycji_zestawu(_pv_snapshot(), "31000", "a@x.pl", T0, "p")
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13000"}, None, T0, "adm")
		self.assertEqual(nowy["edycja_reczna"], snap["edycja_reczna"])
		self.assertEqual(nowy["podsumowanie"]["netto"], "31000.00")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], str(Decimal("31000.00") - Decimal("21000.00")))

	def test_podsumowanie_rzeczywiste_przeliczane_gdy_istnialo(self):
		snap = scal_snapshot(_pv_snapshot(), {"k_falownik": "4000"}, [], T0, "adm")
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13000"}, None, T0, "adm")
		# falownik rzeczywisty 4000 + bateria wg planu 13000 + montaz 3000
		self.assertEqual(nowy["podsumowanie_rzeczywiste"]["koszt_rzeczywisty"], "20000.00")
		self.assertEqual(nowy["podsumowanie_rzeczywiste"]["marza_rzeczywista"], "10000.00")

	def test_brak_podsumowania_rzeczywistego_gdy_nie_istnialo(self):
		nowy = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, None, T0, "adm")
		self.assertIsNone(nowy["podsumowanie_rzeczywiste"])

	def test_zysk_z_prowizja(self):
		snap = _pv_snapshot()
		snap["podsumowanie"]["prowizja_plan"] = "500.00"
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13000"}, None, T0, "adm")
		self.assertEqual(nowy["podsumowanie"]["zysk_plan"], "8500.00")

	def test_stary_snapshot_z_suma_rozna_od_sumy_linii(self):
		snap = _pv_snapshot()
		snap["podsumowanie"]["koszt_plan"] = "20500.00"  # linie sumują się do 20000
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13000"}, None, T0, "adm")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "21500.00")  # delta, nie suma z linii
		nowy2 = zmien_koszty_planowane(snap, {"k_bateria": "13000"}, "21500", T0, "adm")
		self.assertFalse([l for l in nowy2["linie"] if l["klucz"] == "korekta_sumy_plan"])

	def test_edycja_planu_slad(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, None, T0, "a@x.pl")
		self.assertEqual(
			p1["edycja_planu"],
			{"kiedy": T0, "kto": "a@x.pl", "koszt_plan_przed": "20000.00", "koszt_plan_pierwotny": "20000.00"},
		)
		p2 = zmien_koszty_planowane(p1, {"k_bateria": "14000"}, None, "2026-11-14 10:00:00", "b@x.pl")
		self.assertEqual(p2["edycja_planu"]["koszt_plan_przed"], "21000.00")
		self.assertEqual(p2["edycja_planu"]["koszt_plan_pierwotny"], "20000.00")
		self.assertEqual(p2["edycja_planu"]["kto"], "b@x.pl")

	def test_nie_mutuje_wejscia(self):
		snap = _pv_snapshot()
		kopia = copy.deepcopy(snap)
		koszty = {"k_bateria": "13000"}
		nowy = zmien_koszty_planowane(snap, koszty, "25000", T0, "adm")
		self.assertEqual(snap, kopia)
		self.assertEqual(koszty, {"k_bateria": "13000"})
		self.assertIsNot(nowy["linie"], snap["linie"])

	def test_scal_snapshot_zachowuje_nowe_klucze(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, "25000", T0, "adm")
		po = scal_snapshot(p1, {"k_bateria": "12500"}, [], "2026-11-14", "adm")
		self.assertEqual(_linia(po, "k_bateria")["koszt_plan_pierwotny"], "12000.00")
		self.assertEqual(_linia(po, "k_bateria")["koszt_plan"], "13000.00")
		self.assertEqual(_linia(po, "korekta_sumy_plan")["koszt_plan"], "4000.00")
		self.assertEqual(po["edycja_planu"], p1["edycja_planu"])
		self.assertEqual(po["podsumowanie"]["koszt_plan"], "25000.00")
		# rzeczywiste: falownik 5000 + bateria 12500 + montaz 3000 + korekta 4000 (wg planu)
		self.assertEqual(po["podsumowanie_rzeczywiste"]["koszt_rzeczywisty"], "24500.00")

	def test_scal_snapshot_odrzuca_koszt_rzeczywisty_korekty(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {}, "25000", T0, "adm")
		with self.assertRaises(ValueError):
			scal_snapshot(p1, {"korekta_sumy_plan": "1"}, [], T0, "adm")
		ok = scal_snapshot(p1, {"korekta_sumy_plan": None}, [], T0, "adm")
		self.assertEqual(_linia(ok, "korekta_sumy_plan")["koszt_plan"], "5000.00")

	def test_aktualizuj_po_edycji_zestawu_zachowuje_nowe_klucze(self):
		p1 = zmien_koszty_planowane(_pv_snapshot(), {"k_bateria": "13000"}, "25000", T0, "adm")
		po = aktualizuj_po_edycji_zestawu(p1, "40000", "a@x.pl", T0, "")
		self.assertEqual(_linia(po, "k_bateria")["koszt_plan_pierwotny"], "12000.00")
		self.assertIn("korekta_sumy_plan", [l["klucz"] for l in po["linie"]])
		self.assertEqual(po["edycja_planu"], p1["edycja_planu"])
		self.assertEqual(po["podsumowanie"]["koszt_plan"], "25000.00")

	def test_policz_zmiany_planu(self):
		snap = _pv_snapshot()
		nowy = zmien_koszty_planowane(snap, {"k_bateria": "13000", "k_falownik": "5000"}, "21500", T0, "adm")
		# bateria zmieniona + korekta dodana (falownik bez zmiany)
		self.assertEqual(policz_zmiany_planu(snap, nowy), 2)
		self.assertEqual(policz_zmiany_planu(snap, snap), 0)


class ZmienKosztyPlanowaneOdrzucenieTest(unittest.TestCase):
	def test_brak_zmian_odrzucony(self):
		for koszty, suma in (({}, None), ({}, "20000"), ({"k_bateria": "12000"}, None), ({"k_bateria": None}, "20000.00")):
			with self.assertRaisesRegex(ValueError, "Brak zmian"):
				zmien_koszty_planowane(_pv_snapshot(), koszty, suma, T0, "adm")

	def test_none_na_nieistniejacej_korekcie_to_brak_zmian(self):
		with self.assertRaisesRegex(ValueError, "Brak zmian"):
			zmien_koszty_planowane(_pv_snapshot(), {"korekta_sumy_plan": None}, None, T0, "adm")

	def test_suma_ujemna_odrzucona(self):
		snap = zmien_koszty_planowane(_pv_snapshot(), {}, "100", T0, "adm")  # korekta -19900
		with self.assertRaisesRegex(ValueError, "nie może być ujemna"):
			zmien_koszty_planowane(
				snap, {"k_falownik": "0", "k_bateria": "0", "k_montaz_pv": "0"}, None, T0, "adm"
			)

	def test_czy_zmieniona_korekta(self):
		snap = _pv_snapshot()
		z_korekta = zmien_koszty_planowane(snap, {}, "21500", T0, "adm")
		inna = zmien_koszty_planowane(z_korekta, {}, "22000", T0, "adm")
		usunieta = zmien_koszty_planowane(z_korekta, {"korekta_sumy_plan": None}, None, T0, "adm")
		inna_linia = zmien_koszty_planowane(z_korekta, {"k_bateria": "13000"}, None, T0, "adm")
		self.assertTrue(czy_zmieniona_korekta(snap, z_korekta))
		self.assertTrue(czy_zmieniona_korekta(z_korekta, usunieta))
		self.assertTrue(czy_zmieniona_korekta(z_korekta, inna))
		self.assertFalse(czy_zmieniona_korekta(z_korekta, inna_linia))
		self.assertFalse(czy_zmieniona_korekta(snap, snap))


def _snap_marze() -> dict:
	snap = _pv_snapshot()
	snap["skladniki_marzy"] = [
		{"klucz": "marza_proenergy", "etykieta": "Marża ProEnergy", "kwota": "5000.00"},
		{"klucz": "narzut", "etykieta": "Narzut handlowca", "kwota": "1000.00"},
	]
	return snap


def _sk(snap: dict, klucz: str) -> dict:
	return next(sk for sk in snap["skladniki_marzy"] if sk["klucz"] == klucz)


class ZmienSkladnikiMarzyTest(unittest.TestCase):
	def test_zmiana_i_wartosc_pierwotna(self):
		nowy = zmien_skladniki_marzy(_snap_marze(), {"narzut": "1 500,50"}, T0, "adm")
		self.assertEqual(_sk(nowy, "narzut")["kwota"], "1500.50")
		self.assertEqual(_sk(nowy, "narzut")["kwota_pierwotna"], "1000.00")
		self.assertNotIn("kwota_pierwotna", _sk(nowy, "marza_proenergy"))
		self.assertEqual(nowy["edycja_marzy"], {"kiedy": T0, "kto": "adm"})
		self.assertEqual(nowy["zmodyfikowal"], "adm")

	def test_pierwotna_nie_nadpisywana(self):
		p1 = zmien_skladniki_marzy(_snap_marze(), {"narzut": "1500"}, T0, "adm")
		p2 = zmien_skladniki_marzy(p1, {"narzut": "2000"}, T0, "adm")
		self.assertEqual(_sk(p2, "narzut")["kwota_pierwotna"], "1000.00")
		self.assertEqual(_sk(p2, "narzut")["kwota"], "2000.00")

	def test_przywrocenie_none_i_rowna_pierwotnej(self):
		p1 = zmien_skladniki_marzy(_snap_marze(), {"narzut": "1500"}, T0, "adm")
		for wartosc in (None, "1000"):
			p2 = zmien_skladniki_marzy(p1, {"narzut": wartosc}, T0, "adm")
			self.assertEqual(_sk(p2, "narzut")["kwota"], "1000.00")
			self.assertNotIn("kwota_pierwotna", _sk(p2, "narzut"))

	def test_brak_zmian(self):
		with self.assertRaisesRegex(ValueError, "Brak zmian w składnikach marży."):
			zmien_skladniki_marzy(_snap_marze(), {"narzut": "1000"}, T0, "adm")
		with self.assertRaisesRegex(ValueError, "Brak zmian w składnikach marży."):
			zmien_skladniki_marzy(_snap_marze(), {"narzut": None}, T0, "adm")

	def test_nieznany_klucz(self):
		with self.assertRaisesRegex(ValueError, "Nieznany składnik marży: xx."):
			zmien_skladniki_marzy(_snap_marze(), {"xx": "1"}, T0, "adm")

	def test_kwota_ujemna_lub_smiec(self):
		for zla in ("-1", "abc", True):
			with self.assertRaises(ValueError):
				zmien_skladniki_marzy(_snap_marze(), {"narzut": zla}, T0, "adm")

	def test_cp_i_brak_snapshotu(self):
		snap = _snap_marze()
		snap["linia_produktowa"] = "cp"
		with self.assertRaisesRegex(ValueError, "Czystego Powietrza"):
			zmien_skladniki_marzy(snap, {"narzut": "1"}, T0, "adm")
		for pusty in (None, {}):
			with self.assertRaisesRegex(ValueError, "Brak snapshotu kosztów"):
				zmien_skladniki_marzy(pusty, {"narzut": "1"}, T0, "adm")

	def test_brak_mutacji_i_podsumowanie_nietkniete(self):
		snap = _snap_marze()
		kopia = copy.deepcopy(snap)
		nowy = zmien_skladniki_marzy(snap, {"narzut": "2000", "marza_proenergy": "100"}, T0, "adm")
		self.assertEqual(snap, kopia)
		self.assertEqual(nowy["podsumowanie"], kopia["podsumowanie"])
		self.assertEqual(nowy["linie"], kopia["linie"])
		self.assertEqual(nowy["dodatkowe"], kopia["dodatkowe"])
		self.assertEqual(nowy["podsumowanie_rzeczywiste"], kopia["podsumowanie_rzeczywiste"])

	def test_przezywa_inne_edycje(self):
		edytowany = zmien_skladniki_marzy(_snap_marze(), {"narzut": "1500"}, T0, "adm")
		po_planie = zmien_koszty_planowane(edytowany, {"k_bateria": "13000"}, None, T0, "adm")
		po_zestawie = aktualizuj_po_edycji_zestawu(edytowany, "31000", "adm", T0)
		po_kosztach = scal_snapshot(edytowany, {"k_bateria": "100"}, [], T0, "adm")
		for wynik in (po_planie, po_zestawie, po_kosztach):
			self.assertEqual(_sk(wynik, "narzut")["kwota"], "1500.00")
			self.assertEqual(_sk(wynik, "narzut")["kwota_pierwotna"], "1000.00")
			self.assertEqual(wynik["edycja_marzy"], {"kiedy": T0, "kto": "adm"})

	def test_policz_zmiany_i_nierozdzielona(self):
		snap = _snap_marze()
		nowy = zmien_skladniki_marzy(snap, {"narzut": "1500"}, T0, "adm")
		self.assertEqual(policz_zmiany_skladnikow(snap, nowy), 1)
		self.assertEqual(nierozdzielona_marza(snap), Decimal("4000.00"))
		self.assertEqual(nierozdzielona_marza(nowy), Decimal("3500.00"))


# ---------------------------------------------------------------------------
# Wspólny edytor zestawu, kosztów i marż (ops#340)
# ---------------------------------------------------------------------------


def _snap_ems() -> dict:
	"""PV: koszty 51921.00, marże 32000.00 (narzut 10000.00), netto 83921.00, bilans 0."""
	snap = _pv_snapshot()
	for linia, kwota in zip(snap["linie"], ("3251.00", "40000.00", "8670.00"), strict=True):
		linia["koszt_plan"] = kwota
	snap["skladniki_marzy"] = [
		{"klucz": "marza_proenergy", "etykieta": "Marza ProEnergy", "kwota": "11000.00"},
		{"klucz": "marza_sps", "etykieta": "Marza SPS", "kwota": "11000.00"},
		{"klucz": "narzut", "etykieta": "Narzut handlowca", "kwota": "10000.00"},
	]
	snap["podsumowanie"] = {
		"netto": "83921.00",
		"koszt_plan": "51921.00",
		"marza_plan": "32000.00",
		"prowizja_plan": None,
		"zysk_plan": "32000.00",
	}
	return snap


WIERSZE_EMS = [
	{"typ": "Falownik", "nazwa": "Sigen 8 kW"},
	{"typ": "Magazyn energii", "nazwa": "Sigen 12 kWh"},
	{"typ": "Montaż", "nazwa": "Montaż PV"},
	{"typ": "EMS Zeronest", "nazwa": "EMS z integratorem"},
]


def _linie_ems(**koszty) -> list[dict]:
	bazowe = {"k_falownik": ("3251.00", 0), "k_bateria": ("40000.00", 1), "k_montaz_pv": ("8670.00", 2)}
	wynik = []
	for klucz, (kwota, idx) in bazowe.items():
		wynik.append({"klucz": klucz, "etykieta": klucz, "koszt_plan": koszty.get(klucz, kwota), "wiersz": idx})
	return wynik


class EtykietaWyswietlanaTest(unittest.TestCase):
	def test_znane_klucze_dostaja_polskie_etykiety(self):
		self.assertEqual(etykieta_wyswietlana("k_montaz_pv", "Montaz PV"), "Montaż PV")
		self.assertEqual(etykieta_wyswietlana("k_ppoz", "Uzgodnienia PPOZ"), "Uzgodnienia PPOŻ")
		self.assertEqual(etykieta_wyswietlana("bonus_liderki", "Bonus liderki"), "Bonus liderski")
		self.assertEqual(etykieta_wyswietlana("marza_dodatki", "x"), "Marża dodatki")

	def test_nieznany_klucz_zwraca_zapisana_etykiete(self):
		self.assertEqual(etykieta_wyswietlana("pc_x:montaz", "Montaż (Pompa)"), "Montaż (Pompa)")
		self.assertEqual(etykieta_wyswietlana("r_1", None), "")


class DopasujLinieDoWierszyTest(unittest.TestCase):
	def test_pv_po_typie_i_montaz_po_nazwie(self):
		snap = _snap_ems()
		snap["linie"].append(
			{**snap["linie"][2], "klucz": "k_montaz_mag", "koszt_plan": "1000.00"}
		)
		wiersze = [
			{"typ": "Falownik", "nazwa": "F"},
			{"typ": "Montaż", "nazwa": "Montaż magazynu"},
			{"typ": "Montaż", "nazwa": "Montaż instalacji"},
			{"typ": "Magazyn energii", "nazwa": "B"},
		]
		self.assertEqual(
			dopasuj_linie_do_wierszy(wiersze, snap),
			{"k_falownik": 0, "k_montaz_mag": 1, "k_montaz_pv": 2, "k_bateria": 3},
		)

	def test_dwa_wiersze_tego_samego_typu_nie_sa_dopasowane_po_typie(self):
		snap = _snap_ems()
		wiersze = [{"typ": "Falownik", "nazwa": "A"}, {"typ": "Falownik", "nazwa": "B"}]
		self.assertEqual(dopasuj_linie_do_wierszy(wiersze, snap), {})

	def test_podpis_wygrywa_i_obsluguje_duplikaty_kolejno(self):
		snap = _snap_ems()
		snap["linie"][0]["wiersz"] = {"typ": "Falownik", "nazwa": "B"}
		snap["linie"][1]["wiersz"] = {"typ": "Falownik", "nazwa": "B"}
		wiersze = [{"typ": "Falownik", "nazwa": "B"}, {"typ": "Falownik", "nazwa": "B"}]
		self.assertEqual(dopasuj_linie_do_wierszy(wiersze, snap), {"k_falownik": 0, "k_bateria": 1})

	def test_oze_po_etykiecie_bez_wielkosci_liter(self):
		snap = zbuduj_snapshot_oze(WEWNETRZNE_OZE, "2026-01-01")
		wiersze = [{"typ": "Pompa ciepła", "nazwa": "BUFOR"}, {"typ": "X", "nazwa": "Inna"}]
		self.assertEqual(dopasuj_linie_do_wierszy(wiersze, snap), {"wspolne:bufor": 0})

	def test_linia_bez_dopasowania_i_brak_snapshotu(self):
		self.assertEqual(dopasuj_linie_do_wierszy([], _snap_ems()), {})
		self.assertEqual(dopasuj_linie_do_wierszy([{"typ": "Falownik", "nazwa": "F"}], None), {})

	def test_korekta_sumy_nie_jest_dopasowywana(self):
		snap = zmien_koszty_planowane(_snap_ems(), {}, "50000", T0, "adm")
		wynik = dopasuj_linie_do_wierszy([{"typ": "Falownik", "nazwa": "F"}], snap)
		self.assertNotIn("korekta_sumy_plan", wynik)


class ZmienPlanLacznyTest(unittest.TestCase):
	def _ems(self, **kw):
		snap = kw.pop("snap", None) or _snap_ems()
		linie = kw.pop("linie", None)
		if linie is None:
			linie = [*_linie_ems(), {"klucz": None, "etykieta": "EMS z integratorem", "koszt_plan": "3000.00", "wiersz": 3}]
		return zmien_plan_laczny(
			snap, linie, kw.pop("marze", {"narzut": "7000.00"}), WIERSZE_EMS, kw.pop("netto", "83921.00"), T0, "adm", "ems"
		)

	def test_przyklad_kontrolny_ems(self):
		snap = _snap_ems()
		kopia = copy.deepcopy(snap)
		nowy = self._ems(snap=snap)
		self.assertEqual(snap, kopia)  # wejście nie jest mutowane
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "54921.00")
		self.assertEqual(nowy["podsumowanie"]["netto"], "83921.00")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], "29000.00")
		self.assertEqual(_sk(nowy, "narzut")["kwota"], "7000.00")
		self.assertEqual(_sk(nowy, "narzut")["kwota_pierwotna"], "10000.00")
		self.assertEqual(
			bilans(nowy),
			{"netto": Decimal("83921.00"), "koszty": Decimal("54921.00"), "marze": Decimal("29000.00"), "roznica": Decimal("0.00")},
		)
		nowa = _linia(nowy, "r_1")
		self.assertTrue(nowa["reczna"])
		self.assertEqual(nowa["wiersz"], {"typ": "EMS Zeronest", "nazwa": "EMS z integratorem"})
		self.assertEqual(nowa["etykieta"], "EMS z integratorem")
		self.assertIsNone(nowa["koszt_rzeczywisty"])
		self.assertNotIn("edycja_reczna", nowy)  # netto bez zmian
		self.assertEqual(nowy["edycja_planu"]["koszt_plan_pierwotny"], "51921.00")
		self.assertEqual(nowy["edycja_marzy"], {"kiedy": T0, "kto": "adm"})
		self.assertTrue(czy_zmieniony_plan(snap, nowy))

	def test_zmiana_kosztu_linii_katalogowej_zapamietuje_pierwotny(self):
		linie = _linie_ems(k_falownik="4000.00")
		nowy = self._ems(linie=linie, marze={})
		self.assertEqual(_linia(nowy, "k_falownik")["koszt_plan"], "4000.00")
		self.assertEqual(_linia(nowy, "k_falownik")["koszt_plan_pierwotny"], "3251.00")
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "52670.00")
		wrot = self._ems(snap=nowy, linie=_linie_ems(), marze={})
		self.assertNotIn("koszt_plan_pierwotny", _linia(wrot, "k_falownik"))

	def test_linia_katalogowa_nieobecna_zostaje_z_zerem(self):
		linie = [l for l in _linie_ems() if l["klucz"] != "k_montaz_pv"]
		nowy = self._ems(linie=linie, marze={})
		self.assertEqual(_linia(nowy, "k_montaz_pv")["koszt_plan"], "0.00")
		self.assertEqual(_linia(nowy, "k_montaz_pv")["koszt_plan_pierwotny"], "8670.00")
		self.assertIsNone(_linia(nowy, "k_montaz_pv")["wiersz"])
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "43251.00")

	def test_linia_reczna_nieobecna_jest_usuwana(self):
		z_ems = self._ems()
		bez = self._ems(snap=z_ems, linie=_linie_ems(), marze={})
		self.assertNotIn("r_1", [l["klucz"] for l in bez["linie"]])
		self.assertEqual(bez["podsumowanie"]["koszt_plan"], "51921.00")

	def test_linia_reczna_z_kosztem_rzeczywistym_blokuje_usuniecie(self):
		z_ems = self._ems()
		_linia(z_ems, "r_1")["koszt_rzeczywisty"] = "2900.00"
		with self.assertRaisesRegex(ValueError, "Najpierw usuń koszt rzeczywisty pozycji: EMS z integratorem."):
			self._ems(snap=z_ems, linie=_linie_ems(), marze={})

	def test_edycja_linii_recznej_zmienia_etykiete_i_koszt(self):
		z_ems = self._ems()
		linie = [*_linie_ems(), {"klucz": "r_1", "etykieta": "EMS v2", "koszt_plan": "2500.00", "wiersz": None}]
		nowy = self._ems(snap=z_ems, linie=linie, marze={})
		self.assertEqual(_linia(nowy, "r_1")["etykieta"], "EMS v2")
		self.assertIsNone(_linia(nowy, "r_1")["wiersz"])
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "54421.00")

	def test_klucz_nowej_linii_jest_unikalny(self):
		z_ems = self._ems()
		linie = [
			*_linie_ems(),
			{"klucz": "r_1", "etykieta": "EMS", "koszt_plan": "3000.00", "wiersz": 3},
			{"klucz": None, "etykieta": "Drugi", "koszt_plan": "100.00", "wiersz": None},
		]
		nowy = self._ems(snap=z_ems, linie=linie, marze={})
		self.assertEqual([l["klucz"] for l in nowy["linie"]][-2:], ["r_1", "r_2"])

	def test_pusta_etykieta_przy_powiazaniu_bierze_nazwe_wiersza(self):
		linie = [*_linie_ems(), {"klucz": None, "etykieta": "  ", "koszt_plan": "10.00", "wiersz": 3}]
		nowy = self._ems(linie=linie, marze={})
		self.assertEqual(_linia(nowy, "r_1")["etykieta"], "EMS z integratorem")

	def test_pusta_etykieta_bez_wiersza_to_blad(self):
		linie = [*_linie_ems(), {"klucz": None, "etykieta": "", "koszt_plan": "10.00", "wiersz": None}]
		with self.assertRaisesRegex(ValueError, "Podaj nazwę kosztu"):
			self._ems(linie=linie, marze={})

	def test_korekta_sumy(self):
		snap = zmien_koszty_planowane(_snap_ems(), {}, "50000", T0, "adm")
		kor = _linia(snap, "korekta_sumy_plan")["koszt_plan"]
		obecna = [*_linie_ems(), {"klucz": "korekta_sumy_plan", "etykieta": "x", "koszt_plan": kor, "wiersz": None}]
		bez_zmian = self._ems(snap=snap, linie=obecna, marze={})
		self.assertEqual(_linia(bez_zmian, "korekta_sumy_plan")["koszt_plan"], kor)
		with self.assertRaisesRegex(ValueError, "Kwoty korekty"):
			zmieniona = [dict(l, koszt_plan="1.00") if l["klucz"] == "korekta_sumy_plan" else l for l in obecna]
			self._ems(snap=snap, linie=zmieniona, marze={})
		usunieta = self._ems(snap=snap, linie=_linie_ems(), marze={})
		self.assertNotIn("korekta_sumy_plan", [l["klucz"] for l in usunieta["linie"]])
		self.assertEqual(usunieta["podsumowanie"]["koszt_plan"], "51921.00")

	def test_zmiana_netto_ustawia_edycje_reczna_i_marze(self):
		nowy = self._ems(linie=_linie_ems(), marze={}, netto="90000.00")
		self.assertEqual(nowy["podsumowanie"]["netto"], "90000.00")
		self.assertEqual(nowy["podsumowanie"]["marza_plan"], "38079.00")
		self.assertEqual(nowy["edycja_reczna"]["netto_pierwotne"], "83921.00")
		self.assertEqual(nowy["edycja_reczna"]["powod"], "ems")
		self.assertNotIn("edycja_planu", nowy)
		self.assertNotIn("edycja_marzy", nowy)

	def test_oznacz_edycje_stempluje_przy_niezmienionej_cenie(self):
		def wywolaj(snap, **kw):
			return zmien_plan_laczny(
				snap, _linie_ems(), {"narzut": "9000.00"}, WIERSZE_EMS, None, T0, "adm", "  powod 1 ", **kw
			)

		pierwszy = wywolaj(_snap_ems(), oznacz_edycje=True)
		er = pierwszy["edycja_reczna"]
		self.assertEqual((er["kiedy"], er["kto"], er["powod"]), (T0, "adm", "powod 1"))
		self.assertEqual(er["netto_przed"], "83921.00")
		self.assertEqual(er["netto_pierwotne"], "83921.00")
		self.assertEqual(pierwszy["zmodyfikowal"], "adm")
		drugi = zmien_plan_laczny(
			pierwszy, _linie_ems(), {"narzut": "8000.00"}, WIERSZE_EMS, "90000.00", T0, "adm", "p2", oznacz_edycje=True
		)
		self.assertEqual(drugi["edycja_reczna"]["netto_pierwotne"], "83921.00")
		self.assertEqual(drugi["edycja_reczna"]["netto_przed"], "83921.00")
		trzeci = zmien_plan_laczny(
			drugi, _linie_ems(), {}, WIERSZE_EMS, None, T0, "adm", "p3", oznacz_edycje=True
		)
		self.assertEqual(trzeci["edycja_reczna"]["netto_pierwotne"], "83921.00")
		self.assertEqual(trzeci["edycja_reczna"]["netto_przed"], "90000.00")

	def test_bez_oznacz_edycje_cena_bez_zmian_nie_dodaje_edycji_recznej(self):
		nowy = zmien_plan_laczny(_snap_ems(), _linie_ems(), {"narzut": "9000.00"}, WIERSZE_EMS, None, T0, "adm", "x")
		self.assertNotIn("edycja_reczna", nowy)

	def test_netto_none_zostawia_cene(self):
		nowy = self._ems(netto=None)
		self.assertEqual(nowy["podsumowanie"]["netto"], "83921.00")

	def test_brak_zmian_nie_jest_bledem(self):
		snap = _snap_ems()
		nowy = self._ems(snap=snap, linie=_linie_ems(), marze={})
		self.assertFalse(czy_zmieniony_plan(snap, nowy))
		self.assertNotIn("edycja_planu", nowy)
		self.assertNotIn("edycja_marzy", nowy)
		self.assertIsNone(nowy["zmodyfikowano"])

	def test_podsumowanie_rzeczywiste_tylko_gdy_istnialo(self):
		self.assertIsNone(self._ems()["podsumowanie_rzeczywiste"])
		snap = scal_snapshot(_snap_ems(), {"k_falownik": "100"}, [], T0, "adm")
		nowy = self._ems(snap=snap)
		self.assertIsNotNone(nowy["podsumowanie_rzeczywiste"])

	def test_sumuje_od_poprzedniej_sumy_nie_od_zera(self):
		snap = _snap_ems()
		snap["podsumowanie"]["koszt_plan"] = "60000.00"  # stara suma różna od sumy linii
		nowy = self._ems(snap=snap)
		self.assertEqual(nowy["podsumowanie"]["koszt_plan"], "63000.00")

	def test_walidacje(self):
		przypadki = [
			(dict(linie=[{"klucz": "k_nieznany", "etykieta": "", "koszt_plan": "1", "wiersz": None}]), "Nieznana pozycja"),
			(dict(linie=[*_linie_ems(), {"klucz": None, "etykieta": "a", "koszt_plan": "1", "wiersz": 9}]), "nieistniejącą pozycję"),
			(dict(linie=[*_linie_ems(), {"klucz": None, "etykieta": "a", "koszt_plan": "1", "wiersz": 0}]), "tę samą pozycję"),
			(dict(linie=_linie_ems(k_falownik="-5")), "Nieprawidłowa kwota"),
			(dict(marze={"narzut": "-1"}), "Nieprawidłowa kwota"),
			(dict(marze={"nie_ma": "1"}), "Nieznany składnik marży"),
			(dict(linie=[dict(l, koszt_plan="0") for l in _linie_ems()], netto="1"), None),
		]
		for kw, wzorzec in przypadki:
			if wzorzec is None:
				continue
			with self.subTest(wzorzec=wzorzec), self.assertRaisesRegex(ValueError, wzorzec):
				self._ems(**kw)

	def test_cp_i_brak_snapshotu(self):
		with self.assertRaisesRegex(ValueError, "Brak snapshotu"):
			zmien_plan_laczny(None, [], {}, [], None, T0, "adm")
		cp = _snap_ems()
		cp["linia_produktowa"] = "cp"
		with self.assertRaisesRegex(ValueError, "Czystego Powietrza"):
			zmien_plan_laczny(cp, [], {}, [], None, T0, "adm")

	def test_snapshot_oze_dopasowanie_po_etykiecie_przy_zapisie(self):
		snap = zbuduj_snapshot_oze(WEWNETRZNE_OZE, "2026-01-01")
		wiersze = [{"typ": "Pompa ciepła", "nazwa": "Bufor"}]
		linie = [dict(klucz=l["klucz"], etykieta=l["etykieta"], koszt_plan=l["koszt_plan"], wiersz=None) for l in snap["linie"]]
		linie[1]["wiersz"] = 0
		nowy = zmien_plan_laczny(snap, linie, {}, wiersze, None, T0, "adm")
		self.assertEqual(_linia(nowy, "wspolne:bufor")["wiersz"], {"typ": "Pompa ciepła", "nazwa": "Bufor"})
		self.assertEqual(dopasuj_linie_do_wierszy(wiersze, nowy), {"wspolne:bufor": 0})

	def test_edycje_przezywaja_scal_snapshot(self):
		nowy = self._ems()
		po_kosztach = scal_snapshot(nowy, {"k_falownik": "100"}, [], T0, "adm")
		self.assertTrue(_linia(po_kosztach, "r_1")["reczna"])
		self.assertEqual(_linia(po_kosztach, "r_1")["wiersz"], {"typ": "EMS Zeronest", "nazwa": "EMS z integratorem"})
		self.assertEqual(_linia(po_kosztach, "k_falownik")["wiersz"], {"typ": "Falownik", "nazwa": "Sigen 8 kW"})
		self.assertNotIn("reczna", _linia(po_kosztach, "k_falownik"))


class WidokKosztowTest(unittest.TestCase):
	def test_ksztalt_zgodny_z_kontraktem(self):
		snap = _snap_ems()
		widok = widok_kosztow(snap, WIERSZE_EMS[:3], True)
		self.assertEqual(
			widok["linie"][0],
			{
				"klucz": "k_falownik",
				"etykieta": "Falownik",
				"koszt_plan": "3251.00",
				"koszt_plan_pierwotny": None,
				"koszt_rzeczywisty": None,
				"wiersz": 0,
				"reczna": False,
				"korekta": False,
			},
		)
		self.assertEqual(widok["linie"][2]["etykieta"], "Montaż PV")
		self.assertEqual(widok["skladniki_marzy"][2], {"klucz": "narzut", "etykieta": "Narzut handlowca", "kwota": "10000.00", "kwota_pierwotna": None})
		self.assertEqual(widok["podsumowanie"], {"netto": "83921.00", "koszt_plan": "51921.00", "marza_plan": "32000.00"})
		self.assertEqual(widok["rozliczenie_handlowca"], {"naliczone": True})

	def test_none_gdy_brak_snapshotu_lub_cp(self):
		self.assertIsNone(widok_kosztow(None, []))
		cp = _snap_ems()
		cp["linia_produktowa"] = "cp"
		self.assertIsNone(widok_kosztow(cp, []))

	def test_korekta_i_reczna_oznaczone(self):
		snap = zmien_koszty_planowane(_snap_ems(), {}, "50000", T0, "adm")
		widok = widok_kosztow(snap, [])
		self.assertTrue(next(l for l in widok["linie"] if l["korekta"])["klucz"] == "korekta_sumy_plan")
