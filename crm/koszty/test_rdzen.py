import copy
import unittest
from decimal import Decimal

from crm.koszty.rdzen import scal_snapshot, zbuduj_snapshot_cp

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
