import unittest

from crm.volteo_geokodowanie import (
	DOKLADNOSCI,
	GUGIK_URL,
	NOMINATIM_URL,
	ZRODLA,
	Adres,
	Wynik,
	geokoduj,
	hash_adresu,
	parsuj_gugik,
	parsuj_gugik_przysiolek,
	parsuj_nominatim,
	zapytanie_gugik,
	zapytanie_gugik_przysiolek,
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
			"voivodeship": "dolnośląskie",
			"county": "trzebnicki",
			"x": "16.8200000658115",
			"y": "51.428611141916",
		},
		"2": {
			"city": "Zakrzewo",
			"voivodeship": "kujawsko-pomorskie",
			"county": "aleksandrowski",
			"x": "18.8141667209183",
			"y": "52.7769444624719",
		},
		"3": {
			"city": "Zakrzewo",
			"voivodeship": "kujawsko-pomorskie",
			"county": "aleksandrowski",
			"x": "18.6261111594886",
			"y": "52.7569444809348",
		},
		"4": {
			"city": "Zakrzewo",
			"voivodeship": "kujawsko-pomorskie",
			"county": "chełmiński",
			"x": "18.4730555041799",
			"y": "53.3177777387868",
		},
	},
}

GUGIK_MIASTO_WOJEWODZTWO_I_POWIAT = {
	# Fixture syntetyczna (nie z realnego curl) - specjalnie skonstruowana,
	# żeby jednoznacznie sprawdzić KOLEJNOŚĆ rozstrzygania z QA #102-2:
	# najpierw województwo, potem powiat wśród tego, co zostało. Filtrowanie
	# powiatu jako pierwszego dałoby dwa dopasowania "poznański"
	# (kandydat 1 i 3, różne województwa) - błędną niejednoznaczność.
	"type": "city",
	"found objects": 3,
	"results": {
		"1": {
			"city": "Nowa Wieś",
			"voivodeship": "wielkopolskie",
			"county": "poznański",
			"x": "16.9000000000000",
			"y": "52.4000000000000",
		},
		"2": {
			"city": "Nowa Wieś",
			"voivodeship": "wielkopolskie",
			"county": "kaliski",
			"x": "18.0000000000000",
			"y": "51.7000000000000",
		},
		"3": {
			"city": "Nowa Wieś",
			"voivodeship": "mazowieckie",
			"county": "poznański",
			"x": "20.5000000000000",
			"y": "52.1000000000000",
		},
	},
}

GUGIK_ZAKRZEWO_45_JEDEN_ZLY_KOD = {
	# Sprawdzone 2026-09-18: realna odpowiedź GUGiK dla "Zakrzewo 45" ma 8
	# kandydatów (patrz GUGIK_ZAKRZEWO_45_ADRES_8), ale ten sam kształt
	# odpowiedzi (jeden kandydat "returned objects": 1) pojawia się też przy
	# innych zapytaniach, gdy GUGiK zwróci tylko jedno trafienie. Ta fixture
	# to zredukowany, syntetyczny przypadek dokładnie z opisu QA #102-1:
	# jeden kandydat w 63-910, lead ma kod 84-223 (inna wieś o tej samej
	# nazwie) - przed poprawką moduł przyjmowałby tę złą wieś.
	"type": "address",
	"found objects": 15,
	"returned objects": 1,
	"results": {
		"1": {
			"city": "Zakrzewo",
			"street": None,
			"number": "45",
			"code": "63-910",
			"jednostka": "{Polska,wielkopolskie,rawicki,Miejska Górka}",
			"x": "16.8988959688829",
			"y": "51.6708325420272",
		}
	},
}

GUGIK_BIELSKO_MIERNICZA_35 = {
	# Sprawdzone 2026-09-18: realny curl "Bielsko-Biała, Miernicza 35" -
	# GUGiK zwraca DWA kandydatów, prawdziwą ulicę (Miernicza, dokładny
	# fuzzy-match numeru 35) i fuzzy-dopasowaną INNĄ ulicę o podobnej
	# pisowni (Sternicza, accuracy 0.72 zamiast 1 - widoczne w polu
	# "accuracy" realnej odpowiedzi, pominiętym tu jako nieużywane przez
	# moduł). Każdy kandydat ma swój WŁASNY, różny kod pocztowy - miasto ma
	# kody per ulica, podczas gdy lead w bazie ma zwykle kod ogólny miasta
	# (np. 43-300) różny od obu.
	"type": "address",
	"found objects": 15,
	"returned objects": 2,
	"results": {
		"1": {
			"city": "Bielsko-Biała",
			"street": "Miernicza",
			"number": "35",
			"code": "43-318",
			"jednostka": "{Polska,śląskie,Bielsko-Biała,Bielsko-Biała}",
			"x": "19.0775563576093",
			"y": "49.8057942200174",
		},
		"2": {
			"city": "Bielsko-Biała",
			"street": "Sternicza",
			"number": "35",
			"code": "43-316",
			"jednostka": "{Polska,śląskie,Bielsko-Biała,Bielsko-Biała}",
			"x": "19.0256298900019",
			"y": "49.8053808884128",
		},
	},
}

GUGIK_ZALESIE_14_PIETNASCIE_WSI = {
	# Sprawdzone 2026-09-18: realny curl "Zalesie 14" (bez miejscowości) -
	# GUGiK trafia limit "max results limit": 15 (found == returned == 15),
	# każda wieś Zalesie inny kod; skrócone do pierwszych czterech dla
	# czytelności testu - test dotyczy braku dopasowania kodu, nie
	# konkretnej liczby kandydatów. Żaden z tych kodów (ani z pełnych 15 w
	# realnej odpowiedzi) nie jest "77-400" - kod leada z przykładu QA
	# ("Zalesie 14, 77-400 Święta").
	"type": "address",
	"found objects": 15,
	"returned objects": 15,
	"results": {
		"1": {"city": "Zalesie", "street": None, "number": "14", "code": "38-423", "x": "22.0", "y": "49.6"},
		"2": {"city": "Zalesie", "street": None, "number": "14", "code": "26-670", "x": "20.9", "y": "51.4"},
		"3": {"city": "Zalesie", "street": None, "number": "14", "code": "19-222", "x": "22.5", "y": "53.5"},
		"4": {"city": "Zalesie", "street": None, "number": "14", "code": "26-920", "x": "21.5", "y": "51.3"},
	},
}

GUGIK_SWIETA_ZALESIE_14_BRAK = {
	# Sprawdzone 2026-09-18: realny curl "Święta, Zalesie 14" (pełne
	# zapytanie GUGiK dla przysiółka) - 0 wyników. GUGiK nie zna Zalesie
	# jako części miejscowości Święta; stąd krok "hipoteza przysiółka"
	# (zapytanie samo "Zalesie 14", patrz niżej).
	"type": "address",
	"found objects": 15,
	"returned objects": 0,
	"results": None,
}

GUGIK_ZALESIE_14_Z_TRAFIENIEM = {
	# Syntetyczne rozszerzenie GUGIK_ZALESIE_14_PIETNASCIE_WSI o piąty
	# kandydat z kodem "77-400" - realny curl "Zalesie 14" zwraca limit 15
	# wyników i "77-400" nie jest wśród nich (GUGiK prawdopodobnie nie ma w
	# TERYT osobnego rekordu dla tego konkretnego przysiółka), więc ten
	# fixture demonstruje MECHANIZM (dokładne dopasowanie kodu wśród wielu
	# tożsamo nazwanych miejsc akceptowane z dokładnością "adres"), nie
	# odtwarza dosłownie stanu bazy GUGiK dla tego jednego przykładu.
	"type": "address",
	"found objects": 15,
	"returned objects": 15,
	"results": {
		"1": {"city": "Zalesie", "street": None, "number": "14", "code": "38-423", "x": "22.0", "y": "49.6"},
		"2": {"city": "Zalesie", "street": None, "number": "14", "code": "77-400", "x": "17.05", "y": "53.7"},
		"3": {"city": "Zalesie", "street": None, "number": "14", "code": "19-222", "x": "22.5", "y": "53.5"},
	},
}

GUGIK_RYBNIK_MIASTO_WIELOZNACZNE = {
	# Sprawdzone 2026-09-18: realny curl "Rybnik" (sama miejscowość) -
	# CZTERY miejscowości Rybnik w Polsce, w tym prawdziwe miasto na
	# prawach powiatu (śląskie, powiat "Rybnik" - miasto jest swoim
	# własnym powiatem w TERYT).
	"type": "city",
	"found objects": 4,
	"results": {
		"1": {
			"city": "Rybnik",
			"voivodeship": "łódzkie",
			"county": "łęczycki",
			"x": "18.9876172486982",
			"y": "52.1491643746461",
		},
		"2": {
			"city": "Rybnik",
			"voivodeship": "łódzkie",
			"county": "sieradzki",
			"x": "18.581394090746",
			"y": "51.4760935377884",
		},
		"3": {
			"city": "Rybnik",
			"voivodeship": "śląskie",
			"county": "Rybnik",
			"x": "18.5418587185368",
			"y": "50.0959900778398",
		},
		"4": {
			"city": "Rybnik",
			"voivodeship": "świętokrzyskie",
			"county": "pińczowski",
			"x": "20.6457539367068",
			"y": "50.5529700597552",
		},
	},
}

NOMINATIM_RYBNIK_POLNA_11_INNA_GMINA = [
	# Sprawdzone 2026-09-18: realny curl "Polna 11" + city=Rybnik +
	# postalcode=44-200 (kod, który wpisalibyśmy dla leada z Rybnika) -
	# Nominatim i tak trafia w INNĄ gminę (Świerklany, powiat rybnicki, kod
	# 44-264) niż zapytana - display_name NIE zawiera "44-200", więc filtr
	# kodu (parsuj_nominatim) ma to odrzucić.
	{
		"lat": "50.0402606",
		"lon": "18.5702274",
		"place_rank": 30,
		"display_name": "11, Polna, Biasawice, Michałkowice, Jankowice, gmina Świerklany, "
		"powiat rybnicki, województwo śląskie, 44-264, Polska",
	}
]

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


def _http_get_wg_url(gugik: list | None = None, nominatim: list | None = None):
	"""Fałszywe `http_get`, świadome URL-a: osobne kolejki dla GUGiK i
	Nominatim, konsumowane w kolejności wywołań do danego URL-a - odporne na
	to, ile kroków łańcucha `geokoduj` faktycznie odpytuje GUGiK (pełny
	adres, przysiółek, sama miejscowość dzielą jedną kolejkę `gugik`, w tej
	kolejności wywołań; Nominatim ma własną, osobną kolejkę). Element będący
	instancją `Exception` jest podnoszony zamiast zwrócony. Wywołanie ponad
	zaplanowaną liczbę dla danego URL-a rzuca `AssertionError` czytelnie
	sygnalizującym brakującą fixture w teście, zamiast cichego `IndexError`
	połkniętego przez `except Exception` w `geokoduj`. `wywolania` zbiera
	(url, params, headers) KAŻDEGO wywołania (obu kolejek razem), do
	sprawdzenia łącznej liczby i kolejności zapytań w teście."""
	kolejka_gugik = list(gugik or [])
	kolejka_nominatim = list(nominatim or [])
	wywolania = []

	def http_get(url, params, headers):
		wywolania.append((url, params, headers))
		kolejka = kolejka_gugik if url == GUGIK_URL else kolejka_nominatim
		if not kolejka:
			raise AssertionError(f"test nie zaplanował odpowiedzi #{len(wywolania)} dla {url!r}")
		wynik = kolejka.pop(0)
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
		# Zapytanie "sama ulica" (bez numeru) - kandydat i lead oba bez numeru
		# to zgodność (patrz `_numer_pasuje`), nie brak dopasowania.
		odpowiedz = {
			"type": "address",
			"results": {"1": {"street": "Miodowa", "number": None, "code": "89-422", "x": "17.0", "y": "53.0"}},
		}
		wynik = parsuj_gugik(odpowiedz, _adres(ulica="Miodowa", kod="89-422"))
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
		# QA #102 runda 2: oba kandydaci mają TĘ SAMĄ ulicę+numer co lead
		# (przechodzą sito 1) i TEN SAM kod ("00-000", sito 2 nie wybiera
		# jednego) - to jedyny przypadek, w którym promień 300 m w ogóle
		# wchodzi do gry: prawdopodobny duplikat rekordu GUGiK pod tym samym
		# adresem, nie dwa różne miejsca.
		odpowiedz = {
			"type": "address",
			"results": {
				"1": {"street": "Rynek", "number": "1", "code": "00-000", "x": "19.0000", "y": "52.0000"},
				"2": {"street": "Rynek", "number": "1", "code": "00-000", "x": "19.0010", "y": "52.0010"},
			},
		}
		wynik = parsuj_gugik(odpowiedz, _adres(ulica="Rynek", nr_domu="1", kod="00-000"))
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.lat, 52.0000)

	def test_o2_fuzzy_ulica_odrzucona_kod_dokladny_akceptowany(
		self: "TestParsujGugik",
	) -> None:
		# QA #102 runda 2, sito 1: "Sternicza" jest fuzzy-dopasowaniem GUGiK
		# do zapytanej "Miernicza" (inna ulica, podobna pisownia) - sito
		# street+number odrzuca ją, więc po sicie 1 zostaje TYLKO Miernicza,
		# nawet zanim jakikolwiek kod wejdzie do gry.
		adres = _adres(ulica="Miernicza", nr_domu="35", kod="43-318", miejscowosc="Bielsko-Biała")
		wynik = parsuj_gugik(GUGIK_BIELSKO_MIERNICZA_35, adres)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertAlmostEqual(wynik.lat, 49.8057942200174)
		self.assertAlmostEqual(wynik.lng, 19.0775563576093)

	def test_o2b_kod_ogolny_miasta_akceptowany_mimo_roznicy_od_kodu_ulicy(
		self: "TestParsujGugik",
	) -> None:
		# QA #102 runda 2: lead ma kod OGÓLNY miasta (43-300), różny od
		# obu kodów per-ulica w odpowiedzi (43-318/43-316). Po sicie 1
		# (street+number) zostaje DOKŁADNIE jeden kandydat (Miernicza -
		# Sternicza odpadła jako fuzzy), a jego `city` zgadza się z
		# miejscowością leada -> przyjęty mimo różnicy kodu.
		adres = _adres(ulica="Miernicza", nr_domu="35", kod="43-300", miejscowosc="Bielsko-Biała")
		wynik = parsuj_gugik(GUGIK_BIELSKO_MIERNICZA_35, adres)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertAlmostEqual(wynik.lat, 49.8057942200174)

	def test_o2c_pojedynczy_kandydat_po_ulicy_ale_inne_miasto_zwraca_none(
		self: "TestParsujGugik",
	) -> None:
		# Odróżnienie od testu wyżej: kandydat przechodzi sito 1 (street+number
		# się zgadzają), kod się nie zgadza, ALE jego `city` jest INNE niż
		# miejscowość leada - to prawdziwa kolizja (dwie różne miejscowości),
		# nie "kod ogólny miasta", więc `None`.
		odpowiedz = {
			"type": "address",
			"results": {
				"1": {"city": "Radom", "street": "Lipowa", "number": "5", "code": "26-600", "x": "21.0", "y": "51.4"}
			},
		}
		adres = _adres(ulica="Lipowa", nr_domu="5", kod="99-999", miejscowosc="Kielce")
		self.assertIsNone(parsuj_gugik(odpowiedz, adres))

	def test_o2d_wies_pojedynczy_kandydat_kod_niepasujacy_akceptowany_jak_kod_ogolny(
		self: "TestParsujGugik",
	) -> None:
		# Rewizja QA #102 rundy 1 w świetle rundy 2: sito wsi-bez-ulicy
		# wymaga `city == miejscowosc` PRZED sprawdzeniem kodu, więc
		# jedyny ocalały kandydat ma city zgodne z leadem Z DEFINICJI -
		# sito "kod ogólny miasta"/"pojedynczy kandydat" nie potrafi tu
		# odróżnić "ta sama wieś, kod niedokładny" od "inna wieś o tej
		# samej nazwie". W PRAKTYCE to nieszkodliwe: prawdziwa kolizja nazw
		# ("Zakrzewo" istnieje w 8 województwach, patrz GUGIK_ZAKRZEWO_45_ADRES_8)
		# zawsze zwraca WSZYSTKICH kandydatów razem (GUGiK nie wie, że
		# lead miał na myśli akurat jedną z nich), a wtedy o wyborze
		# decyduje dopasowanie kodu wśród wielu (test_m/test_n) - ten test
		# pokrywa tylko przypadek, gdy GUGiK sam zwrócił JEDNĄ wieś jako
		# jedyne trafienie (silny sygnał pewności), tak samo jak dla
		# pojedynczej ulicy w mieście (test_o2b).
		adres = _adres(nr_domu="45", kod="84-223", miejscowosc="Zakrzewo")
		wynik = parsuj_gugik(GUGIK_ZAKRZEWO_45_JEDEN_ZLY_KOD, adres)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "adres")

	def test_o3_adres_kod_pusty_zachowuje_stare_zachowanie(self: "TestParsujGugik") -> None:
		# Wyjątek z QA #102-1: gdy lead NIE ma kodu pocztowego wpisanego,
		# filtrowanie po kodzie jest pomijane - pojedynczy kandydat wciąż
		# wystarcza, tak jak przed poprawką.
		adres = _adres(nr_domu="45", miejscowosc="Zakrzewo")
		wynik = parsuj_gugik(GUGIK_ZAKRZEWO_45_JEDEN_ZLY_KOD, adres)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "adres")

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

	def test_w2_miasto_jeden_kandydat_wojewodztwo_pasuje(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(
			GUGIK_SWARZEDZ_MIASTO, _adres(miejscowosc="Swarzędz"), wojewodztwo="wielkopolskie"
		)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")

	def test_w3_miasto_jeden_kandydat_wojewodztwo_niezgodne_zwraca_none(
		self: "TestParsujGugik",
	) -> None:
		# QA #102-2: "ta sama logika bezpieczeństwa co w 1" - jeden kandydat
		# od początku, ale z innym województwem niż lead, to zła miejscowość
		# (powtarzająca się nazwa w innym województwie).
		wynik = parsuj_gugik(
			GUGIK_SWARZEDZ_MIASTO, _adres(miejscowosc="Swarzędz"), wojewodztwo="mazowieckie"
		)
		self.assertIsNone(wynik)

	def test_w4_miasto_wielu_kandydatow_wojewodztwo_rozstrzyga(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(
			GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE,
			_adres(miejscowosc="Zakrzewo"),
			wojewodztwo="dolnośląskie",
		)
		self.assertIsNotNone(wynik)
		self.assertAlmostEqual(wynik.lat, 51.428611141916)

	def test_w5_miasto_wojewodztwo_bez_dopasowania_zwraca_none(self: "TestParsujGugik") -> None:
		wynik = parsuj_gugik(
			GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE,
			_adres(miejscowosc="Zakrzewo"),
			wojewodztwo="lubelskie",
		)
		self.assertIsNone(wynik)

	def test_w6_miasto_wojewodztwo_potem_powiat_kolejnosc(self: "TestParsujGugik") -> None:
		# QA #102-2: filtrowanie NAJPIERW po województwie, potem po powiecie
		# wśród tego, co zostało. Filtrowanie samym powiatem "poznański" dałoby
		# DWA dopasowania (kandydat 1 i 3, różne województwa) - niejednoznaczne;
		# województwo najpierw zawęża do kandydata 1 i 2 (oba wielkopolskie),
		# dopiero wtedy powiat "poznański" rozstrzyga jednoznacznie na 1.
		wynik = parsuj_gugik(
			GUGIK_MIASTO_WOJEWODZTWO_I_POWIAT,
			_adres(miejscowosc="Nowa Wieś"),
			wojewodztwo="wielkopolskie",
			powiat="poznański",
		)
		self.assertIsNotNone(wynik)
		self.assertAlmostEqual(wynik.lat, 52.4)

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

	def test_ak2_kod_ustawiony_ale_niezgodny_mimo_pasujacej_miejscowosci(
		self: "TestParsujNominatim",
	) -> None:
		# QA #102-3: analogicznie do parsuj_gugik - gdy lead MA kod pocztowy,
		# to on rozstrzyga, nie miejscowość. Wcześniejsza wersja (kod LUB
		# miejscowość) przyjmowałaby to trafienie, bo "Sypniewo" jest w
		# display_name mimo złego kodu - dokładnie ten sam problem
		# powtarzających się nazw miejscowości co w GUGiK.
		lista = [
			{
				"lat": "53.0",
				"lon": "17.0",
				"place_rank": 30,
				"display_name": "10, Miodowa, Sypniewo, gmina Inna, powiat inny, 00-000, Polska",
			}
		]
		wynik = parsuj_nominatim(lista, _adres(kod="89-422", miejscowosc="Sypniewo"))
		self.assertIsNone(wynik)


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


class TestZapytanieGugikPrzysiolek(unittest.TestCase):
	def test_ax_ulica_rozna_od_miejscowosci_z_nr_i_kodem(
		self: "TestZapytanieGugikPrzysiolek",
	) -> None:
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertEqual(zapytanie_gugik_przysiolek(adres), "Zalesie 14")

	def test_ay_brak_kodu_pomija_krok(self: "TestZapytanieGugikPrzysiolek") -> None:
		# QA #102 runda 2: bez kodu leada nie ma jak bezpiecznie zweryfikować
		# trafienia wśród wielu identycznie nazwanych przysiółków/wsi -
		# krok jest pomijany, nie zgadywany.
		adres = _adres(ulica="Zalesie", nr_domu="14", miejscowosc="Święta")
		self.assertIsNone(zapytanie_gugik_przysiolek(adres))

	def test_az_ulica_pusta_pomija_krok(self: "TestZapytanieGugikPrzysiolek") -> None:
		adres = _adres(nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(zapytanie_gugik_przysiolek(adres))

	def test_ba_ulica_rowna_miejscowosci_to_nie_przysiolek(
		self: "TestZapytanieGugikPrzysiolek",
	) -> None:
		# To zwykła wieś-bez-ulicy (już obsłużona w kroku 1, zapytanie_gugik),
		# nie hipoteza przysiółka.
		adres = _adres(ulica="Święta", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(zapytanie_gugik_przysiolek(adres))

	def test_bb_nr_pusty_pomija_krok(self: "TestZapytanieGugikPrzysiolek") -> None:
		adres = _adres(ulica="Zalesie", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(zapytanie_gugik_przysiolek(adres))


class TestParsujGugikPrzysiolek(unittest.TestCase):
	def test_bc_dokladne_dopasowanie_kodu_wsrod_wielu_tozsamo_nazwanych(
		self: "TestParsujGugikPrzysiolek",
	) -> None:
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		wynik = parsuj_gugik_przysiolek(GUGIK_ZALESIE_14_Z_TRAFIENIEM, adres)
		self.assertEqual(wynik, Wynik(lat=53.7, lng=17.05, dokladnosc="adres", zrodlo="gugik"))

	def test_bd_limit_15_bez_dopasowania_kodu_nie_zgaduje(
		self: "TestParsujGugikPrzysiolek",
	) -> None:
		# QA #102 runda 2: GUGiK zwraca maks. 15 wyników - gdy żaden z tych,
		# co dostaliśmy, nie ma kodu leada, `None`, NIGDY zgadywanie
		# najbliższego/pierwszego.
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(parsuj_gugik_przysiolek(GUGIK_ZALESIE_14_PIETNASCIE_WSI, adres))

	def test_be_typ_city_nieobslugiwany(self: "TestParsujGugikPrzysiolek") -> None:
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(parsuj_gugik_przysiolek(GUGIK_SWARZEDZ_MIASTO, adres))

	def test_bf_odpowiedz_none(self: "TestParsujGugikPrzysiolek") -> None:
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(parsuj_gugik_przysiolek(None, adres))

	def test_bg_brak_wynikow(self: "TestParsujGugikPrzysiolek") -> None:
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		self.assertIsNone(parsuj_gugik_przysiolek(GUGIK_SWIETA_ZALESIE_14_BRAK, adres))

	def test_bh_wielu_kandydatow_z_tym_samym_kodem_w_promieniu_pierwszy(
		self: "TestParsujGugikPrzysiolek",
	) -> None:
		# 0.001 stopnia to ok. 110 m w pionie - dwa rekordy praktycznie w tym
		# samym miejscu (duplikat w bazie GUGiK), w promieniu 300 m.
		odpowiedz = {
			"type": "address",
			"results": {
				"1": {"city": "Zalesie", "street": None, "number": "14", "code": "77-400", "x": "17.050", "y": "53.700"},
				"2": {"city": "Zalesie", "street": None, "number": "14", "code": "77-400", "x": "17.051", "y": "53.701"},
			},
		}
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		wynik = parsuj_gugik_przysiolek(odpowiedz, adres)
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.lat, 53.700)


class TestGeokoduj(unittest.TestCase):
	def test_ao_gugik_sukces_nie_wola_dalej(self: "TestGeokoduj") -> None:
		adres = _adres(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(gugik=[GUGIK_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertEqual(len(http_get.wywolania), 1)

	def test_ap_gugik_brak_nominatim_sukces(self: "TestGeokoduj") -> None:
		# Wieś-bez-ulicy (bez osobnej `ulica`) - krok 2 (przysiółek) pomijany,
		# łańcuch przechodzi wprost do Nominatim.
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(gugik=[GUGIK_BRAK_WYNIKOW], nominatim=[NOMINATIM_SYPNIEWO_MIODOWA_10])
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")
		self.assertEqual(len(http_get.wywolania), 2)

	def test_aq_wszystkie_cztery_kroki_brak_zwraca_none(self: "TestGeokoduj") -> None:
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(
			gugik=[GUGIK_BRAK_WYNIKOW, GUGIK_BRAK_WYNIKOW], nominatim=[NOMINATIM_PUSTA]
		)
		self.assertIsNone(geokoduj(adres, http_get))
		self.assertEqual(len(http_get.wywolania), 3)

	def test_ar_wyjatek_na_gugik_przechodzi_do_nominatim(self: "TestGeokoduj") -> None:
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(
			gugik=[TimeoutError("sieć padła")], nominatim=[NOMINATIM_SYPNIEWO_MIODOWA_10]
		)
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")

	def test_as_wyjatek_na_kazdym_kroku_nigdy_nie_rzuca(self: "TestGeokoduj") -> None:
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(
			gugik=[TimeoutError("sieć padła"), OSError("DNS padło")],
			nominatim=[ValueError("zły JSON")],
		)
		self.assertIsNone(geokoduj(adres, http_get))
		self.assertEqual(len(http_get.wywolania), 3)

	def test_at_uzyj_nominatim_false_pomija_tylko_nominatim(self: "TestGeokoduj") -> None:
		# uzyj_nominatim=False pomija WYŁĄCZNIE krok 3 (Nominatim) - kroki
		# GUGiK (1 i 4) nadal działają, bo nie mają budżetu 1 zapytania/s.
		adres = _adres(nr_domu="10", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(gugik=[GUGIK_BRAK_WYNIKOW, GUGIK_BRAK_WYNIKOW])
		wynik = geokoduj(adres, http_get, uzyj_nominatim=False)
		self.assertIsNone(wynik)
		self.assertEqual(len(http_get.wywolania), 2)
		self.assertTrue(all(url == GUGIK_URL for url, _, _ in http_get.wywolania))

	def test_au_wynik_poza_polska_odrzucony_probuje_nominatim(self: "TestGeokoduj") -> None:
		odpowiedz_poza_polska = {
			"type": "address",
			"results": {"1": {"city": "Sypniewo", "street": None, "number": "1", "code": "89-422", "x": "10.0", "y": "60.0"}},
		}
		adres = _adres(nr_domu="1", kod="89-422", miejscowosc="Sypniewo")
		http_get = _http_get_wg_url(
			gugik=[odpowiedz_poza_polska], nominatim=[NOMINATIM_SYPNIEWO_MIODOWA_10]
		)
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.zrodlo, "osm")

	def test_av_powiat_przekazywany_do_gugik(self: "TestGeokoduj") -> None:
		adres = _adres(miejscowosc="Zakrzewo")
		http_get = _http_get_wg_url(gugik=[GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE])
		wynik = geokoduj(adres, http_get, powiat="trzebnicki")
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")

	def test_av2_wojewodztwo_przekazywane_do_gugik(self: "TestGeokoduj") -> None:
		adres = _adres(miejscowosc="Zakrzewo")
		http_get = _http_get_wg_url(gugik=[GUGIK_ZAKRZEWO_MIASTO_WIELOZNACZNE])
		wynik = geokoduj(adres, http_get, wojewodztwo="dolnośląskie")
		self.assertIsNotNone(wynik)
		self.assertAlmostEqual(wynik.lat, 51.428611141916)

	def test_aw_brak_adresu_probuje_od_razu_nominatim(self: "TestGeokoduj") -> None:
		# zapytanie_gugik(adres) i zapytanie_gugik_przysiolek(adres) dają None
		# (brak miejscowości/ulicy) -> GUGiK nie jest odpytywany wcale, tylko
		# Nominatim; krok 4 też pomija się (brak miejscowości).
		adres = _adres(kod="89-422")
		http_get = _http_get_wg_url(nominatim=[NOMINATIM_PUSTA])
		wynik = geokoduj(adres, http_get)
		self.assertIsNone(wynik)
		self.assertEqual(len(http_get.wywolania), 1)

	def test_bi_przysiolek_po_kodzie_trafia_i_konczy_lancuch(self: "TestGeokoduj") -> None:
		# "Zalesie 14, 77-400 Święta": krok 1 (pełny adres) nie trafia
		# (sprawdzone realnym curl), krok 2 (hipoteza przysiółka, sama
		# "Zalesie 14") trafia po kodzie - łańcuch kończy się tu, Nominatim
		# nigdy nie jest odpytywany.
		adres = _adres(ulica="Zalesie", nr_domu="14", kod="77-400", miejscowosc="Święta")
		http_get = _http_get_wg_url(
			gugik=[GUGIK_SWIETA_ZALESIE_14_BRAK, GUGIK_ZALESIE_14_Z_TRAFIENIEM]
		)
		wynik = geokoduj(adres, http_get)
		self.assertEqual(wynik.dokladnosc, "adres")
		self.assertEqual(wynik.zrodlo, "gugik")
		self.assertEqual(len(http_get.wywolania), 2)

	def test_bj_przysiolek_bez_kodu_pominiety_lancuch_kontynuuje(
		self: "TestGeokoduj",
	) -> None:
		# Lead bez kodu pocztowego: krok 2 jest CAŁKOWICIE pominięty (żadne
		# wywołanie http_get) - dokładnie dwa kolejne elementy kolejki GUGiK
		# starczają na kroki 1 i 4 (gdyby krok 2 błędnie odpalił, kolejka
		# GUGiK wyczerpałaby się o jedno wywołanie za wcześnie i licznik
		# poniżej by się nie zgodził).
		adres = _adres(ulica="Zalesie", nr_domu="14", miejscowosc="Święta")
		http_get = _http_get_wg_url(
			gugik=[GUGIK_SWIETA_ZALESIE_14_BRAK, GUGIK_BRAK_WYNIKOW], nominatim=[NOMINATIM_PUSTA]
		)
		wynik = geokoduj(adres, http_get)
		self.assertIsNone(wynik)
		self.assertEqual(len(http_get.wywolania), 3)

	def test_bk_city_fallback_na_koncu_lancucha_i_kolejnosc_wywolan(
		self: "TestGeokoduj",
	) -> None:
		# Kroki 1-3 wszystkie bez trafienia, krok 4 (sama miejscowość)
		# ratuje z dokładnością "miejscowosc" - lepszy punkt niż całkowity
		# brak współrzędnych. Ten sam test potwierdza KOLEJNOŚĆ łańcucha:
		# GUGiK pełny adres, GUGiK przysiółek, Nominatim, GUGiK miejscowość.
		adres = _adres(ulica="Nieistniejąca", nr_domu="1", kod="00-000", miejscowosc="Rybnik")
		http_get = _http_get_wg_url(
			gugik=[GUGIK_BRAK_WYNIKOW, GUGIK_BRAK_WYNIKOW, GUGIK_RYBNIK_MIASTO_WIELOZNACZNE],
			nominatim=[NOMINATIM_PUSTA],
		)
		wynik = geokoduj(adres, http_get, wojewodztwo="śląskie")
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")
		self.assertEqual(wynik.zrodlo, "gugik")
		self.assertAlmostEqual(wynik.lat, 50.0959900778398)
		self.assertEqual(
			[url for url, _, _ in http_get.wywolania],
			[GUGIK_URL, GUGIK_URL, NOMINATIM_URL, GUGIK_URL],
		)

	def test_bl_rybnik_polna_nominatim_kod_niezgodny_odrzucony_city_fallback_ratuje(
		self: "TestGeokoduj",
	) -> None:
		# QA #102 runda 2, przykład "Rybnik, polna 11": GUGiK "found 15,
		# returned 0" (poniżej progu - sprawdzone realnym curl), Nominatim
		# trafia "Polna 11" w INNEJ gminie z innym kodem - filtr kodu w
		# parsuj_nominatim ma to odrzucić (sprawdzone tu wprost, nie tylko
		# założone), a krok 4 (miejscowość) daje punkt Rybnika.
		adres = _adres(ulica="Polna", nr_domu="11", kod="44-200", miejscowosc="Rybnik")
		http_get = _http_get_wg_url(
			gugik=[GUGIK_BRAK_WYNIKOW, GUGIK_BRAK_WYNIKOW, GUGIK_RYBNIK_MIASTO_WIELOZNACZNE],
			nominatim=[NOMINATIM_RYBNIK_POLNA_11_INNA_GMINA],
		)
		wynik = geokoduj(adres, http_get, wojewodztwo="śląskie")
		self.assertIsNotNone(wynik)
		self.assertEqual(wynik.dokladnosc, "miejscowosc")
		self.assertEqual(wynik.zrodlo, "gugik")


if __name__ == "__main__":
	unittest.main()
