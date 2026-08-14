import copy
import unittest
from datetime import date
from decimal import Decimal
from typing import Any

from crm.volteo_umowa_pdf import POLA_KOMPONENTU, zbuduj_kontekst

_PLACEHOLDER_PRODUCENT = "PLACEHOLDER — do uzupelnienia (dokumentacja producenta modulu PV)"
_PLACEHOLDER_MODEL = "PLACEHOLDER — do uzupelnienia (model modulu PV)"
_DZIS = date(2026, 8, 6)


def _umowa(**nadpisania: Any) -> dict[str, Any]:
	"""Kompletny, "roboczo wypełniony" formularz `Volteo Umowa` — baza do modyfikacji w testach."""
	baza: dict[str, Any] = {
		"adres_zam_jak_montaz": "Nie",
		"adres_zam_ulica": "Kwiatowa",
		"adres_zam_nr_domu": "5",
		"adres_zam_nr_mieszkania": "",
		"adres_zam_kod": "00-001",
		"adres_zam_miasto": "Warszawa",
		"adres_montaz_ulica": "Polna",
		"adres_montaz_nr_domu": "10",
		"adres_montaz_nr_mieszkania": "",
		"adres_montaz_kod": "02-002",
		"adres_montaz_miasto": "Kraków",
		"typ_budynku": "Jednorodzinny",
		"powierzchnia_prog": "do 300 m²",
		"powierzchnia_m2": Decimal("150"),
		"finansowanie": "Gotówka 100%",
		"wklad_wlasny_pln": Decimal("0"),
		"kwota_kredytu_pln": Decimal("0"),
		"internet": "Wi-Fi",
		"instalacja_odgromowa": "Nie",
		"moc_przylaczeniowa_kw": Decimal("8.5"),
		"liczba_faz": "3",
		"przekop_gruntowy": "Nie",
		"dodatkowy_kabel_m": 0,
		"ppoz_wymagane": 0,
		"istniejaca_pv": "Nie",
		"istniejaca_pv_moc_inwertera_kw": Decimal("0"),
		"istniejaca_pv_moc_kwp": Decimal("0"),
		"istniejaca_pv_producent_inwertera": "",
		"zgoda_kontakt_telefoniczny": 0,
		"zgoda_dzialania_promocyjne": 0,
		"zgoda_realizacja_przed_odstapieniem": 0,
	}
	baza.update(nadpisania)
	return baza


def _deal(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"name": "PRO/PVME/26/1000",
		"deal_value": Decimal("43454.88"),
		"custom_netto": Decimal("40236.0"),
		"custom_pv_power_kwp": Decimal("5.0"),
		"custom_panele": 10,
		"custom_falownik": "Sigenergy TP2 6 kW",
		"custom_bateria": "Sigenergy 12 kWh (6+6)",
		"custom_pojemnosc_kwh": Decimal("12.0"),
		"custom_konstrukcja": "Dach skośny - blacha",
		"custom_install_address": "",
		"custom_install_city": "",
		"custom_install_postal_code": "",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"first_name": "Jan",
		"last_name": "Kowalski",
		"custom_pesel": "90010112345",
		"mobile_no": "500600700",
		"email": "jan@example.com",
	}
	baza.update(nadpisania)
	return baza


def _zestaw() -> list[dict[str, Any]]:
	return [
		{"typ": "Falownik", "nazwa": "Sigenergy TP2 6 kW", "ilosc": 1},
		{"typ": "Panele PV", "nazwa": "Panel PV", "ilosc": 10},
	]


def _komponenty() -> list[dict[str, Any]]:
	return [
		{
			"kategoria": "Falownik",
			"nazwa": "Sigenergy",
			"model": "TP2 6 kW",
			"producent": "Sigenergy",
			"moc_kw": Decimal("6.0"),
			"gwarancja_lat": 0,
		},
		{
			"kategoria": "Magazyn energii",
			"nazwa": "Sigenergy",
			"model": "12 kWh (6+6)",
			"producent": "Sigenergy",
			"moc_kw": Decimal("0.0"),
			"pojemnosc_kwh": Decimal("12"),
			"gwarancja_lat": 0,
		},
	]


def _panel_komponent(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"kategoria": "Panel PV",
		"nazwa": "JA Solar",
		"model": "JAM54S31 425/MR",
		"producent": "JA Solar",
		"moc_wp": 425,
		"gwarancja_tekst": "25/30",
	}
	baza.update(nadpisania)
	return baza


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"panel_producent": _PLACEHOLDER_PRODUCENT,
		"panel_model": _PLACEHOLDER_MODEL,
		"panel_moc_wp": 0,
		# Data (tekstowe), nie Int — "nigdy nie ustawiono" odpowiada None, tak
		# jak faktycznie zwraca `frappe.db.get_singles_dict` dla pustego pola
		# tekstowego (w przeciwienstwie do Int/Currency, gdzie puste czyta się
		# jako 0). Patrz `crm.api.umowa`, gdzie `stale` jest budowane właśnie z
		# `get_singles_dict`.
		"panel_gwarancja_lat": None,
	}
	baza.update(nadpisania)
	return baza


def _kontekst(**nadpisania_umowa: Any) -> dict[str, Any]:
	"""Skrót: buduje kontekst z bazowych fixture'ów, z opcjonalnymi nadpisaniami `umowa`."""
	return zbuduj_kontekst(
		_umowa(**nadpisania_umowa), _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS
	)


class TestZeroZnaczyPustke(unittest.TestCase):
	def test_a_gwarancja_zero_nie_jest_zero_lat(self: "TestZeroZnaczyPustke") -> None:
		# panel_gwarancja_lat jest teraz polem tekstowym (Data), nie Int — jego
		# semantyka "puste znaczy puste" jest pokryta osobno przez
		# TestPanelGwarancjaTekst. inwerter/bateria zostaja tutaj bez zmian:
		# to wciaz pola Int na Volteo Komponent, gdzie 0 nie moze wydrukowac
		# sie jako "0 lat".
		kontekst = _kontekst()
		self.assertEqual(kontekst["inwerter_gwarancja_lat"], "")
		self.assertEqual(kontekst["bateria_gwarancja_lat"], "")

	def test_b_moc_string_zero(self: "TestZeroZnaczyPustke") -> None:
		deal = _deal(custom_pv_power_kwp="0")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["moc_pv_kwp"], "")

	def test_c_moc_string_sama_spacja(self: "TestZeroZnaczyPustke") -> None:
		deal = _deal(custom_pv_power_kwp=" ")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["moc_pv_kwp"], "")

	def test_d_moc_bateria_zero_bo_katalog_nie_ma_danych(self: "TestZeroZnaczyPustke") -> None:
		# Stan faktyczny katalogu (moc_kw = 0.0 we wszystkich magazynach energii)
		# — musi wyjść pusto, nie "0".
		kontekst = _kontekst()
		self.assertEqual(kontekst["bateria_moc_kw"], "")

	def test_e_kwoty_zero_tez_sa_puste(self: "TestZeroZnaczyPustke") -> None:
		kontekst = _kontekst(wklad_wlasny_pln=Decimal("0"), kwota_kredytu_pln=Decimal("0"))
		self.assertEqual(kontekst["wklad_wlasny"], "")
		self.assertEqual(kontekst["kwota_kredytu"], "")

	def test_f_powierzchnia_zero_jest_pusta(self: "TestZeroZnaczyPustke") -> None:
		kontekst = _kontekst(powierzchnia_m2=Decimal("0"))
		self.assertEqual(kontekst["powierzchnia_m2"], "")

	def test_g_sztuki_zero_sa_puste(self: "TestZeroZnaczyPustke") -> None:
		deal = _deal(custom_panele=0)
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["panel_szt"], "")


class TestPlaceholder(unittest.TestCase):
	def test_a_panel_producent_model_placeholder_jest_pusty(self: "TestPlaceholder") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["panel_producent_model"], "")

	def test_b_placeholder_wykrywany_niezaleznie_od_wielkosci_liter(self: "TestPlaceholder") -> None:
		stale = _stale(panel_producent="placeholder — coś tam", panel_model="")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), stale, _DZIS)
		self.assertEqual(kontekst["panel_producent_model"], "")

	def test_c_jeden_z_pary_placeholder_drugi_prawdziwy(self: "TestPlaceholder") -> None:
		stale = _stale(panel_producent="JA Solar", panel_model=_PLACEHOLDER_MODEL)
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), stale, _DZIS)
		self.assertEqual(kontekst["panel_producent_model"], "JA Solar")

	def test_d_niepowiazane_pole_placeholder_tez_znika(self: "TestPlaceholder") -> None:
		kontekst = _kontekst(istniejaca_pv_producent_inwertera="PLACEHOLDER cokolwiek")
		self.assertEqual(kontekst["ist_pv_producent_inwertera"], "")


class TestPanelGwarancjaTekst(unittest.TestCase):
	"""panel_gwarancja_lat stało się polem tekstowym (Data) — nosi teraz DWIE
	gwarancje w jednym wpisie (np. "25/30": produktowa/liniowa mocy), więc
	zamiast `_liczba_calkowita` przechodzi przez `_tekst`. Kontrakt `_tekst`:
	`None` → "", placeholder → "", realna wartość przechodzi bez zmian."""

	def test_a_puste_daje_pusty_string(self: "TestPanelGwarancjaTekst") -> None:
		stale = _stale(panel_gwarancja_lat=None)
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), stale, _DZIS)
		self.assertEqual(kontekst["panel_gwarancja_lat"], "")

	def test_b_placeholder_daje_pusty_string(self: "TestPanelGwarancjaTekst") -> None:
		stale = _stale(panel_gwarancja_lat="placeholder — do uzupelnienia")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), stale, _DZIS)
		self.assertEqual(kontekst["panel_gwarancja_lat"], "")

	def test_c_realna_wartosc_przechodzi_bez_zmian(self: "TestPanelGwarancjaTekst") -> None:
		stale = _stale(panel_gwarancja_lat="25/30")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), stale, _DZIS)
		self.assertEqual(kontekst["panel_gwarancja_lat"], "25/30")


class TestFinansowanie(unittest.TestCase):
	def test_a_kredyt_100(self: "TestFinansowanie") -> None:
		kontekst = _kontekst(finansowanie="Kredyt 100%")
		self.assertTrue(kontekst["fin_kredyt_100"])
		self.assertFalse(kontekst["fin_kredyt_wklad"])
		self.assertFalse(kontekst["fin_gotowka"])

	def test_b_kredyt_plus_gotowka(self: "TestFinansowanie") -> None:
		kontekst = _kontekst(finansowanie="Kredyt + gotówka")
		self.assertFalse(kontekst["fin_kredyt_100"])
		self.assertTrue(kontekst["fin_kredyt_wklad"])
		self.assertFalse(kontekst["fin_gotowka"])

	def test_c_gotowka_100(self: "TestFinansowanie") -> None:
		kontekst = _kontekst(finansowanie="Gotówka 100%")
		self.assertFalse(kontekst["fin_kredyt_100"])
		self.assertFalse(kontekst["fin_kredyt_wklad"])
		self.assertTrue(kontekst["fin_gotowka"])

	def test_d_nieznane_lub_puste_wszystkie_false(self: "TestFinansowanie") -> None:
		for wartosc in (None, "", "Coś innego"):
			with self.subTest(wartosc=wartosc):
				kontekst = _kontekst(finansowanie=wartosc)
				self.assertFalse(kontekst["fin_kredyt_100"])
				self.assertFalse(kontekst["fin_kredyt_wklad"])
				self.assertFalse(kontekst["fin_gotowka"])


class TestKonstrukcja(unittest.TestCase):
	def test_a_dach_skosny_blacha(self: "TestKonstrukcja") -> None:
		deal = _deal(custom_konstrukcja="Dach skośny - blacha")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertTrue(kontekst["montaz_dach"])
		self.assertFalse(kontekst["montaz_grunt"])
		self.assertEqual(kontekst["pokrycie_dachowe"], "Blacha")

	def test_b_konstrukcja_gruntowa(self: "TestKonstrukcja") -> None:
		deal = _deal(custom_konstrukcja="Konstrukcja gruntowa")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["montaz_dach"])
		self.assertTrue(kontekst["montaz_grunt"])
		self.assertEqual(kontekst["pokrycie_dachowe"], "")

	def test_c_nieznana_konstrukcja_oba_false(self: "TestKonstrukcja") -> None:
		deal = _deal(custom_konstrukcja="Coś nieznanego")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["montaz_dach"])
		self.assertFalse(kontekst["montaz_grunt"])
		self.assertEqual(kontekst["pokrycie_dachowe"], "")


class TestFormatowanieKwoty(unittest.TestCase):
	def test_a_kwota_z_tysiacami(self: "TestFormatowanieKwoty") -> None:
		deal = _deal(custom_netto=Decimal("40236.0"))
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "40 236,00")

	def test_b_kwota_ponizej_tysiaca_bez_separatora(self: "TestFormatowanieKwoty") -> None:
		deal = _deal(custom_netto=Decimal("999.5"))
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "999,50")

	def test_c_kwota_miliony_dwie_grupy_separatora(self: "TestFormatowanieKwoty") -> None:
		deal = _deal(custom_netto=Decimal("1234567.89"))
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "1 234 567,89")

	def test_d_moc_bez_zbednych_zer(self: "TestFormatowanieKwoty") -> None:
		self.assertEqual(
			zbuduj_kontekst(
				_umowa(),
				_deal(custom_pv_power_kwp=Decimal("5.0")),
				_kontakt(),
				_zestaw(),
				_komponenty(),
				_stale(),
				_DZIS,
			)["moc_pv_kwp"],
			"5",
		)
		self.assertEqual(
			zbuduj_kontekst(
				_umowa(),
				_deal(custom_pv_power_kwp=Decimal("4.5")),
				_kontakt(),
				_zestaw(),
				_komponenty(),
				_stale(),
				_DZIS,
			)["moc_pv_kwp"],
			"4,5",
		)


class TestDopasowanieKomponentu(unittest.TestCase):
	def test_a_falownik_dopasowany_po_sklejonej_nazwie(self: "TestDopasowanieKomponentu") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["inwerter_moc_kw"], "6")
		self.assertEqual(kontekst["inwerter_szt"], "1")

	def test_b_kategoria_inwerter_nie_pasuje_musi_byc_falownik(self: "TestDopasowanieKomponentu") -> None:
		komponenty = [
			{
				"kategoria": "Inwerter",  # celowo zła kategoria — w katalogu jej nie ma
				"nazwa": "Sigenergy",
				"model": "TP2 6 kW",
				"moc_kw": Decimal("6.0"),
				"gwarancja_lat": 10,
			}
		]
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		self.assertEqual(kontekst["inwerter_moc_kw"], "")
		self.assertEqual(kontekst["inwerter_gwarancja_lat"], "")

	def test_c_brak_dopasowania_gdy_falownik_nieznany(self: "TestDopasowanieKomponentu") -> None:
		deal = _deal(custom_falownik="Coś czego nie ma w katalogu")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["inwerter_moc_kw"], "")
		self.assertEqual(kontekst["inwerter_szt"], "")
		self.assertEqual(kontekst["inwerter_producent_model"], "Coś czego nie ma w katalogu")

	def test_d_brak_falownika_na_deal_nic_sie_nie_wywraca(self: "TestDopasowanieKomponentu") -> None:
		deal = _deal(custom_falownik=None)
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["inwerter_moc_kw"], "")
		self.assertEqual(kontekst["inwerter_szt"], "")
		self.assertEqual(kontekst["inwerter_producent_model"], "")


class TestPanelZDeal(unittest.TestCase):
	@staticmethod
	def _kontekst_panel(card: dict[str, Any], custom_panel: Any) -> dict[str, Any]:
		deal = _deal(custom_panel=custom_panel)
		return zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), [card], _stale(), _DZIS)

	def test_a_dane_panelu_z_karty_deala(self: "TestPanelZDeal") -> None:
		card = _panel_komponent()
		custom_panel = f"{card['nazwa']} {card['model']}"
		kontekst = self._kontekst_panel(card, custom_panel)
		self.assertEqual(kontekst["panel_producent_model"], custom_panel)
		self.assertEqual(kontekst["panel_moc_wp"], "425")
		self.assertEqual(kontekst["panel_gwarancja_lat"], "25/30")

	def test_b_puste_lub_brakujace_custom_panel_zostawia_stale(self: "TestPanelZDeal") -> None:
		stale = _stale(panel_producent="Trina", panel_model="Vertex S+", panel_moc_wp=435, panel_gwarancja_lat="25/30")
		oczekiwany = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), [], stale, _DZIS)
		for custom_panel in (None, ""):
			with self.subTest(custom_panel=custom_panel):
				kontekst = zbuduj_kontekst(
					_umowa(), _deal(custom_panel=custom_panel), _kontakt(), _zestaw(), [], stale, _DZIS
				)
				self.assertEqual(
					{k: kontekst[k] for k in ("panel_producent_model", "panel_moc_wp", "panel_gwarancja_lat")},
					{k: oczekiwany[k] for k in ("panel_producent_model", "panel_moc_wp", "panel_gwarancja_lat")},
				)

	def test_c_dezaktywowana_karta_nadal_pasuje(self: "TestPanelZDeal") -> None:
		card = _panel_komponent(aktywny=0)
		custom_panel = f"{card['nazwa']} {card['model']}"
		kontekst = self._kontekst_panel(card, custom_panel)
		self.assertEqual(kontekst["panel_producent_model"], custom_panel)
		self.assertEqual(kontekst["panel_moc_wp"], "425")

	def test_d_zero_mocy_panelu_jest_puste(self: "TestPanelZDeal") -> None:
		card = _panel_komponent(moc_wp=0)
		custom_panel = f"{card['nazwa']} {card['model']}"
		kontekst = self._kontekst_panel(card, custom_panel)
		self.assertEqual(kontekst["panel_moc_wp"], "")
		self.assertNotEqual(kontekst["panel_moc_wp"], "0")

	def test_e_custom_panel_musi_byc_sklejeniem_nazwy_i_modelu(self: "TestPanelZDeal") -> None:
		card = _panel_komponent(nazwa="Longi", model="Hi-MO 6 450 W", moc_wp=450)
		custom_panel = f"{card['nazwa']} {card['model']}"
		kontekst = self._kontekst_panel(card, custom_panel)
		self.assertEqual(custom_panel, "Longi Hi-MO 6 450 W")
		self.assertEqual(kontekst["panel_producent_model"], custom_panel)
		self.assertEqual(kontekst["panel_moc_wp"], "450")

	def test_f_niepasujacy_panel_wraca_do_stale(self: "TestPanelZDeal") -> None:
		stale = _stale(panel_producent="Trina", panel_model="Vertex S+", panel_moc_wp=435, panel_gwarancja_lat="25/30")
		kontekst = zbuduj_kontekst(
			_umowa(), _deal(custom_panel="Nie ma takiego panelu"), _kontakt(), _zestaw(), [_panel_komponent()], stale, _DZIS
		)
		kontekst_stale = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), [], stale, _DZIS)
		self.assertEqual(kontekst["panel_producent_model"], kontekst_stale["panel_producent_model"])
		self.assertEqual(kontekst["panel_moc_wp"], kontekst_stale["panel_moc_wp"])
		self.assertEqual(kontekst["panel_gwarancja_lat"], kontekst_stale["panel_gwarancja_lat"])


class TestKontraktPolKomponentu(unittest.TestCase):
	"""Regresja defektu z 2026-08-06: `crm/api/umowa.py::_KOMPONENT_POLA` był
	literałem osobnym od tego, czego `zbuduj_kontekst` faktycznie potrzebuje, i
	brakowało w nim `kategoria` — `_znajdz_komponent` nigdy niczego nie
	dopasowywał, bez błędu w logach, po prostu puste pola w PDF-ie umowy. Żaden
	istniejący test tego nie łapał, bo wszystkie fixture'y komponentów w tym
	pliku ręcznie wpisywały `kategoria` z góry.

	Testy poniżej budują wiersze komponentów WYŁĄCZNIE z kluczy zadeklarowanych
	w `POLA_KOMPONENTU` (stała-kontrakt w `crm/volteo_umowa_pdf.py`) zamiast z
	ręcznie wymyślonego zestawu — jeśli ktoś kiedyś usunie `kategoria` (albo
	inny wymagany klucz) z tej stałej, `_komponent_z_kontraktu` przestanie go
	dołączać i `test_a` poniżej pęknie, zamiast po cichu dalej przechodzić."""

	@staticmethod
	def _komponent_z_kontraktu(**wartosci: Any) -> dict[str, Any]:
		"""Buduje wiersz komponentu z dokładnie kluczy `POLA_KOMPONENTU` — brakująca
		wartość w `wartosci` daje `None` na danym kluczu (symuluje pole nigdy
		niewypełnione w bazie), a klucz spoza `POLA_KOMPONENTU` jest ignorowany
		(symuluje pole, którego API i tak by nie pobrało)."""
		return {pole: wartosci.get(pole) for pole in POLA_KOMPONENTU}

	def test_a_dopasowanie_dziala_gdy_wiersz_ma_dokladnie_pola_kontraktu(self: "TestKontraktPolKomponentu") -> None:
		falownik = self._komponent_z_kontraktu(
			kategoria="Falownik",
			nazwa="Sigenergy",
			model="TP2 6 kW",
			producent="Sigenergy",
			moc_kw=Decimal("6.0"),
			gwarancja_lat=10,
		)
		kontekst = zbuduj_kontekst(_umowa(), _deal(), _kontakt(), _zestaw(), [falownik], _stale(), _DZIS)
		self.assertEqual(kontekst["inwerter_moc_kw"], "6")
		self.assertEqual(kontekst["inwerter_gwarancja_lat"], "10")

	def test_b_dane_1_do_1_z_produkcji_falownik(self: "TestKontraktPolKomponentu") -> None:
		# Wiersz zweryfikowany sondą na produkcji 2026-08-06 (float, nie Decimal —
		# dokładnie tak, jak `frappe.get_all` zwraca dane).
		komponenty = [
			{
				"kategoria": "Falownik",
				"nazwa": "Sigenergy",
				"model": "TP2 6 kW",
				"moc_kw": 6.0,
				"pojemnosc_kwh": 0.0,
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_falownik="Sigenergy TP2 6 kW")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		self.assertEqual(kontekst["inwerter_moc_kw"], "6")
		# `gwarancja_lat = 0` na produkcji dla wszystkich 72 wierszy — zero ma
		# nadal wychodzić jako pustka, nie jako "0 lat gwarancji".
		self.assertEqual(kontekst["inwerter_gwarancja_lat"], "")

	def test_c_dane_1_do_1_z_produkcji_magazyn(self: "TestKontraktPolKomponentu") -> None:
		komponenty = [
			{
				"kategoria": "Magazyn energii",
				"nazwa": "Sigenergy",
				"model": "12 kWh (6+6)",
				"moc_kw": 0.0,
				"pojemnosc_kwh": 12.0,
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_bateria="Sigenergy 12 kWh (6+6)")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		# Magazyny mają `moc_kw = 0.0` na produkcji — pustka, nie "0".
		self.assertEqual(kontekst["bateria_moc_kw"], "")
		self.assertEqual(kontekst["bateria_gwarancja_lat"], "")

	def test_d_ta_sama_nazwa_w_innej_kategorii_nie_pasuje(self: "TestKontraktPolKomponentu") -> None:
		# Falownik i magazyn o identycznej sklejonej nazwie "Sigenergy TP2 6 kW" —
		# filtr po kategorii ma nadal działać, nie tylko sklejona nazwa.
		falownik_prawdziwy = self._komponent_z_kontraktu(
			kategoria="Falownik", nazwa="Sigenergy", model="TP2 6 kW", moc_kw=Decimal("6.0"), gwarancja_lat=10
		)
		magazyn_ta_sama_nazwa = self._komponent_z_kontraktu(
			kategoria="Magazyn energii", nazwa="Sigenergy", model="TP2 6 kW", moc_kw=Decimal("99.0"), gwarancja_lat=99
		)
		deal = _deal(custom_falownik="Sigenergy TP2 6 kW")
		kontekst = zbuduj_kontekst(
			_umowa(), deal, _kontakt(), _zestaw(), [magazyn_ta_sama_nazwa, falownik_prawdziwy], _stale(), _DZIS
		)
		# Musi dopasować falownik (moc 6), nie magazyn o tej samej nazwie (moc 99).
		self.assertEqual(kontekst["inwerter_moc_kw"], "6")
		self.assertEqual(kontekst["inwerter_gwarancja_lat"], "10")


class TestBateriaSztPojemnoscJedn(unittest.TestCase):
	"""Fixture `_komponenty()` domyślnie ma "Sigenergy 12 kWh (6+6)" — 2 moduły
	po 6 kWh równe, więc `bateria_szt`/`bateria_pojemnosc_jedn_kwh` wychodzą
	wypełnione, nie puste (odczyt z konwencji nazewnictwa katalogu, ZADANIE 1)."""

	def test_a_moduly_rowne_sztuki_i_pojemnosc_jedn_wypelnione(
		self: "TestBateriaSztPojemnoscJedn",
	) -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["bateria_szt"], "2")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6")

	def test_b_lacznie_kwh_liczone_normalnie(self: "TestBateriaSztPojemnoscJedn") -> None:
		deal = _deal(custom_pojemnosc_kwh=Decimal("12.0"))
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_pojemnosc_lacznie_kwh"], "12")

	def test_c_brak_baterii_na_deal_oba_puste(self: "TestBateriaSztPojemnoscJedn") -> None:
		deal = _deal(custom_bateria=None)
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_szt"], "")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "")

	def test_d_bateria_nieznana_w_katalogu_oba_puste(self: "TestBateriaSztPojemnoscJedn") -> None:
		deal = _deal(custom_bateria="Coś czego nie ma w katalogu")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_szt"], "")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "")

	def test_e_model_nierozpoznawalny_regula_4_oba_puste(self: "TestBateriaSztPojemnoscJedn") -> None:
		# Komponent JEST dopasowany (sklejona nazwa pasuje), ale `model` nie
		# zawiera nawet "kWh" — nie wygląda na zapis pojemności, więc nie
		# zgadujemy, tylko zwracamy pustkę (reguła 4 zadania).
		komponenty = [
			{
				"kategoria": "Magazyn energii",
				"nazwa": "Tajemniczy",
				"model": "Model bez wzorca",
				"pojemnosc_kwh": Decimal("12.0"),
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_bateria="Tajemniczy Model bez wzorca")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_szt"], "")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "")

	def test_f_literowka_w_katalogu_regula_5_oba_puste(self: "TestBateriaSztPojemnoscJedn") -> None:
		# Suma składników nawiasu (6+6=12) nie zgadza się z zapisaną
		# `pojemnosc_kwh` (15) — literówka w katalogu, więc oba klucze puste
		# zamiast zgadywania, która wartość jest błędna (reguła 5 zadania).
		komponenty = [
			{
				"kategoria": "Magazyn energii",
				"nazwa": "Sigenergy",
				"model": "15 kWh (6+6)",
				"pojemnosc_kwh": Decimal("15.0"),
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_bateria="Sigenergy 15 kWh (6+6)")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_szt"], "")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "")

	def test_g_moduly_rozne_pojemnosc_jedn_lista_przecinkowa(self: "TestBateriaSztPojemnoscJedn") -> None:
		# Moduły o różnych pojemnościach (suma się zgadza, składniki różne) —
		# zamiast pustki drukujemy listę po przecinku, żeby dokument pokazywał
		# realny skład zestawu zamiast udawać jedną wspólną wartość.
		komponenty = [
			{
				"kategoria": "Magazyn energii",
				"nazwa": "Sigenergy",
				"model": "21 kWh (6+6+9)",
				"pojemnosc_kwh": Decimal("21.0"),
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_bateria="Sigenergy 21 kWh (6+6+9)")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)
		self.assertEqual(kontekst["bateria_szt"], "3")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6,6,9")


class TestBateriaKatalogDwanascieWierszy(unittest.TestCase):
	"""Każdy z dwunastu rzeczywistych wierszy katalogu "Magazyn energii"
	(zweryfikowanych sondą — patrz treść zadania), po jednym teście na wiersz."""

	@staticmethod
	def _kontekst_dla(nazwa: str, model: str, pojemnosc_kwh: str) -> dict[str, Any]:
		komponenty = [
			{
				"kategoria": "Magazyn energii",
				"nazwa": nazwa,
				"model": model,
				"pojemnosc_kwh": Decimal(pojemnosc_kwh),
				"gwarancja_lat": 0,
			}
		]
		deal = _deal(custom_bateria=f"{nazwa} {model}")
		return zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), komponenty, _stale(), _DZIS)

	def test_a_sigenergy_12_6plus6(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Sigenergy", "12 kWh (6+6)", "12.0")
		self.assertEqual(kontekst["bateria_szt"], "2")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6")

	def test_b_sigenergy_15_6plus9(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		# Moduły różne (6+9) — lista przecinkowa zamiast pustki (user request,
		# 2026-08-12): "6,9" pokazuje realny skład, nie udaje jednej wartości.
		kontekst = self._kontekst_dla("Sigenergy", "15 kWh (6+9)", "15.0")
		self.assertEqual(kontekst["bateria_szt"], "2")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6,9")

	def test_c_sigenergy_18_9plus9(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Sigenergy", "18 kWh (9+9)", "18.0")
		self.assertEqual(kontekst["bateria_szt"], "2")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "9")

	def test_d_sigenergy_21_6plus6plus9(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		# Moduły różne (6+6+9) — lista przecinkowa "6,6,9" (user request, 2026-08-12).
		kontekst = self._kontekst_dla("Sigenergy", "21 kWh (6+6+9)", "21.0")
		self.assertEqual(kontekst["bateria_szt"], "3")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6,6,9")

	def test_e_sigenergy_24_6plus9plus9(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		# Moduły różne (6+9+9) — lista przecinkowa "6,9,9" (user request, 2026-08-12).
		kontekst = self._kontekst_dla("Sigenergy", "24 kWh (6+9+9)", "24.0")
		self.assertEqual(kontekst["bateria_szt"], "3")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "6,9,9")

	def test_f_sigenergy_27_9plus9plus9(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Sigenergy", "27 kWh (9+9+9)", "27.0")
		self.assertEqual(kontekst["bateria_szt"], "3")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "9")

	def test_g_deye_12_bez_nawiasu(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Deye", "12 kWh", "12.0")
		self.assertEqual(kontekst["bateria_szt"], "1")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "12")

	def test_h_deye_16_bez_nawiasu(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Deye", "16 kWh", "16.0")
		self.assertEqual(kontekst["bateria_szt"], "1")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "16")

	def test_i_deye_24_12plus12(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Deye", "24 kWh (12+12)", "24.0")
		self.assertEqual(kontekst["bateria_szt"], "2")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "12")

	def test_j_solax_tbat_5_8_bez_nawiasu(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Bateria Solax", "T-BAT 5.8kWh", "5.8")
		self.assertEqual(kontekst["bateria_szt"], "1")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "5,8")

	def test_k_solax_tbat_10_6_bez_nawiasu(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Bateria Solax", "T-BAT 10.6kWh", "10.6")
		self.assertEqual(kontekst["bateria_szt"], "1")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "10,6")

	def test_l_dyness_tower_10_6_bez_nawiasu(self: "TestBateriaKatalogDwanascieWierszy") -> None:
		kontekst = self._kontekst_dla("Dyness", "Tower 10.6kWh", "10.6")
		self.assertEqual(kontekst["bateria_szt"], "1")
		self.assertEqual(kontekst["bateria_pojemnosc_jedn_kwh"], "10,6")


class TestPparyBooleanRozlaczne(unittest.TestCase):
	def test_a_internet_trzy_opcje(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(internet="Kablowy")
		self.assertFalse(kontekst["internet_wifi"])
		self.assertTrue(kontekst["internet_kablowy"])
		self.assertFalse(kontekst["internet_brak"])

	def test_b_internet_nieznany_wszystkie_false(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(internet=None)
		self.assertFalse(kontekst["internet_wifi"])
		self.assertFalse(kontekst["internet_kablowy"])
		self.assertFalse(kontekst["internet_brak"])

	def test_c_fazy(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(liczba_faz="1")
		self.assertTrue(kontekst["fazy_1"])
		self.assertFalse(kontekst["fazy_3"])

	def test_d_budynek_nieznany_typ_oba_false(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(typ_budynku="")
		self.assertFalse(kontekst["budynek_jednorodzinny"])
		self.assertFalse(kontekst["budynek_wielorodzinny"])

	def test_e_powierzchnia_prog(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(powierzchnia_prog="powyżej 300 m²")
		self.assertFalse(kontekst["pow_do_300"])
		self.assertTrue(kontekst["pow_ponad_300"])

	def test_f_odgromowa_i_przekop(self: "TestPparyBooleanRozlaczne") -> None:
		kontekst = _kontekst(instalacja_odgromowa="Tak", przekop_gruntowy="Tak")
		self.assertTrue(kontekst["odgromowa_tak"])
		self.assertFalse(kontekst["odgromowa_nie"])
		self.assertTrue(kontekst["przekop_tak"])
		self.assertFalse(kontekst["przekop_nie"])


class TestPpoz(unittest.TestCase):
	def test_a_wymagane(self: "TestPpoz") -> None:
		kontekst = _kontekst(ppoz_wymagane=1)
		self.assertTrue(kontekst["ppoz_tak"])
		self.assertFalse(kontekst["ppoz_nie"])

	def test_b_niewymagane_jednoznacznie_zapisane_jako_zero(self: "TestPpoz") -> None:
		kontekst = _kontekst(ppoz_wymagane=0)
		self.assertFalse(kontekst["ppoz_tak"])
		self.assertTrue(kontekst["ppoz_nie"])

	def test_c_nieznane_oba_puste(self: "TestPpoz") -> None:
		kontekst = _kontekst(ppoz_wymagane=None)
		self.assertFalse(kontekst["ppoz_tak"])
		self.assertFalse(kontekst["ppoz_nie"])

	def test_d_string_z_klienta(self: "TestPpoz") -> None:
		kontekst = _kontekst(ppoz_wymagane="1")
		self.assertTrue(kontekst["ppoz_tak"])


class TestKabel(unittest.TestCase):
	"""`dodatkowy_kabel` (Select: Tak/Nie) jest właściwym źródłem prawdy, gdy
	wypełniony — testy `test_d`..`test_k` pokrywają jego pełną tabelę prawdy.
	Testy `test_a`..`test_c` pokrywają umowy sprzed wprowadzenia tego Select
	(pole brakuje/puste/nierozpoznane), gdzie jedynym sygnałem pozostaje stara
	heurystyka: dodatnia liczba metrów kabla = Tak."""

	def test_a_kabel_dodatni_wlacza_tak(self: "TestKabel") -> None:
		# Selektor nieobecny w ogóle (fixture bazowy nie ma klucza
		# "dodatkowy_kabel") — legacy heurystyka metrów decyduje.
		kontekst = _kontekst(dodatkowy_kabel_m=15)
		self.assertTrue(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "15")

	def test_b_kabel_zero_nie_zgaduje_nie(self: "TestKabel") -> None:
		# Selektor nieobecny i metry zerowe — nie da się odróżnić "klient nie
		# potrzebuje kabla" od "pole jeszcze nie wypełnione", więc obie kratki
		# puste (legacy heurystyka, tak jak w test_a, tylko z zerem metrów).
		kontekst = _kontekst(dodatkowy_kabel_m=0)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_c_kabel_brak_pola(self: "TestKabel") -> None:
		umowa = _umowa()
		del umowa["dodatkowy_kabel_m"]
		kontekst = zbuduj_kontekst(umowa, _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_d_wybor_tak_z_metrami(self: "TestKabel") -> None:
		kontekst = _kontekst(dodatkowy_kabel="Tak", dodatkowy_kabel_m=15)
		self.assertTrue(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "15")

	def test_e_wybor_tak_zero_metrow(self: "TestKabel") -> None:
		# Jawne "Tak" wystarcza samo w sobie — zerowe metry nie cofają kratki,
		# tylko zostawiają pole mb puste (kabel będzie, długość nieznana).
		kontekst = _kontekst(dodatkowy_kabel="Tak", dodatkowy_kabel_m=0)
		self.assertTrue(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_f_wybor_tak_brak_pola_metrow(self: "TestKabel") -> None:
		umowa = _umowa(dodatkowy_kabel="Tak")
		del umowa["dodatkowy_kabel_m"]
		kontekst = zbuduj_kontekst(umowa, _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertTrue(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_g_wybor_nie_zero_metrow(self: "TestKabel") -> None:
		kontekst = _kontekst(dodatkowy_kabel="Nie", dodatkowy_kabel_m=0)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertTrue(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_h_wybor_nie_brak_metrow(self: "TestKabel") -> None:
		umowa = _umowa(dodatkowy_kabel="Nie")
		del umowa["dodatkowy_kabel_m"]
		kontekst = zbuduj_kontekst(umowa, _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertTrue(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_i_wybor_nie_wygrywa_mimo_metrow(self: "TestKabel") -> None:
		# Niespójny wpis (przedstawiciel zaznaczył "Nie", ale metry zostały w
		# formularzu) — jawne "Nie" wygrywa, a metry są tłumione na wydruku, bo
		# dokument prawny nie może sam sobie zaprzeczać.
		kontekst = _kontekst(dodatkowy_kabel="Nie", dodatkowy_kabel_m=15)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertTrue(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")

	def test_j_wybor_nieznany_string_legacy_metry_dodatnie(self: "TestKabel") -> None:
		# Wartość spoza Tak/Nie (np. dane historyczne/uszkodzone) traktowana
		# jak brak selektora — heurystyka metrów przejmuje decyzję.
		kontekst = _kontekst(dodatkowy_kabel="Coś nieznanego", dodatkowy_kabel_m=15)
		self.assertTrue(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "15")

	def test_k_wybor_pusty_string_zero_metrow(self: "TestKabel") -> None:
		kontekst = _kontekst(dodatkowy_kabel="", dodatkowy_kabel_m=0)
		self.assertFalse(kontekst["kabel_tak"])
		self.assertFalse(kontekst["kabel_nie"])
		self.assertEqual(kontekst["kabel_mb"], "")


class TestPrzekopMb(unittest.TestCase):
	def test_a_niewypelnione_pole_jest_puste(self: "TestPrzekopMb") -> None:
		# Fixture bazowy nie ustawia "przekop_mb" — pole istnieje w schemacie
		# (`ops/crm-umowa.py` + whitelist zapisu `crm/api/umowa.py`), ale bywa
		# niewypełnione, więc defensywny odczyt `.get()` daje pustkę.
		kontekst = _kontekst()
		self.assertEqual(kontekst["przekop_mb"], "")

	def test_b_wypelnione_pole_jest_drukowane(self: "TestPrzekopMb") -> None:
		kontekst = _kontekst(przekop_mb=25)
		self.assertEqual(kontekst["przekop_mb"], "25")


class TestRodo(unittest.TestCase):
	"""`rodo_data_imie_nazwisko`: linia podpisu klienta na str. 9 (indeks 8,
	koniec Załącznika nr 4 - klauzula RODO) - data zawarcia umowy + imię i
	nazwisko klienta WIELKIMI literami, decyzja produktowa 2026-08-12."""

	def test_a_data_i_imie_nazwisko_wielkimi_literami(self: "TestRodo") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["rodo_data_imie_nazwisko"], "06.08.2026, JAN KOWALSKI")

	def test_b_brak_imienia_i_nazwiska_sama_data_bez_przecinka(self: "TestRodo") -> None:
		kontakt = _kontakt(first_name="", last_name="")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), kontakt, _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["rodo_data_imie_nazwisko"], "06.08.2026")


class TestZgody(unittest.TestCase):
	def test_a_obie_udzielone(self: "TestZgody") -> None:
		kontekst = _kontekst(zgoda_kontakt_telefoniczny=1, zgoda_dzialania_promocyjne=1)
		self.assertTrue(kontekst["zgoda_telefon"])
		self.assertTrue(kontekst["zgoda_promocja"])

	def test_b_obie_nieudzielone(self: "TestZgody") -> None:
		kontekst = _kontekst(zgoda_kontakt_telefoniczny=0, zgoda_dzialania_promocyjne=0)
		self.assertFalse(kontekst["zgoda_telefon"])
		self.assertFalse(kontekst["zgoda_promocja"])

	def test_c_brak_pola_traktowany_jako_nieudzielona(self: "TestZgody") -> None:
		umowa = _umowa()
		del umowa["zgoda_kontakt_telefoniczny"]
		kontekst = zbuduj_kontekst(umowa, _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["zgoda_telefon"])

	def test_d_zalacznik_3_udzielona(self: "TestZgody") -> None:
		kontekst = _kontekst(zgoda_realizacja_przed_odstapieniem=1)
		self.assertTrue(kontekst["zgoda_wczesniejsza_realizacja"])

	def test_e_zalacznik_3_zero_nieudzielona(self: "TestZgody") -> None:
		kontekst = _kontekst(zgoda_realizacja_przed_odstapieniem=0)
		self.assertFalse(kontekst["zgoda_wczesniejsza_realizacja"])

	def test_f_zalacznik_3_brak_pola_nieudzielona(self: "TestZgody") -> None:
		umowa = _umowa()
		del umowa["zgoda_realizacja_przed_odstapieniem"]
		kontekst = zbuduj_kontekst(umowa, _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertFalse(kontekst["zgoda_wczesniejsza_realizacja"])


class TestAdresyIDane(unittest.TestCase):
	def test_a_adres_montazu_ze_szczegolowych_pol_umowy(self: "TestAdresyIDane") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["adres_montazu"], "ul. Polna 10, 02-002 Kraków")

	def test_b_adres_montazu_awaryjnie_z_deal(self: "TestAdresyIDane") -> None:
		umowa = _umowa(
			adres_montaz_ulica="",
			adres_montaz_nr_domu="",
			adres_montaz_nr_mieszkania="",
			adres_montaz_kod="",
			adres_montaz_miasto="",
		)
		deal = _deal(
			custom_install_address="Osiedlowa 3",
			custom_install_city="Poznań",
			custom_install_postal_code="61-000",
		)
		kontekst = zbuduj_kontekst(umowa, deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["adres_montazu"], "Osiedlowa 3, 61-000 Poznań")

	def test_c_klient_adres_taki_sam_jak_montaz(self: "TestAdresyIDane") -> None:
		kontekst = _kontekst(
			adres_zam_jak_montaz="Tak",
			adres_zam_ulica="",
			adres_zam_nr_domu="",
			adres_zam_nr_mieszkania="",
			adres_zam_kod="",
			adres_zam_miasto="",
		)
		self.assertEqual(kontekst["klient_adres"], kontekst["adres_montazu"])
		self.assertNotEqual(kontekst["klient_adres"], "")

	def test_d_klient_adres_wlasny_gdy_inny_niz_montaz(self: "TestAdresyIDane") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["klient_adres"], "ul. Kwiatowa 5, 00-001 Warszawa")

	def test_e_data_zawarcia_format_polski(self: "TestAdresyIDane") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["data_zawarcia"], "06.08.2026")

	def test_f_klient_imie_nazwisko(self: "TestAdresyIDane") -> None:
		kontakt = _kontakt(first_name="Anna", last_name="Nowak")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), kontakt, _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["klient_imie_nazwisko"], "Anna Nowak")

	def test_g_pesel_telefon_email_wprost_z_kontaktu(self: "TestAdresyIDane") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["klient_pesel"], "90010112345")
		self.assertEqual(kontekst["klient_telefon"], "500600700")
		self.assertEqual(kontekst["klient_email"], "jan@example.com")

	def test_h_umowa_nr_z_nazwy_deala(self: "TestAdresyIDane") -> None:
		deal = _deal(name="PRO/CP/26/0042")
		kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["umowa_nr"], "PRO/CP/26/0042")


class TestNieMutujeWejscia(unittest.TestCase):
	def test_a_zaden_argument_nie_jest_modyfikowany(self: "TestNieMutujeWejscia") -> None:
		umowa = _umowa()
		deal = _deal()
		kontakt = _kontakt()
		zestaw = _zestaw()
		komponenty = _komponenty()
		stale = _stale()

		umowa_kopia = copy.deepcopy(umowa)
		deal_kopia = copy.deepcopy(deal)
		kontakt_kopia = copy.deepcopy(kontakt)
		zestaw_kopia = copy.deepcopy(zestaw)
		komponenty_kopia = copy.deepcopy(komponenty)
		stale_kopia = copy.deepcopy(stale)

		zbuduj_kontekst(umowa, deal, kontakt, zestaw, komponenty, stale, _DZIS)

		self.assertEqual(umowa, umowa_kopia)
		self.assertEqual(deal, deal_kopia)
		self.assertEqual(kontakt, kontakt_kopia)
		self.assertEqual(zestaw, zestaw_kopia)
		self.assertEqual(komponenty, komponenty_kopia)
		self.assertEqual(stale, stale_kopia)


class TestWynikSameStringiIBooleTylko(unittest.TestCase):
	def test_a_typy_wartosci_w_kontekscie(self: "TestWynikSameStringiIBooleTylko") -> None:
		kontekst = _kontekst()
		for klucz, wartosc in kontekst.items():
			with self.subTest(klucz=klucz):
				self.assertIsInstance(wartosc, (str, bool), f"{klucz} ma typ {type(wartosc)!r}")


class TestPelnyPrzypadekZSondy(unittest.TestCase):
	"""Realistyczny, kompletny przypadek na danych zweryfikowanych sondą 2026-08-06."""

	def setUp(self: "TestPelnyPrzypadekZSondy") -> None:
		deal = _deal(
			deal_value=Decimal("43454.88"),
			custom_netto=Decimal("40236.0"),
			custom_falownik="Sigenergy TP2 6 kW",
			custom_bateria="Sigenergy 12 kWh (6+6)",
			custom_panele=10,
			custom_pv_power_kwp=Decimal("5.0"),
			custom_konstrukcja="Dach skośny - blacha",
			custom_pojemnosc_kwh=Decimal("12.0"),
		)
		self.kontekst = zbuduj_kontekst(_umowa(), deal, _kontakt(), _zestaw(), _komponenty(), _stale(), _DZIS)

	def test_a_kwoty(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertEqual(self.kontekst["wynagrodzenie_brutto"], "43 454,88")
		self.assertEqual(self.kontekst["wynagrodzenie_netto"], "40 236,00")

	def test_b_moc_i_panele(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertEqual(self.kontekst["moc_pv_kwp"], "5")
		self.assertEqual(self.kontekst["panel_szt"], "10")

	def test_c_konstrukcja(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertTrue(self.kontekst["montaz_dach"])
		self.assertFalse(self.kontekst["montaz_grunt"])
		self.assertEqual(self.kontekst["pokrycie_dachowe"], "Blacha")

	def test_d_inwerter(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertEqual(self.kontekst["inwerter_producent_model"], "Sigenergy TP2 6 kW")
		self.assertEqual(self.kontekst["inwerter_moc_kw"], "6")
		self.assertEqual(self.kontekst["inwerter_szt"], "1")

	def test_e_bateria(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertEqual(self.kontekst["bateria_producent_model"], "Sigenergy 12 kWh (6+6)")
		self.assertEqual(self.kontekst["bateria_pojemnosc_lacznie_kwh"], "12")
		self.assertEqual(self.kontekst["bateria_moc_kw"], "")
		# "12 kWh (6+6)" = 2 moduły równe po 6 kWh (ZADANIE 1) — wypełnione, nie puste.
		self.assertEqual(self.kontekst["bateria_pojemnosc_jedn_kwh"], "6")
		self.assertEqual(self.kontekst["bateria_szt"], "2")

	def test_f_panel_placeholder_pusty(self: "TestPelnyPrzypadekZSondy") -> None:
		self.assertEqual(self.kontekst["panel_producent_model"], "")
		self.assertEqual(self.kontekst["panel_moc_wp"], "")
		self.assertEqual(self.kontekst["panel_gwarancja_lat"], "")


class TestPodpisy(unittest.TestCase):
	"""ZADANIE 2: `podpis_zamawiajacy` (imię i nazwisko klienta WIELKIMI
	literami) i `podpis_wykonawca` (stały tekst "PROENERGY") — oznaczenia
	miejsc podpisu wypełnione przez nas, bo Autenti dokleja jeden zbiorczy
	podpis elektroniczny na końcu całego pliku."""

	def test_a_wielkie_litery_z_polskimi_znakami(self: "TestPodpisy") -> None:
		kontakt = _kontakt(first_name="Łukasz", last_name="Żółć")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), kontakt, _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["podpis_zamawiajacy"], "ŁUKASZ ŻÓŁĆ")

	def test_b_brak_nazwiska_pusty_string(self: "TestPodpisy") -> None:
		kontakt = _kontakt(first_name="", last_name="")
		kontekst = zbuduj_kontekst(_umowa(), _deal(), kontakt, _zestaw(), _komponenty(), _stale(), _DZIS)
		self.assertEqual(kontekst["podpis_zamawiajacy"], "")

	def test_c_podpis_wykonawca_zawsze_proenergy(self: "TestPodpisy") -> None:
		for kontakt_nadpisania in ({}, {"first_name": "", "last_name": ""}):
			with self.subTest(kontakt_nadpisania=kontakt_nadpisania):
				kontakt = _kontakt(**kontakt_nadpisania)
				kontekst = zbuduj_kontekst(
					_umowa(), _deal(), kontakt, _zestaw(), _komponenty(), _stale(), _DZIS
				)
				self.assertEqual(kontekst["podpis_wykonawca"], "PROENERGY")


if __name__ == "__main__":
	unittest.main()
