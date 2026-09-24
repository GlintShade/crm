import unittest

from crm.volteo_kredyt import ETYKIETY_POL, ETYKIETY_WNIOSKODAWCY, POLA_WNIOSKODAWCY

# Mirror of crm/api/kredyt.py's `_DANE_POLA_DOZWOLONE` (the 53 fieldnames
# `volteo_kredyt_save` accepts). Retyped independently rather than imported:
# `crm.api.kredyt` needs `frappe`, which is not installed on this machine
# (same reason `crm/volteo_kredyt.py` stays frappe-free, per its module
# docstring). A change to `_DANE_POLA_DOZWOLONE` requires the matching
# change here.
#
# Grown by the 10 `wnioskodawca_*` fields (ops#157, `POLA_WNIOSKODAWCY`) so
# this allowlist mirror covers the applicant-data canon too. This mirror is
# ahead of the real `crm.api.kredyt._DANE_POLA_DOZWOLONE` until the sibling
# issues land: A1 (schema for the `wnioskodawca_*` custom fields on
# `Volteo Kredyt`, in `ops/crm-kredyt.py`, a separate repo) and A4 (wiring
# `crm.api.kredyt` itself to accept and read these fields). Deliberate: this
# issue is the frappe-free canon only, per its own scope.
_DANE_POLA_DOZWOLONE = (
	"miejsce_urodzenia",
	"rodzaj_dokumentu",
	"seria_numer_dokumentu",
	"data_wydania_dokumentu",
	"data_waznosci_dokumentu",
	"adres_zameldowania_taki_sam",
	"adres_zameldowania",
	"adres_korespondencji_taki_sam",
	"adres_korespondencji",
	"wyksztalcenie",
	"stan_cywilny",
	"liczba_osob_na_utrzymaniu",
	"kwota_800_plus",
	"dochod_wspolmalzonka",
	"zrodlo_dochodu_malzonka",
	"oplaty_miesieczne",
	"suma_zobowiazan",
	"numer_rachunku",
	"praca_wlaczone",
	"praca_forma",
	"praca_okres",
	"praca_okres_od",
	"praca_okres_do",
	"praca_nip",
	"praca_nazwa_zakladu",
	"praca_adres_telefon",
	"praca_kwota_dochodu",
	"emerytura_wlaczone",
	"emerytura_numer_swiadczenia",
	"emerytura_od_kiedy",
	"emerytura_kwota_dochodu",
	"renta_wlaczone",
	"renta_numer_swiadczenia",
	"renta_od_kiedy",
	"renta_kwota_dochodu",
	"dzialalnosc_wlaczone",
	"dzialalnosc_forma_opodatkowania",
	"dzialalnosc_forma_inna",
	"dzialalnosc_nip",
	"dzialalnosc_nazwa",
	"dzialalnosc_adres",
	"dzialalnosc_telefon",
	"dzialalnosc_od_kiedy",
	"dzialalnosc_kwota_dochodu",
	"gospodarstwo_wlaczone",
	"gospodarstwo_nip",
	"gospodarstwo_od_kiedy",
	"gospodarstwo_kwota_dochodu",
	"inne_wlaczone",
	"inne_1_typ",
	"inne_1_kwota",
	"inne_2_typ",
	"inne_2_kwota",
	"wnioskodawca_pesel",
	"wnioskodawca_imiona",
	"wnioskodawca_nazwisko",
	"wnioskodawca_telefon",
	"wnioskodawca_email",
	"wnioskodawca_kod_pocztowy",
	"wnioskodawca_miejscowosc",
	"wnioskodawca_ulica",
	"wnioskodawca_nr_domu",
	"wnioskodawca_nr_lokalu",
)

# Mirror of ops/crm-kredyt.py's `KREDYT_FIELDS` labels (the doctype canon,
# 53 data fields, `deal`/`status`/section breaks excluded). Same
# independent-retype rationale as `_DANE_POLA_DOZWOLONE` above: a relabel in
# ops/crm-kredyt.py requires the matching change here AND in
# `crm/volteo_kredyt.py`'s `ETYKIETY_POL`.
#
# ONE deliberate divergence from ops/crm-kredyt.py (ops#148 acceptance
# criteria): `dzialalnosc_forma_inna`'s doctype label joins its two clauses
# with an em dash (ends in "jaka?" after that dash). This project's
# zero-em-dash rule forbids that in code/tests/comments we write, so the
# canon here (and in ETYKIETY_POL) spells it with a colon instead ("Inna
# forma opodatkowania: jaka?"). Aligning ops/crm-kredyt.py's own label to
# match is a separate, deliberately deferred change (not part of this
# issue); see the final report for ops#148.
_ETYKIETY_KANON_DOCTYPE = {
	"miejsce_urodzenia": "Miejsce urodzenia",
	"rodzaj_dokumentu": "Rodzaj dokumentu tożsamości",
	"seria_numer_dokumentu": "Seria i numer dokumentu tożsamości",
	"data_wydania_dokumentu": "Data wydania dokumentu tożsamości",
	"data_waznosci_dokumentu": "Data ważności dokumentu tożsamości",
	"adres_zameldowania_taki_sam": "Czy adres zamieszkania jest taki sam, jak adres zameldowania?",
	"adres_zameldowania": "Adres zamieszkania",
	"adres_korespondencji_taki_sam": "Czy adres do korespondencji jest taki sam, jak adres zameldowania?",
	"adres_korespondencji": "Adres do korespondencji",
	"wyksztalcenie": "Wykształcenie",
	"stan_cywilny": "Stan cywilny",
	"liczba_osob_na_utrzymaniu": "Liczba osób w gospodarstwie domowym na utrzymaniu",
	"kwota_800_plus": "Kwota świadczenia 800+",
	"dochod_wspolmalzonka": "Deklarowany dochód współmałżonka",
	"zrodlo_dochodu_malzonka": "Źródło dochodu małżonka",
	"oplaty_miesieczne": "Opłaty miesięczne",
	"suma_zobowiazan": "Suma miesięcznych zobowiązań kredytowych i finansowych",
	"numer_rachunku": "Numer rachunku bankowego",
	"praca_wlaczone": "Dochód: umowa o pracę / zlecenie / dzieło",
	"praca_forma": "Forma zatrudnienia",
	"praca_okres": "Okres zatrudnienia",
	"praca_okres_od": "Zatrudnienie od",
	"praca_okres_do": "Zatrudnienie do",
	"praca_nip": "NIP zakładu pracy",
	"praca_nazwa_zakladu": "Nazwa zakładu pracy",
	"praca_adres_telefon": "Adres i numer telefonu zakładu pracy",
	"praca_kwota_dochodu": "Kwota dochodu",
	"emerytura_wlaczone": "Dochód: emerytura",
	"emerytura_numer_swiadczenia": "Numer świadczenia",
	"emerytura_od_kiedy": "Od kiedy przyznane jest świadczenie",
	"emerytura_kwota_dochodu": "Kwota dochodu",
	"renta_wlaczone": "Dochód: renta",
	"renta_numer_swiadczenia": "Numer świadczenia",
	"renta_od_kiedy": "Od kiedy przyznane jest świadczenie",
	"renta_kwota_dochodu": "Kwota dochodu",
	"dzialalnosc_wlaczone": "Dochód: działalność gospodarcza",
	"dzialalnosc_forma_opodatkowania": "Forma opodatkowania",
	"dzialalnosc_forma_inna": "Inna forma opodatkowania: jaka?",
	"dzialalnosc_nip": "NIP firmy",
	"dzialalnosc_nazwa": "Nazwa firmy",
	"dzialalnosc_adres": "Adres firmy",
	"dzialalnosc_telefon": "Numer telefonu do firmy",
	"dzialalnosc_od_kiedy": "Od kiedy prowadzona jest działalność?",
	"dzialalnosc_kwota_dochodu": "Kwota dochodu",
	"gospodarstwo_wlaczone": "Dochód: gospodarstwo rolne",
	"gospodarstwo_nip": "NIP gospodarstwa",
	"gospodarstwo_od_kiedy": "Od kiedy prowadzone jest gospodarstwo?",
	"gospodarstwo_kwota_dochodu": "Kwota dochodu",
	"inne_wlaczone": "Dochód: inne",
	"inne_1_typ": "Typ dochodu (1)",
	"inne_1_kwota": "Kwota dochodu (1)",
	"inne_2_typ": "Typ dochodu (2)",
	"inne_2_kwota": "Kwota dochodu (2)",
	"wnioskodawca_pesel": "PESEL",
	"wnioskodawca_imiona": "Imiona",
	"wnioskodawca_nazwisko": "Nazwisko",
	"wnioskodawca_telefon": "Telefon",
	"wnioskodawca_email": "E-mail",
	"wnioskodawca_kod_pocztowy": "Kod pocztowy",
	"wnioskodawca_miejscowosc": "Miejscowość",
	"wnioskodawca_ulica": "Ulica",
	"wnioskodawca_nr_domu": "Nr domu",
	"wnioskodawca_nr_lokalu": "Nr lokalu",
}


class TestEtykietyKanonZgodneZDozwolonymiPolami(unittest.TestCase):
	def test_a_klucze_etykiet_pokrywaja_sie_z_dozwolonymi_polami(self: "TestEtykietyKanonZgodneZDozwolonymiPolami") -> None:
		self.assertEqual(set(ETYKIETY_POL.keys()), set(_DANE_POLA_DOZWOLONE))

	def test_b_pol_jest_63(self: "TestEtykietyKanonZgodneZDozwolonymiPolami") -> None:
		# 53 pola danych Volteo Kredyt + 10 pól wnioskodawcy (ops#157).
		self.assertEqual(len(_DANE_POLA_DOZWOLONE), 63)
		self.assertEqual(len(ETYKIETY_POL), 63)


class TestEtykietyKanonZgodneZDoctype(unittest.TestCase):
	def test_a_wartosci_zgadzaja_sie_z_kanonem_doctype(self: "TestEtykietyKanonZgodneZDoctype") -> None:
		self.assertEqual(ETYKIETY_POL, _ETYKIETY_KANON_DOCTYPE)

	def test_b_adres_zameldowania_to_adres_zamieszkania(self: "TestEtykietyKanonZgodneZDoctype") -> None:
		# K5 (ops#148): fieldname mówi "zameldowania", ale doctype i papier
		# mówią "zamieszkania". Kanon musi zostać przy brzmieniu doctype'u,
		# decyzja właściciela o docelowym brzmieniu jest otwarta.
		self.assertEqual(ETYKIETY_POL["adres_zameldowania"], "Adres zamieszkania")

	def test_c_suma_zobowiazan_kanon_pelny(self: "TestEtykietyKanonZgodneZDoctype") -> None:
		# K6 (ops#148): kanon (używany w komunikacie blokującym PDF) to pełne
		# brzmienie doctype'u/papieru, nie skrócona etykieta ekranowa.
		self.assertEqual(
			ETYKIETY_POL["suma_zobowiazan"],
			"Suma miesięcznych zobowiązań kredytowych i finansowych",
		)


class TestKanonWnioskodawcy(unittest.TestCase):
	def test_a_pol_jest_10(self: "TestKanonWnioskodawcy") -> None:
		self.assertEqual(len(POLA_WNIOSKODAWCY), 10)
		self.assertEqual(len(ETYKIETY_WNIOSKODAWCY), 10)

	def test_b_klucze_etykiet_pokrywaja_sie_z_polami(self: "TestKanonWnioskodawcy") -> None:
		self.assertEqual(set(ETYKIETY_WNIOSKODAWCY.keys()), set(POLA_WNIOSKODAWCY))

	def test_c_etykiety_wnioskodawcy_sa_domieszane_do_etykiety_pol(self: "TestKanonWnioskodawcy") -> None:
		for pole, etykieta in ETYKIETY_WNIOSKODAWCY.items():
			with self.subTest(pole=pole):
				self.assertEqual(ETYKIETY_POL[pole], etykieta)

	def test_d_kolejnosc_i_tresc_etykiet(self: "TestKanonWnioskodawcy") -> None:
		self.assertEqual(
			POLA_WNIOSKODAWCY,
			(
				"wnioskodawca_pesel",
				"wnioskodawca_imiona",
				"wnioskodawca_nazwisko",
				"wnioskodawca_telefon",
				"wnioskodawca_email",
				"wnioskodawca_kod_pocztowy",
				"wnioskodawca_miejscowosc",
				"wnioskodawca_ulica",
				"wnioskodawca_nr_domu",
				"wnioskodawca_nr_lokalu",
			),
		)
		self.assertEqual(
			[ETYKIETY_WNIOSKODAWCY[pole] for pole in POLA_WNIOSKODAWCY],
			[
				"PESEL",
				"Imiona",
				"Nazwisko",
				"Telefon",
				"E-mail",
				"Kod pocztowy",
				"Miejscowość",
				"Ulica",
				"Nr domu",
				"Nr lokalu",
			],
		)


class TestEtykietyKanonBezMyslnikow(unittest.TestCase):
	def test_a_zero_myslnikow_em_i_en(self: "TestEtykietyKanonBezMyslnikow") -> None:
		# Myślnik em (U+2014) i en (U+2013) zapisane jako escape, nie
		# literał: sam ten plik testowy podlega regule zero-myślników
		# projektu, więc znak nie może wystąpić w źródle jako glif.
		myslnik_em = "\u2014"
		myslnik_en = "\u2013"
		for fieldname, etykieta in ETYKIETY_POL.items():
			with self.subTest(fieldname=fieldname):
				self.assertNotIn(myslnik_em, etykieta)
				self.assertNotIn(myslnik_en, etykieta)


if __name__ == "__main__":
	unittest.main()
