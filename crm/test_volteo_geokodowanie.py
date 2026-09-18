import unittest

from crm.volteo_geokodowanie import (
	DOKLADNOSCI,
	ZRODLA,
	Adres,
	Wynik,
	geokoduj,
	hash_adresu,
	parsuj_gugik,
	parsuj_nominatim,
	zapytanie_gugik,
	zapytanie_nominatim,
)

# --- Nagrane odpowiedzi, zweryfikowane realnym curl 2026-09-18 -----------------
# GUGiK UUG: https://services.gugik.gov.pl/uug/?request=GetAddress&address=...&srid=4326
# Nominatim: https://nominatim.openstreetmap.org/search?format=jsonv2&countrycodes=pl&...

GUGIK_SYPNIEWO_MIODOWA_10 = {
	"type": "address",
	"found objects": 15,
	"returned objects": 1,
	"results": {
		"1": {
			"city": "Sypniewo",
			"street": "Miodowa",
			"number": "10",
			"code": "89-422",
			"jednostka": "{Polska,kujawsko-pomorskie,sępoleński,Więcbork}",
			"x": "17.3146680637357",
			"y": "53.3726619432232",
			"accuracy": "1",
		}
	},
}

GUGIK_ZAKRZEWO_45_ADRES_8 = {
	"type": "address",
	"found objects": 15,
	"returned objects": 8,
	"results": {
		"1": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "63-910",
			"jednostka": "{Polska,wielkopolskie,rawicki,Miejska Górka}",
			"x": "16.8988959688829",
			"y": "51.6708325420272",
		},
		"2": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "13-200",
			"jednostka": "{Polska,warmińsko-mazurskie,działdowski,Działdowo}",
			"x": "20.1558859760874",
			"y": "53.186476432529",
		},
		"3": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "06-425",
			"jednostka": "{Polska,mazowieckie,makowski,Karniewo}",
			"x": "21.0500056743834",
			"y": "52.8857805791735",
		},
		"4": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "87-220",
			"jednostka": "{Polska,kujawsko-pomorskie,grudziądzki,Radzyń Chełmiński}",
			"x": "18.9411229903863",
			"y": "53.410991706994",
		},
		"5": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "62-620",
			"jednostka": "{Polska,wielkopolskie,kolski,Babiak}",
			"x": "18.657063325997",
			"y": "52.368056028575",
		},
		"6": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "84-223",
			"jednostka": "{Polska,pomorskie,wejherowski,Linia}",
			"x": "17.8932726470263",
			"y": "54.4596489029187",
		},
		"7": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "19-213",
			"jednostka": "{Polska,podlaskie,grajewski,Radziłów}",
			"x": "22.3163047402395",
			"y": "53.4436380111662",
		},
		"8": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "76-150",
			"jednostka": "{Polska,zachodniopomorskie,sławieński,Darłowo}",
			"x": "16.4626994487923",
			"y": "54.4465176135012",
		},
	},
}

GUGIK_BRAK_WYNIKOW = {
	"type": "address",
	"found objects": 15,
	"returned objects": 0,
	"results": None,
}

GUGIK_SWARZEDZ_MIASTO = {
	"type": "city",
	"found objects": 1,
	"results": {
		"1": {
			"city": "Swarzędz",
			"voivodeship": "wielkopolskie",
			"county": "poznański",
			"commune": "Swarzędz",
			"x": "17.0703588232033",
			"y": "52.4081689182488",
		}
	},
}

GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE = {
	"type": "city",
	"found objects": 25,
	"results": {
		"1": {
			"city": "Zakrzewo",
			"county": "trzebnicki",
			"x": "16.8200000658115",
			"y": "51.428611141916",
		},
		"2": {
			"city": "Zakrzewo",
			"county": "aleksandrowski",
			"x": "18.8141667209183",
			"y": "52.7769444624719",
		},
		"3": {
			"city": "Zakrzewo",
			"county": "aleksandrowski",
			"x": "18.6261111594886",
			"y": "52.7569444809348",
		},
		"4": {
			"city": "Zakrzewo",
			"county": "chełmiński",
			"x": "18.4730555041799",
			"y": "53.3177777387868",
		},
	},
}

GUGIK_MARSZALKOWSKA_ULICA_TYP_STREET = {
	"type": "street",
	"found objects": 1,
	"results": {
		"1": {
			"street": "ulica Marszałkowska",
			"city": "Warszawa",
			"x": "21.0123420894858",
			"y": "52.2288011708547",
		}
	},
}

NOMINATIM_SYPNIEWO_MIODOWA_10 = [
	{
		"lat": "53.3726619",
		"lon": "17.3146681",
		"place_rank": 30,
		"display_name": "10, Miodowa, Sypniewo, gmina Więcbork, powiat sępoleński, "
		"województwo kujawsko-pomorskie, 89-422, Polska",
	}
]

NOMINATIM_SWARZEDZ_MIASTO = [
	{
		"lat": "52.4103728",
		"lon": "17.0771038",
		"place_rank": 16,
		"display_name": "Swarzędz, gmina Swarzędz, powiat poznański, "
		"województwo wielkopolskie, 62-020, Polska",
	}
]

NOMINATIM_MIODOWA_ULICA = [
	{
		"lat": "53.3722459",
		"lon": "17.3150417",
		"place_rank": 26,
		"display_name": "Miodowa, Sypniewo, gmina Więcbork, powiat sępoleński, "
		"województwo kujawsko-pomorskie, 89-422, Polska",
	}
]

NOMINATIM_PUSTA = []


def _adres(ulica="", nr_domu="", kod="", miejscowosc="") -> Adres:
	return Adres(ulica=ulica, nr_domu=nr_domu, kod=kod, miejscowosc=miejscowosc)


def _http_get_z_sekwencji(odpowiedzi: list):
	"""Fałszywe `http_get`: zwraca kolejne elementy `odpowiedzi` przy kolejnych
	wywołaniach; element będący instancją `Exception` jest podnoszony zamiast
	zwrócony. `wywolania` zbiera (url, params, headers) każdego wywołania, do
	sprawdzenia w testach, ile razy i z czym `geokoduj` sięgnął po sieć."""
	wywolania = []

	def http_get(url, params, headers):
		wywolania.append((url, params, headers))
		wynik = odpowiedzi[len(wywolania) - 1]
		if isinstance(wynik, Exception):
			raise wynik
		return wynik

	http_get.wywolania = wywolania
	return http_get


class TestStale(unittest.TestCase):
	def test_a_dokladnosci_i_zrodla_ksztalt(self: "TestStale") -> None:
		self.assertEqual(DOKLADNOSCI, ("adres", "ulica", "miejscowosc", "kod", "brak"))
		self.assertEqual(ZRODLA, ("gugik", "osm", "kod", "reczne"))


class TestZapytanieGugik(unittest.TestCase):
	def test_b_wies_bez_ulicy_z_numerem(self: "TestZapytanieGugik") -> None:
		adres = _adres(nr_domu="10", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo 10")

	def test_c_wies_gdzie_ulica_rowna_miejscowosci_case_insensitive(
		self: "TestZapytanieGugik",
	) -> None:
		adres = _adres(ulica="sypniewo", nr_domu="10", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo 10")

	def test_d_ulica_i_numer(self: "TestZapytanieGugik") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo, Miodowa 10")

	def test_e_sama_ulica_bez_numeru(self: "TestZapytanieGugik") -> None:
		adres = _adres(ulica="Miodowa", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo, Miodowa")

	def test_f_tylko_miejscowosc(self: "TestZapytanieGugik") -> None:
		adres = _adres(miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo")

	def test_g_wies_bez_ulicy_bez_numeru_to_tez_tylko_miejscowosc(
		self: "TestZapytanieGugik",
	) -> None:
		adres = _adres(ulica="Sypniewo", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo")

	def test_h_brak_miejscowosci(self: "TestZapytanieGugik") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422")
		self.assertIsNone(zapytanie_gugik(adres))

	def test_i_biale_znaki_przycinane(self: "TestZapytanieGugik") -> None:
		adres = _adres(ulica="  Miodowa  ", nr_domu=" 10 ", miejscowosc="  Sypniewo  ")
		self.assertEqual(zapytanie_gugik(adres), "Sypniewo, Miodowa 10")


class TestParsujGugik(unittest.TestCase):
	def test_j_adres_jeden_wynik_z_numerem(self: "TestParsujGugik") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		wynik = parsuj_gugik(GUGIK_SYPNIEWO_MIODOWA_10, adres)
		self.assertEqual(wynik, Wynik(lat=53.3726619432232, lng=17.3146680637357, dokladnosc="adres", zrodlo="gugik"))

	def test_k_adres_kandydat_bez_numeru_ma_ulica(self: "TestParsujGugik") -> None:
		odpowiedz = {
			"type": "address",
			"results": {"1": {"street": "Miodowa", "number": None, "code": "89-422", "x": "17.0", "y": "53.0"}},
		}
		wynik = parsuj_gugik(odpowiedz, _adres(kod="89-422"))
		self.assertEqual(wynik.dokladnosc, "ulica")

	def test_l_adres_kandydat_bez_ulicy_ani_numeru_ma_miejscowosc(
		self: "TestParsujGugik",
	) -> None:
		odpowiedz = {
			"type": "address",
			"results": {"1": {"street": None, "number": None, "code": "89-422", "x": "17.0", "y": "53.0"}},
		}
		wynik = parsuj_gugik(odpowiedz, _adres(kod="89-422"))
		self.assertEqual(wynik.dokladnosc, "miejscowosc")

	def test_m_adres_wieloznaczny_rozstrzygniety_po_kodzie(self: "TestParsujGugik") -> None:
		adres = _adres(nr_domu="45", kod="84-223", miejscowosc="Zakrzewo")
		wynik = parsuj_gugik(GUGIK_ZAKRZEWO_45_ADRES_8, adres)
		self.assertIsNotNone(wynik)
		self.assertAlmostEqual(wynik.lat, 54.4596489029187)
		self.assertAlmostEqual(wynik.lng, 17.8932726470263)
		self.assertEqual(wynik.dokladnosc, "adres")

	def test_n_adres_wieloznaczny_bez_dopasowania_kodu_i_rozrzucony_ponad_300m(
		self: "TestParsujGugik",
	) -> None:
		adres = _adres(nr_domu="45", kod="00-000", miejscowosc="Zakrzewo")
		self.assertIsNone(parsuj_gugik(GUGIK_ZAKRZEWO_45_ADRES_8, adres))

	def test_o_adres_wieloznaczny_ale_w_promieniu_300m_bierze_pierwszy(
		self: "TestParsujGugik",
	) -> None:
		odpowiedz = {
			"type": "address",
			"results": {
				"1": {"street": "Rynek", "number": "1", "code": "00-000", "x": "19.0000", "y": "52.0000"},
				"2": {"street": "Rynek", "number": "1a", "code": "00-000", "x": "19.0010", "y": "52.0010"},
			},
		}
		wynik = parsuj_gugik(odpowiedz, _adres(kod="99-999"))
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.lat, 52.0000)

	def test_p_brak_wynikow_results_none(self: "TestParsujGugik") -> None:
		self.assertIsNone(parsuj_gugik(GUGIK_BRAK_WYNIKOW, _adres()))

	def test_q_odpowiedz_none(self: "TestParsujGugik") -> None:
		self.assertIsNone(parsuj_gugik(None, _adres()))

	def test_r_odpowiedz_bez_klucza_results(self: "TestParsujGugik") -> None:
		self.assertIsNone(parsuj_gugik({"type": "address"}, _adres()))

	def test_s_miasto_jeden_wynik(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(GUGIK_SWARZEDZ_MIASTO, _adres(miejscowosc="Swarzędz"))
		self.assertEqual(wynik, Wynik(lat=52.4081689182488, lng=17.0703588232033, dokladnosc="miejscowosc", zrodlo="gugik"))

	def test_t_miasto_wieloznaczne_rozstrzygniete_po_powiecie(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(
			GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE, _adres(miejscowosc="Zakrzewo"), powiat="trzebnicki"
		)
		self.assertIsNotNone(wynik)
		self.assertAlmostEqual(wynik.lat, 51.428611141916)

	def test_u_miasto_wieloznaczne_bez_powiatu_zwraca_none(self: "TestParsujGugik") -> None:
		self.assertIsNone(parsuj_gugik(GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE, _adres(miejscowosc="Zakrzewo")))

	def test_v_miasto_wieloznaczne_powiat_dwa_dopasowania_zwraca_none(
		self: "TestParsujGugik",
	) -> None:
		# "aleksandrowski" pasuje do DWÓCH kandydatów w tej próbce - niejednoznaczne.
		wynik = parsuj_gugik(
			GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE, _adres(miejscowosc="Zakrzewo"), powiat="aleksandrowski"
		)
		self.assertIsNone(wynik)

	def test_w_miasto_wieloznaczne_powiat_bez_dopasowania(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(
			GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE, _adres(miejscowosc="Zakrzewo"), powiat="nieistniejacy"
		)
		self.assertIsNone(wynik)

	def test_x_typ_street_nieobslugiwany(self: "TestParsujGugik") -> None:
		self.assertIsNone(parsuj_gugik(GUGIK_MARSZALKOWSKA_ULICA_TYP_STREET, _adres(miejscowosc="Warszawa")))


class TestZapytanieNominatim(unittest.TestCase):
	def test_y_wies_bez_ulicy_z_numerem(self: "TestZapytanieNominatim") -> None:
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		parametry = zapytanie_nominatim(adres)
		self.assertEqual(parametry["street"], "10 Sypniewo")
		self.assertEqual(parametry["city"], "Sypniewo")
		self.assertEqual(parametry["postalcode"], "89-422")
		self.assertEqual(parametry["format"], "jsonv2")
		self.assertEqual(parametry["countrycodes"], "pl")
		self.assertEqual(parametry["limit"], 1)

	def test_z_wies_bez_ulicy_bez_numeru_pomija_street(self: "TestZapytanieNominatim") -> None:
		adres = _adres(miejscowosc="Sypniewo")
		parametry = zapytanie_nominatim(adres)
		self.assertNotIn("street", parametry)
		self.assertEqual(parametry["city"], "Sypniewo")

	def test_aa_ulica_i_numer(self: "TestZapytanieNominatim") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_nominatim(adres)["street"], "Miodowa 10")

	def test_ab_sama_ulica(self: "TestZapytanieNominatim") -> None:
		adres = _adres(ulica="Miodowa", miejscowosc="Sypniewo")
		self.assertEqual(zapytanie_nominatim(adres)["street"], "Miodowa")

	def test_ac_pusty_adres_ma_tylko_podstawowe_klucze(self: "TestZapytanieNominatim") -> None:
		parametry = zapytanie_nominatim(_adres())
		self.assertEqual(parametry, {"format": "jsonv2", "countrycodes": "pl", "limit": 1})


class TestParsujNominatim(unittest.TestCase):
	def test_ad_rank_30_to_adres(self: "TestParsujNominatim") -> None:
		adres = _adres(kod="89-422", miejscowosc="Sypniewo")
		wynik = parsuj_nominatim(NOMINATIM_SYPNIEWO_MIODOWA_10, adres)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertEqual(wynik.zrodlo, "osm")
		self.assertAlmostEqual(wynik.lat, 53.3726619)
		self.assertAlmostEqual(wynik.lng, 17.3146681)

	def test_ae_rank_26_to_ulica(self: "TestParsujNominatim") -> None:
		adres = _adres(kod="89-422", miejscowosc="Sypniewo")
		wynik = parsuj_nominatim(NOMINATIM_MIODOWA_ULICA, adres)
		self.assertEqual(wynik.dokladnosc, "ulica")

	def test_af_rank_16_to_miejscowosc(self: "TestParsujNominatim") -> None:
		adres = _adres(kod="62-020", miejscowosc="Swarzędz")
		wynik = parsuj_nominatim(NOMINATIM_SWARZEDZ_MIASTO, adres)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")

	def test_ag_rank_ponizej_16_to_brak(self: "TestParsujNominatim") -> None:
		lista = [{"lat": "52.0", "lon": "19.0", "place_rank": 8, "display_name": "Polska"}]
		self.assertIsNone(parsuj_nominatim(lista, _adres(miejscowosc="Polska")))

	def test_ah_pusta_lista(self: "TestParsujNominatim") -> None:
		self.assertIsNone(parsuj_nominatim(NOMINATIM_PUSTA, _adres()))

	def test_ai_none_zamiast_listy(self: "TestParsujNominatim") -> None:
		self.assertIsNone(parsuj_nominatim(None, _adres()))

	def test_aj_brak_dopasowania_kodu_i_miejscowosci_w_display_name(
		self: "TestParsujNominatim",
	) -> None:
		lista = [{"lat": "53.0", "lon": "17.0", "place_rank": 30, "display_name": "Zupelnie inne miejsce"}]
		wynik = parsuj_nominatim(lista, _adres(kod="89-422", miejscowosc="Sypniewo"))
		self.assertIsNone(wynik)

	def test_ak_brak_lat_niepoprawny(self: "TestParsujNominatim") -> None:
		lista = [{"lat": "nie-liczba", "lon": "17.0", "place_rank": 30, "display_name": "Sypniewo"}]
		self.assertIsNone(parsuj_nominatim(lista, _adres(miejscowosc="Sypniewo")))


class TestHashAdresu(unittest.TestCase):
	def test_al_taki_sam_hash_niezaleznie_od_wielkosci_liter_i_bialych_znakow(
		self: "TestHashAdresu",
	) -> None:
		a = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		b = _adres(ulica=" MIODOWA ", nr_domu=" 10 ", kod=" 89-422 ", miejscowosc=" sypniewo ")
		self.assertEqual(hash_adresu(a), hash_adresu(b))

	def test_am_rozne_adresy_dostaja_rozny_hash(self: "TestHashAdresu") -> None:
		a = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		b = _adres(ulica="Miodowa", nr_domu="11", kod="89-422", miejscowosc="Sypniewo")
		self.assertNotEqual(hash_adresu(a), hash_adresu(b))

	def test_an_hash_stabilny_miedzy_wywolaniami(self: "TestHashAdresu") -> None:
		a = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		self.assertEqual(hash_adresu(a), hash_adresu(a))
		self.assertEqual(len(hash_adresu(a)), 40)  # SHA-1 hex digest


class TestGeokoduj(unittest.TestCase):
	def test_ao_gugik_sukces_nie_woła_nominatim(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([GUGIK_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertEqual(len(http_get.wywolania), 1)

	def test_ap_gugik_brak_nominatim_sukces(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([GUGIK_BRAK_WYNIKOW, NOMINATIM_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")
		self.assertEqual(len(http_get.wywolania), 2)

	def test_aq_oba_brak_zwraca_none(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([GUGIK_BRAK_WYNIKOW, NOMINATIM_PUSTA])
		self.assertIsNone(geokoduj(adres, http_get))

	def test_ar_wyjatek_na_gugik_przechodzi_do_nominatim(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([TimeoutError("sieć padła"), NOMINATIM_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")

	def test_as_wyjatek_na_obu_nigdy_nie_rzuca(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([TimeoutError("sieć padła"), ValueError("zły JSON")])
		self.assertIsNone(geokoduj(adres, http_get))

	def test_at_uzyj_nominatim_false_pomija_druga_probe(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([GUGIK_BRAK_WYNIKOW])
		wynik = geokoduj(adres, http_get, uzyj_nominatim=False)
		self.assertIsNone(wynik)
		self.assertEqual(len(http_get.wywolania), 1)

	def test_au_wynik_poza_polska_odrzucony_probuje_nominatim(self: "TestGeokoduj") -> None:
		odpowiedz_poza_polska = {
			"type": "address",
			"results": {"1": {"street": "Rynek", "number": "1", "code": "89-422", "x": "10.0", "y": "60.0"}},
		}
		adres = _adres(ulica="Rynek", nr_domu="1", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_z_sekwencji([odpowiedz_poza_polska, NOMINATIM_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")

	def test_av_powiat_przekazywany_do_gugik(self: "TestGeokoduj") -> None:
		adres = _adres(miejscowosc="Zakrzewo")
		http_get = _http_get_z_sekwencji([GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE])
		wynik = geokoduj(adres, http_get, powiat="trzebnicki")
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")

	def test_aw_brak_adresu_probuje_od_razu_nominatim(self: "TestGeokoduj") -> None:
		# zapytanie_gugik(adres) daje None (brak miejscowości) -> GUGiK w ogóle
		# nie jest odpytywany, geokoduj przechodzi prosto do Nominatim.
		adres = _adres(kod="89-422")
		http_get = _http_get_z_sekwencji([NOMINATIM_PUSTA])
		wynik = geokoduj(adres, http_get)
		self.assertIsNone(wynik)
		self.assertEqual(len(http_get.wywolania), 1)


if __name__ == "__main__":
	unittest.main()
