# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import copy
import unittest
from datetime import datetime

from crm.volteo_leady_import import SEPARATOR_UWAG
from crm.volteo_leady_webhook import (
	IMIE_ZASTEPCZE,
	LIMIT_ZADAN_NA_MINUTE,
	ODPOWIEDZI_POSIADA_PV,
	ODPOWIEDZI_SYSTEM_ROZLICZEN,
	UWAGA_KOD_SPOZA_BAZY,
	LadunekOdrzucony,
	dane_z_kodu_pocztowego,
	juz_scalone,
	kampania_z_uwag,
	klucz_limitu,
	limit_przekroczony,
	linia_ponownego_zgloszenia,
	normalizuj_date_zgloszenia,
	normalizuj_kod_tolerancyjnie,
	normalizuj_posiada_pv,
	normalizuj_produkt_reklamy,
	normalizuj_system_rozliczen,
	pola_do_scalenia,
	rozpoznaj_posiada_pv,
	rozpoznaj_system_rozliczen,
	splaszcz_odpowiedzi,
	tresc_sladu_ponownego_zgloszenia,
	zbuduj_leada_z_webhooka,
)

DZIS = "2026-10-22"


def ladunek(**nadpisz):
	baza = {
		"imie_nazwisko": "jan KOWALSKI",
		"telefon": "604 932 720",
		"miasto": "  Poznań ",
		"posiada_pv": "Tak",
		"system_rozliczen": "Net-billing",
		"produkt": "PV + magazyn",
		"data_zgloszenia": "2026-10-20T10:11:12+0000",
		"facebook_lead_id": "123456789",
		"facebook_form_id": "987",
		"formularz": "Formularz PV",
	}
	baza.update(nadpisz)
	return baza


def uwagi(wynik):
	return wynik["custom_uwagi_import"].split(SEPARATOR_UWAG)


class TestPosiadaPv(unittest.TestCase):
	def test_tak_warianty(self):
		for t in ("tak", "Tak", " TAK ", "yes", "True", "1"):
			self.assertEqual(normalizuj_posiada_pv(t), "PV", t)

	def test_nie_warianty(self):
		for t in ("nie", "Nie", "no", "FALSE", "0"):
			self.assertEqual(normalizuj_posiada_pv(t), "", t)

	def test_puste(self):
		self.assertEqual(normalizuj_posiada_pv(""), "")
		self.assertEqual(normalizuj_posiada_pv(None), "")

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_posiada_pv("moze"))

	def test_liczba(self):
		self.assertEqual(normalizuj_posiada_pv(1), "PV")

	def test_opisowe_czytelne_i_slugi(self):
		przypadki = {
			"Mam Fotowoltaik\u0119 bez magazynu energii": "PV",
			"mam_fotowoltaik\u0119_bez_magazynu_energii": "PV",
			"Mam Fotowoltaik\u0119 z magazynem energii": "PV+ME",
			"mam_fotowoltaik\u0119_z_magazynem_energii": "PV+ME",
			"mam_fotowoltaike_z_magazynem_energii": "PV+ME",
			"Nie mam jeszcze Fotowoltaiki": "",
			"nie_mam_jeszcze_fotowoltaiki": "",
		}
		for tekst, oczekiwane in przypadki.items():
			self.assertEqual(normalizuj_posiada_pv(tekst), oczekiwane, tekst)

	def test_opisowe_nierozpoznane(self):
		self.assertIsNone(normalizuj_posiada_pv("mam_pompe_ciepla"))
		self.assertIsNone(normalizuj_posiada_pv("fotowoltaika z magazynem"))


class TestSystemRozliczen(unittest.TestCase):
	def test_nowe(self):
		for t in ("Net-billing", "net billing", "NETBILLING", "nowe zasady", "Nowy system"):
			self.assertEqual(normalizuj_system_rozliczen(t), "Nowe zasady", t)

	def test_stare(self):
		for t in ("net-metering", "Net Metering", "opust", "stare zasady", "stary"):
			self.assertEqual(normalizuj_system_rozliczen(t), "Stare zasady", t)

	def test_slugi_meta(self):
		self.assertEqual(normalizuj_system_rozliczen("nowe_zasady_(net-billing)"), "Nowe zasady")
		self.assertEqual(normalizuj_system_rozliczen("Nowe zasady (net-billing)"), "Nowe zasady")
		self.assertEqual(normalizuj_system_rozliczen("stare_zasady"), "Stare zasady")

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_system_rozliczen("nie wiem"))

	def test_puste(self):
		self.assertIsNone(normalizuj_system_rozliczen(""))
		self.assertIsNone(normalizuj_system_rozliczen(None))

	def test_dwuznaczne(self):
		self.assertIsNone(normalizuj_system_rozliczen("net-billing albo opust"))


class TestProduktReklamy(unittest.TestCase):
	def test_pvme(self):
		for t in (
			"PV MAG",
			"pv+mag",
			"PV + magazyn",
			"pvme",
			"PV i magazyn energii",
			"Fotowoltaika z magazynem",
		):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PVME", t)

	def test_me(self):
		for t in ("mag", "Magazyn", "magazyn energii", "ME"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "ME", t)

	def test_pv(self):
		for t in ("PV", "pv", "Fotowoltaika"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PV", t)

	def test_pc(self):
		for t in ("pompa ciepła", "Pompa ciepla", "PC"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PC", t)

	def test_cp(self):
		for t in ("czyste powietrze", "Czyste Powietrze", "cp"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "CP", t)

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_produkt_reklamy("klimatyzacja"))
		self.assertIsNone(normalizuj_produkt_reklamy("PV tanio"))

	def test_mieszanka_rodzin(self):
		self.assertIsNone(normalizuj_produkt_reklamy("PV i pompa ciepła"))

	def test_puste(self):
		self.assertIsNone(normalizuj_produkt_reklamy(""))
		self.assertIsNone(normalizuj_produkt_reklamy(None))


class TestDataZgloszenia(unittest.TestCase):
	def test_iso_data(self):
		self.assertEqual(normalizuj_date_zgloszenia("2026-10-22"), "2026-10-22")

	def test_iso_datetime_warianty(self):
		for t in ("2026-10-22T10:11:12+0000", "2026-10-22T10:11:12Z", "2026-10-22T10:11:12+02:00"):
			self.assertEqual(normalizuj_date_zgloszenia(t), "2026-10-22", t)

	def test_ze_spacja(self):
		self.assertEqual(normalizuj_date_zgloszenia("2026-10-22 10:11:12"), "2026-10-22")

	def test_nieparsowalne(self):
		for t in ("22.10.2026", "jutro", "2026-13-40", "2026-10-22x"):
			self.assertIsNone(normalizuj_date_zgloszenia(t), t)

	def test_puste(self):
		self.assertIsNone(normalizuj_date_zgloszenia(""))
		self.assertIsNone(normalizuj_date_zgloszenia(None))


class TestSplaszczOdpowiedzi(unittest.TestCase):
	def test_slownik(self):
		self.assertEqual(
			splaszcz_odpowiedzi({"Rachunek": "400 zł", "Dom": "tak"}),
			[("Rachunek", "400 zł"), ("Dom", "tak")],
		)

	def test_lista_facebookowa(self):
		wej = [{"name": "Rachunek", "values": ["400 zł"]}, {"name": "Dom", "values": ["a", "b"]}]
		self.assertEqual(splaszcz_odpowiedzi(wej), [("Rachunek", "400 zł"), ("Dom", "a, b")])

	def test_lista_z_value(self):
		self.assertEqual(splaszcz_odpowiedzi([{"name": "X", "value": "1"}]), [("X", "1")])

	def test_puste_odpowiedzi_pominiete(self):
		self.assertEqual(splaszcz_odpowiedzi({"A": "", "B": None, "C": "x"}), [("C", "x")])

	def test_inne_ksztalty(self):
		self.assertEqual(splaszcz_odpowiedzi("tekst"), [])
		self.assertEqual(splaszcz_odpowiedzi(None), [])
		self.assertEqual(splaszcz_odpowiedzi(["a", 1]), [])

	def test_element_bez_nazwy(self):
		self.assertEqual(splaszcz_odpowiedzi([{"values": ["x"]}]), [])


class TestPelnyLadunek(unittest.TestCase):
	def test_dokladny_slownik(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		self.assertEqual(
			wynik,
			{
				"first_name": "Jan",
				"last_name": "Kowalski",
				"mobile_no": "+48604932720",
				"source": "Facebook",
				"custom_import_source": "FB",
				"custom_import_date": "2026-10-20",
				"facebook_lead_id": "123456789",
				"facebook_form_id": "987",
				"custom_install_city": "Poznań",
				"custom_posiadane_produkty": "PV",
				"custom_zasady_dotacji": "Nowe zasady",
				"custom_uwagi_import": SEPARATOR_UWAG.join(
					[
						"Zrodlo: Facebook Lead Ads",
						"Formularz: Formularz PV",
						"Posiada PV: Tak",
						"System rozliczen: Net-billing",
					]
				),
			},
		)

	def test_nie_mutuje_wejscia(self):
		wej = ladunek(odpowiedzi={"A": "b"})
		kopia = copy.deepcopy(wej)
		zbuduj_leada_z_webhooka(wej, DZIS)
		self.assertEqual(wej, kopia)

	def test_status_i_wlasciciel_nieustawiane(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		for klucz in ("status", "lead_owner", "custom_cc", "doctype"):
			self.assertNotIn(klucz, wynik)

	def test_klucze_bez_wielkosci_liter_i_ze_spacjami(self):
		wynik = zbuduj_leada_z_webhooka({" Telefon ": "604932720", "FACEBOOK_LEAD_ID": "5"}, DZIS)
		self.assertEqual(wynik["mobile_no"], "+48604932720")
		self.assertEqual(wynik["facebook_lead_id"], "5")

	def test_nieznane_klucze_ignorowane(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(cokolwiek="x", status="Won", lead_owner="a@b.pl"), DZIS)
		self.assertNotIn("cokolwiek", wynik)
		self.assertNotIn("status", wynik)
		self.assertNotIn("lead_owner", wynik)

	def test_minimalny_ladunek(self):
		wynik = zbuduj_leada_z_webhooka({"telefon": "604932720", "facebook_lead_id": "1"}, DZIS)
		self.assertEqual(wynik["first_name"], IMIE_ZASTEPCZE)
		self.assertNotIn("last_name", wynik)
		self.assertNotIn("custom_install_city", wynik)
		self.assertNotIn("custom_posiadane_produkty", wynik)
		self.assertNotIn("custom_produkt_procesu", wynik)
		self.assertEqual(wynik["custom_import_date"], DZIS)


class TestOdrzucenia(unittest.TestCase):
	def test_brak_telefonu(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(telefon=""), DZIS)
		self.assertIn("telefon", ctx.exception.powod.lower())

	def test_telefon_none(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka(ladunek(telefon=None), DZIS)

	def test_zly_telefon(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(telefon="12345"), DZIS)
		self.assertIn("12345", ctx.exception.powod)

	def test_brak_klucza_telefon(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka({"facebook_lead_id": "1"}, DZIS)

	def test_brak_id_leada(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(facebook_lead_id=""), DZIS)
		self.assertIn("facebook_lead_id", ctx.exception.powod)

	def test_brak_klucza_id(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka({"telefon": "604932720"}, DZIS)

	def test_ladunek_nie_slownik(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka(["a"], DZIS)

	def test_jest_value_error(self):
		self.assertTrue(issubclass(LadunekOdrzucony, ValueError))


class TestImieNazwisko(unittest.TestCase):
	def test_dwa_slowa(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="anna NOWAK"), DZIS)
		self.assertEqual((w["first_name"], w["last_name"]), ("Anna", "Nowak"))

	def test_jedno_slowo(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="anna"), DZIS)
		self.assertEqual(w["first_name"], "Anna")
		self.assertNotIn("last_name", w)

	def test_trzy_slowa(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="Jan Maria Kowalski"), DZIS)
		self.assertEqual((w["first_name"], w["last_name"]), ("Jan", "Maria Kowalski"))

	def test_firma_bez_zmian(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="Jan Kowalski Usługi Handlowe"), DZIS)
		self.assertEqual(w["first_name"], "Jan Kowalski Usługi Handlowe")
		self.assertNotIn("last_name", w)

	def test_puste_imie(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko=""), DZIS)
		self.assertEqual(w["first_name"], IMIE_ZASTEPCZE)

	def test_nazwisko_z_myslnikiem(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="ewa kowalska-nowak"), DZIS)
		self.assertEqual(w["last_name"], "Kowalska-Nowak")


class TestRozpoznaj(unittest.TestCase):
	def test_slownik_pv(self):
		self.assertEqual(rozpoznaj_posiada_pv("tak,_z_magazynem"), ("PV+ME", "Tak, z magazynem"))
		self.assertEqual(rozpoznaj_posiada_pv("TAK,_BEZ_MAGAZYNU"), ("PV", "Tak, bez magazynu"))

	def test_fallback_pv(self):
		self.assertEqual(rozpoznaj_posiada_pv("Tak"), ("PV", "Tak"))
		self.assertEqual(rozpoznaj_posiada_pv("Nie"), ("", "Nie"))

	def test_nieznane_pv(self):
		self.assertEqual(rozpoznaj_posiada_pv("moze"), (None, "moze"))

	def test_slownik_system(self):
		self.assertEqual(
			rozpoznaj_system_rozliczen("nowe_zasady_(net-billing)"),
			("Nowe zasady", "Nowe zasady (net-billing)"),
		)
		self.assertEqual(rozpoznaj_system_rozliczen("STARE_ZASADY"), ("Stare zasady", "Stare zasady"))

	def test_fallback_system(self):
		self.assertEqual(rozpoznaj_system_rozliczen("net-billing"), ("Nowe zasady", "net-billing"))

	def test_nieznany_system(self):
		self.assertEqual(rozpoznaj_system_rozliczen("moze"), (None, "moze"))


class TestSlownikOdpowiedzi(unittest.TestCase):
	def test_wszystkie_odpowiedzi_pv(self):
		for klucz, (wartosc, etykieta) in ODPOWIEDZI_POSIADA_PV.items():
			with self.subTest(klucz=klucz):
				w = zbuduj_leada_z_webhooka(ladunek(posiada_pv=klucz, system_rozliczen=""), DZIS)
				if wartosc:
					self.assertEqual(w["custom_posiadane_produkty"], wartosc)
				else:
					self.assertNotIn("custom_posiadane_produkty", w)
				self.assertIn("Posiada PV: %s" % etykieta, uwagi(w))
				self.assertNotIn("nierozpoznane", w["custom_uwagi_import"])

	def test_wszystkie_odpowiedzi_system(self):
		for klucz, (wartosc, etykieta) in ODPOWIEDZI_SYSTEM_ROZLICZEN.items():
			with self.subTest(klucz=klucz):
				w = zbuduj_leada_z_webhooka(
					ladunek(posiada_pv="tak,_bez_magazynu", system_rozliczen=klucz), DZIS
				)
				self.assertEqual(w["custom_zasady_dotacji"], wartosc)
				self.assertIn("System rozliczen: %s" % etykieta, uwagi(w))
				self.assertNotIn("nierozpoznane", w["custom_uwagi_import"])

	def test_aktualny_formularz(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(posiada_pv="tak,_z_magazynem", system_rozliczen="nowe_zasady_(net-billing)"), DZIS
		)
		self.assertEqual(w["custom_posiadane_produkty"], "PV+ME")
		self.assertEqual(w["custom_zasady_dotacji"], "Nowe zasady")
		self.assertIn("Posiada PV: Tak, z magazynem", uwagi(w))
		self.assertIn("System rozliczen: Nowe zasady (net-billing)", uwagi(w))

	def test_bez_pv_ze_starymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(posiada_pv="nie_mam_jeszcze_fotowoltaiki", system_rozliczen="stare_zasady"), DZIS
		)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("Posiada PV: Nie mam jeszcze fotowoltaiki", uwagi(w))
		self.assertIn("System rozliczen (klient bez PV): Stare zasady", uwagi(w))

	def test_brak_odpowiedzi_o_pv(self):
		w = zbuduj_leada_z_webhooka(
			{"telefon": "604932720", "facebook_lead_id": "1", "system_rozliczen": "stare_zasady"}, DZIS
		)
		self.assertIn("System rozliczen (brak odpowiedzi o PV): Stare zasady", uwagi(w))
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertNotIn("custom_posiadane_produkty", w)

	def test_nie_daje_klient_bez_pv(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="Nie", system_rozliczen="stare_zasady"), DZIS)
		self.assertIn("System rozliczen (klient bez PV): Stare zasady", uwagi(w))

	def test_pv_nierozpoznane_ze_starymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="moze", system_rozliczen="stare_zasady"), DZIS)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("Posiada PV (nierozpoznane): moze", uwagi(w))
		self.assertIn("System rozliczen (PV nierozpoznane): Stare zasady", uwagi(w))


class TestOdpowiedziOpisowe(unittest.TestCase):
	def test_pv_me_ze_starymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(
				posiada_pv="mam_fotowoltaik\u0119_z_magazynem_energii",
				system_rozliczen="stare_zasady",
			),
			DZIS,
		)
		self.assertEqual(w["custom_posiadane_produkty"], "PV+ME")
		self.assertEqual(w["custom_zasady_dotacji"], "Stare zasady")
		self.assertNotIn("nierozpoznane", w.get("custom_uwagi_import", ""))

	def test_pv_bez_magazynu_z_nowymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(
				posiada_pv="Mam Fotowoltaik\u0119 bez magazynu energii",
				system_rozliczen="nowe_zasady_(net-billing)",
			),
			DZIS,
		)
		self.assertEqual(w["custom_posiadane_produkty"], "PV")
		self.assertEqual(w["custom_zasady_dotacji"], "Nowe zasady")

	def test_nie_mam_zasady_do_uwag(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(posiada_pv="nie_mam_jeszcze_fotowoltaiki", system_rozliczen="stare_zasady"),
			DZIS,
		)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("System rozliczen (klient bez PV): Stare zasady", uwagi(w))
		self.assertNotIn("nierozpoznane", w["custom_uwagi_import"])


class TestPolaLadunku(unittest.TestCase):
	def test_lista_zamiast_stringa(self):
		w = zbuduj_leada_z_webhooka(ladunek(telefon=["604932720"], miasto=["Kraków"]), DZIS)
		self.assertEqual(w["mobile_no"], "+48604932720")
		self.assertEqual(w["custom_install_city"], "Kraków")

	def test_liczba_jako_id_i_telefon(self):
		w = zbuduj_leada_z_webhooka(ladunek(telefon=604932720, facebook_lead_id=123456789.0), DZIS)
		self.assertEqual(w["mobile_no"], "+48604932720")
		self.assertEqual(w["facebook_lead_id"], "123456789")

	def test_system_bez_pv_idzie_do_uwag(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="Nie", system_rozliczen="net-billing"), DZIS)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertIn("System rozliczen (klient bez PV): net-billing", uwagi(w))

	def test_system_nierozpoznany_z_pv(self):
		w = zbuduj_leada_z_webhooka(ladunek(system_rozliczen="nie wiem"), DZIS)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("System rozliczen (nierozpoznane): nie wiem", uwagi(w))

	def test_posiada_pv_nierozpoznane(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="moze", system_rozliczen=""), DZIS)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertIn("Posiada PV (nierozpoznane): moze", uwagi(w))

	def test_produkt_z_reklamy_ignorowany(self):
		for surowy in ("MAG", "PV + magazyn", "klimatyzacja", "x y"):
			with self.subTest(surowy=surowy):
				w = zbuduj_leada_z_webhooka(ladunek(produkt=surowy), DZIS)
				self.assertNotIn("custom_produkt_procesu", w)
				self.assertNotIn(surowy, w["custom_uwagi_import"])
				self.assertNotIn("Produkt", w["custom_uwagi_import"])

	def test_pusta_data_to_dzisiaj(self):
		w = zbuduj_leada_z_webhooka(ladunek(data_zgloszenia=""), DZIS)
		self.assertEqual(w["custom_import_date"], DZIS)
		self.assertTrue(any(l.startswith("Data zgloszenia") for l in uwagi(w)))

	def test_zla_data_to_dzisiaj_z_surowa_w_uwagach(self):
		w = zbuduj_leada_z_webhooka(ladunek(data_zgloszenia="wczoraj"), DZIS)
		self.assertEqual(w["custom_import_date"], DZIS)
		self.assertIn("Data zgloszenia (nierozpoznana): wczoraj", uwagi(w))

	def test_kampania_i_formularz_w_kolejnosci(self):
		w = zbuduj_leada_z_webhooka(ladunek(kampania="Jesien 2026"), DZIS)
		self.assertEqual(
			uwagi(w)[:3], ["Zrodlo: Facebook Lead Ads", "Formularz: Formularz PV", "Kampania: Jesien 2026"]
		)

	def test_odpowiedzi_slownik_na_koncu(self):
		w = zbuduj_leada_z_webhooka(ladunek(odpowiedzi={"Rachunek": "400 zł"}), DZIS)
		linie = uwagi(w)
		self.assertEqual(linie[-1], "Rachunek: 400 zł")

	def test_odpowiedzi_lista_facebookowa(self):
		w = zbuduj_leada_z_webhooka(ladunek(odpowiedzi=[{"name": "Dach", "values": ["skośny"]}]), DZIS)
		self.assertIn("Dach: skośny", uwagi(w))

	def test_pusta_lista_linii_nie_istnieje(self):
		# zawsze jest linia zrodla, wiec pole Uwagi nigdy nie jest puste
		w = zbuduj_leada_z_webhooka(
			{"telefon": "604932720", "facebook_lead_id": "1", "data_zgloszenia": DZIS}, DZIS
		)
		self.assertEqual(w["custom_uwagi_import"], "Zrodlo: Facebook Lead Ads")


class TestNormalizujKodTolerancyjnie(unittest.TestCase):
	def test_rozpoznaje_formaty(self):
		przypadki = {
			"00-000": "00-000",
			"00000": "00-000",
			"00 000": "00-000",
			"00 - 000": "00-000",
			"64\u2011000": "64-000",
			"64\u2013000": "64-000",
			"64.000": "64-000",
			"64_000": "64-000",
			" 64-000 ": "64-000",
			"64-000 Kościan": "64-000",
			"kod 64000": "64-000",
			"64-000 i 64000": "64-000",
		}
		for wejscie, oczekiwane in przypadki.items():
			with self.subTest(wejscie=wejscie):
				self.assertEqual(normalizuj_kod_tolerancyjnie(wejscie), oczekiwane)

	def test_odrzuca(self):
		for wejscie in ("6400", "640000", "123456789", "64-000 i 61-001", "", "abc", "Poznań", None):
			with self.subTest(wejscie=wejscie):
				self.assertIsNone(normalizuj_kod_tolerancyjnie(wejscie))


class TestKodPocztowy(unittest.TestCase):
	def test_poprawny(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="61-001"), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "61-001")

	def test_bez_kreski(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="61001"), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "61-001")
		self.assertNotIn("Kod pocztowy (nierozpoznany)", w["custom_uwagi_import"])

	def test_z_dopiskiem(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="61 - 001 Poznań"), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "61-001")

	def test_niepoprawny(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="6100"), DZIS)
		self.assertNotIn("custom_install_postal_code", w)
		self.assertIn("Kod pocztowy (nierozpoznany): 6100", uwagi(w))

	def test_dwa_kody_to_nierozpoznany(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="64-000 i 61-001"), DZIS)
		self.assertNotIn("custom_install_postal_code", w)
		self.assertIn("Kod pocztowy (nierozpoznany): 64-000 i 61-001", uwagi(w))

	def test_brak(self):
		w = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		self.assertNotIn("custom_install_postal_code", w)

	def test_miasto_z_kodem_przy_pustym_kodzie(self):
		w = zbuduj_leada_z_webhooka(ladunek(miasto="60-101"), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "60-101")
		self.assertNotIn("custom_install_city", w)

	def test_miasto_z_kodem_bez_kreski(self):
		w = zbuduj_leada_z_webhooka(ladunek(miasto="60101", kod_pocztowy=""), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "60-101")
		self.assertNotIn("custom_install_city", w)

	def test_nazwa_miasta_zostaje(self):
		w = zbuduj_leada_z_webhooka(ladunek(miasto="Poznań"), DZIS)
		self.assertEqual(w["custom_install_city"], "Poznań")
		self.assertNotIn("custom_install_postal_code", w)

	def test_kod_i_miasto_razem(self):
		w = zbuduj_leada_z_webhooka(ladunek(miasto="Poznań", kod_pocztowy="61-001"), DZIS)
		self.assertEqual(w["custom_install_city"], "Poznań")
		self.assertEqual(w["custom_install_postal_code"], "61-001")

	def test_nierozpoznany_kod_nie_zjada_miasta(self):
		w = zbuduj_leada_z_webhooka(ladunek(miasto="Poznań", kod_pocztowy="abc"), DZIS)
		self.assertEqual(w["custom_install_city"], "Poznań")
		self.assertIn("Kod pocztowy (nierozpoznany): abc", uwagi(w))


class TestDaneZKoduPocztowego(unittest.TestCase):
	"""ops#322: województwo z `Postal Code` bywa WIELKIMI literami."""

	def _wiersz(self, **nadpisz):
		return {"lat": 51.1, "lng": 17.0, "wojewodztwo": "dolnośląskie", "powiat": "wrocławski", **nadpisz}

	def test_wielkie_litery_z_diakrytykami(self):
		for surowe, oczekiwane in [
			("DOLNOŚLĄSKIE", "dolnośląskie"),
			("MAŁOPOLSKIE", "małopolskie"),
			("ŚLĄSKIE", "śląskie"),
			("Mazowieckie", "mazowieckie"),
			("pomorskie", "pomorskie"),
		]:
			wynik = dane_z_kodu_pocztowego({}, self._wiersz(wojewodztwo=surowe))
			self.assertEqual(wynik["custom_voivodeship"], oczekiwane)

	def test_spoza_kanonu_pomija_pole(self):
		wynik = dane_z_kodu_pocztowego({}, self._wiersz(wojewodztwo="Bawaria"))
		self.assertNotIn("custom_voivodeship", wynik)
		self.assertEqual(wynik["custom_lat"], 51.1)

	def test_puste_i_none(self):
		for surowe in ("", None):
			wynik = dane_z_kodu_pocztowego({}, self._wiersz(wojewodztwo=surowe))
			self.assertNotIn("custom_voivodeship", wynik)

	def test_powiat_kopiowany_bez_zmian(self):
		wynik = dane_z_kodu_pocztowego({}, self._wiersz(powiat="WROCŁAWSKI"))
		self.assertEqual(wynik["custom_powiat"], "WROCŁAWSKI")

	def test_wspolrzedne(self):
		wynik = dane_z_kodu_pocztowego({}, self._wiersz())
		self.assertEqual(wynik["custom_lng"], 17.0)
		self.assertEqual(wynik["custom_geo_dokladnosc"], "kod")
		self.assertEqual(wynik["custom_geo_zrodlo"], "kod")

	def test_brak_wspolrzednych_nie_ustawia_geo(self):
		wynik = dane_z_kodu_pocztowego({}, self._wiersz(lat=None))
		self.assertNotIn("custom_lat", wynik)
		self.assertNotIn("custom_geo_zrodlo", wynik)

	def test_brak_wiersza_dopisuje_notke(self):
		wynik = dane_z_kodu_pocztowego({"custom_uwagi_import": "stara"}, None)
		self.assertEqual(wynik["custom_uwagi_import"], SEPARATOR_UWAG.join(["stara", UWAGA_KOD_SPOZA_BAZY]))
		self.assertNotIn("custom_lat", wynik)

	def test_brak_wiersza_bez_uwag(self):
		wynik = dane_z_kodu_pocztowego({}, None)
		self.assertEqual(wynik["custom_uwagi_import"], UWAGA_KOD_SPOZA_BAZY)

	def test_nie_mutuje_wejscia(self):
		dane = {"custom_uwagi_import": "x"}
		kopia = copy.deepcopy(dane)
		dane_z_kodu_pocztowego(dane, self._wiersz(wojewodztwo="ŚLĄSKIE"))
		dane_z_kodu_pocztowego(dane, None)
		self.assertEqual(dane, kopia)


class TestKluczLimitu(unittest.TestCase):
	def test_format(self):
		k = klucz_limitu("make@x.pl", datetime(2026, 10, 22, 14, 5, 59))
		self.assertEqual(k, "volteo:webhook_leady:limit:make@x.pl:202610221405")

	def test_ta_sama_minuta_ten_sam_klucz(self):
		a = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 0))
		b = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 59))
		self.assertEqual(a, b)

	def test_granica_minuty_inny_klucz(self):
		a = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 30))
		b = klucz_limitu("u", datetime(2026, 10, 22, 14, 6, 29))
		self.assertNotEqual(a, b)

	def test_uzytkownik_w_kluczu(self):
		t = datetime(2026, 10, 22, 14, 5)
		self.assertNotEqual(klucz_limitu("a", t), klucz_limitu("b", t))


class TestLimitPrzekroczony(unittest.TestCase):
	def test_stala(self):
		self.assertEqual(LIMIT_ZADAN_NA_MINUTE, 3)

	def test_zero_i_trzy_przechodza(self):
		self.assertFalse(limit_przekroczony(0))
		self.assertFalse(limit_przekroczony(3))

	def test_czwarte_odrzucone(self):
		self.assertTrue(limit_przekroczony(4))

	def test_wlasny_limit(self):
		self.assertFalse(limit_przekroczony(10, limit=10))
		self.assertTrue(limit_przekroczony(11, limit=10))


if __name__ == "__main__":
	unittest.main()


class TestPonowneZgloszenie(unittest.TestCase):
	def setUp(self):
		self.nowy = zbuduj_leada_z_webhooka(
			ladunek(kampania="GORZÓW", facebook_lead_id="B22", produkt="PV", posiada_pv="Tak"), DZIS
		)

	def test_format_linii(self):
		linia = linia_ponownego_zgloszenia(self.nowy)
		self.assertTrue(linia.startswith("Ponowne zgłoszenie FB 2026-10-20 (lead FB B22): "))
		self.assertTrue(linia.endswith(self.nowy["custom_uwagi_import"]))

	def test_juz_scalone_trafienie_i_pudlo(self):
		uwagi_ist = "stare | " + linia_ponownego_zgloszenia(self.nowy)
		self.assertTrue(juz_scalone(uwagi_ist, "B22"))
		self.assertFalse(juz_scalone(uwagi_ist, "B2"))
		self.assertFalse(juz_scalone("stare", "B22"))
		self.assertFalse(juz_scalone(None, "B22"))
		self.assertFalse(juz_scalone("", "B22"))

	def test_prefiks_id_nie_pasuje_do_dluzszego(self):
		self.assertFalse(juz_scalone("Ponowne zgłoszenie FB x (lead FB 1234): y", "123"))

	def test_kampania_z_uwag(self):
		self.assertEqual(kampania_z_uwag(self.nowy["custom_uwagi_import"]), "GORZÓW")
		self.assertEqual(kampania_z_uwag("Zrodlo: Facebook Lead Ads"), "")
		self.assertEqual(kampania_z_uwag(None), "")

	def test_tresc_sladu(self):
		self.assertEqual(
			tresc_sladu_ponownego_zgloszenia(self.nowy), "Ponowne zgłoszenie z Facebooka: GORZÓW"
		)
		bez = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		self.assertEqual(
			tresc_sladu_ponownego_zgloszenia(bez), "Ponowne zgłoszenie z Facebooka: brak kampanii"
		)

	def test_uwagi_dopisane_do_istniejacych(self):
		wynik = pola_do_scalenia({"custom_uwagi_import": "stare uwagi"}, self.nowy)
		czesci = wynik["custom_uwagi_import"].split(SEPARATOR_UWAG, 1)
		self.assertEqual(czesci[0], "stare uwagi")
		self.assertEqual(czesci[1], linia_ponownego_zgloszenia(self.nowy))

	def test_puste_uwagi_istniejace(self):
		for puste in ("", None):
			wynik = pola_do_scalenia({"custom_uwagi_import": puste}, self.nowy)
			self.assertEqual(wynik["custom_uwagi_import"], linia_ponownego_zgloszenia(self.nowy))

	def test_tagi_tylko_gdy_puste(self):
		ist = {"custom_posiadane_produkty": "", "custom_zasady_dotacji": None, "custom_produkt_procesu": ""}
		wynik = pola_do_scalenia(ist, self.nowy)
		self.assertEqual(wynik["custom_posiadane_produkty"], "PV")
		self.assertEqual(wynik["custom_zasady_dotacji"], "Nowe zasady")
		self.assertNotIn("custom_produkt_procesu", wynik)

	def test_tagi_wypelnione_zostaja(self):
		ist = {
			"custom_posiadane_produkty": "ME",
			"custom_zasady_dotacji": "Stare zasady",
			"custom_produkt_procesu": "PC",
		}
		wynik = pola_do_scalenia(ist, self.nowy)
		self.assertEqual(list(wynik), ["custom_uwagi_import"])

	def test_nowy_bez_tagu_nie_zapisuje_pustego(self):
		nowy = zbuduj_leada_z_webhooka(ladunek(posiada_pv="", system_rozliczen="", produkt=""), DZIS)
		wynik = pola_do_scalenia({}, nowy)
		self.assertEqual(list(wynik), ["custom_uwagi_import"])

	def test_nie_dotyka_pol_chronionych_i_nie_mutuje(self):
		ist = {"custom_uwagi_import": "x", "status": "Umówiony", "lead_owner": "a@b.pl"}
		kopia = copy.deepcopy(ist)
		nowy_kopia = copy.deepcopy(self.nowy)
		wynik = pola_do_scalenia(ist, self.nowy)
		for pole in ("status", "lead_owner", "custom_cc", "first_name", "facebook_lead_id", "mobile_no"):
			self.assertNotIn(pole, wynik)
		self.assertEqual(ist, kopia)
		self.assertEqual(self.nowy, nowy_kopia)
