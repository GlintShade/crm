import unittest

from crm.volteo_lista_szans import (
	FILTER_FIELDS_DEAL,
	FILTER_FIELDS_LEAD,
	POLA_ZAWSZE_DOZWOLONE,
	SORT_FIELDS_DEAL,
	SORT_FIELDS_LEAD,
	niedozwolone_klucze_filtrow,
	podstaw_dzis,
)

PERMITTED = {"name", "status", "deal_owner", "_assign", "_liked_by", "custom_rodzaj_umowy"}

# Lustrzane odbicie nazw pol standardowych, ktore `crm.api.doc` faktycznie
# zna (sort_options' `standard_fields` + get_filterable_fields' `standard_fields`,
# `crm/api/doc.py`) — uzywane tylko do sprawdzenia, ze allowlisty ops#81
# odwoluja sie wylacznie do pol, ktore `doc.py` potrafi rozwiazac bez meta
# doctype'u (poza tym owe pola sa i tak dozwolone przez `_pola_dozwolone` z
# racji `_POLA_ZAWSZE_DOZWOLONE`).
STANDARDOWE_POLA_DOC_PY = frozenset(
	{
		"name",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"_user_tags",
		"_liked_by",
		"_comments",
		"_assign",
	}
)


class TestVolteoListaSzans(unittest.TestCase):
	def test_a_puste_filtry_nic_nie_zwracaja(self: "TestVolteoListaSzans") -> None:
		self.assertEqual(niedozwolone_klucze_filtrow(None, PERMITTED), [])
		self.assertEqual(niedozwolone_klucze_filtrow({}, PERMITTED), [])
		self.assertEqual(niedozwolone_klucze_filtrow([], PERMITTED), [])

	def test_b_dict_same_dozwolone_pola(self: "TestVolteoListaSzans") -> None:
		filters = {"status": "Lead", "deal_owner": "@me", "name": ["like", "PRO/%"]}
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), [])

	def test_c_dict_z_niedozwolonym_polem(self: "TestVolteoListaSzans") -> None:
		filters = {"status": "Lead", "custom_koszty_zysk_plan": [">", 0]}
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED), ["custom_koszty_zysk_plan"]
		)

	def test_d_dict_wiele_niedozwolonych_zachowuje_kolejnosc(self: "TestVolteoListaSzans") -> None:
		filters = {
			"custom_koszty_zysk_plan": [">", 0],
			"status": "Lead",
			"custom_cp_prowizja_handlowa": [">", 0],
		}
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED),
			["custom_koszty_zysk_plan", "custom_cp_prowizja_handlowa"],
		)

	def test_e_lista_trojek_fieldname_operator_wartosc(self: "TestVolteoListaSzans") -> None:
		filters = [["status", "=", "Lead"], ["custom_koszty_zysk_plan", ">", 0]]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED), ["custom_koszty_zysk_plan"]
		)

	def test_f_lista_czworek_doctype_fieldname_operator_wartosc(self: "TestVolteoListaSzans") -> None:
		filters = [
			["CRM Deal", "status", "=", "Lead"],
			["CRM Deal", "custom_cp_nadprowizja_manager", ">", 0],
		]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED),
			["custom_cp_nadprowizja_manager"],
		)

	def test_f2_lista_piatek_doctype_fieldname_operator_wartosc_hidden(
		self: "TestVolteoListaSzans",
	) -> None:
		# Format wysylany przez Desk (/app) dla kazdego filtra listy:
		# [doctype, fieldname, operator, wartosc, hidden]. Regresja ops#124.
		filters = [
			["CRM Deal", "status", "=", "Lead", False],
			["CRM Deal", "custom_cp_nadprowizja_manager", ">", 0, True],
		]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED),
			["custom_cp_nadprowizja_manager"],
		)

	def test_f3_lista_szostek_i_wiecej_nadal_pole_na_indeksie_1(
		self: "TestVolteoListaSzans",
	) -> None:
		# Rdzen (frappe.utils.data.get_filter) obcina wszystko od piatego
		# elementu wzwyz do pierwszych 4. Nazwa pola to zawsze f[1]
		# niezaleznie od tego, ile elementow jest za wartoscia.
		filters = [["CRM Deal", "status", "=", "Lead", False, "cos-jeszcze", 123]]
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), [])

	def test_f4_regresja_desk_converted_crm_lead(self: "TestVolteoListaSzans") -> None:
		# Dokladny wpis z symptomu ops#124: Administrator w /app/crm-lead
		# dostawal "Brak uprawnien do filtrowania po polu ['CRM Lead',
		# 'converted', '=', 0, False]" bo caly wpis piatkowy byl traktowany
		# jako jeden niedozwolony "klucz".
		permitted = PERMITTED | {"converted"}
		filters = [["CRM Lead", "converted", "=", 0, False]]
		self.assertEqual(niedozwolone_klucze_filtrow(filters, permitted, doctype="CRM Lead"), [])

	def test_f5_permlevel_pole_w_piatce_nadal_odrzucone(self: "TestVolteoListaSzans") -> None:
		# Kryterium akceptacji ops#124: filtr po polu permlevel 2 w formie
		# piatkowej Desk musi zostac odrzucony tak samo jak w formie czworkowej.
		filters = [["CRM Lead", "custom_cc", "=", "x", False]]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED, doctype="CRM Lead"),
			["custom_cc"],
		)

	def test_f6_inny_doctype_w_elemencie_0_zawsze_niedozwolony_gdy_doctype_podany(
		self: "TestVolteoListaSzans",
	) -> None:
		# ops#124: wpis wskazujacy INNY doctype niz filtrowany (JOIN po
		# tabeli podrzednej) jest odrzucany bez wzgledu na to, czy nazwa pola
		# akurat pasuje do `permitted` glownego doctype'u. Ten modul nie zna
		# allowlisty drugiego doctype'u i nie moze bezpiecznie zweryfikowac
		# takiego wpisu.
		filters = [["Volteo Zestaw Item", "status", "=", "Lead"]]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED, doctype="CRM Deal"),
			["status"],
		)

	def test_f7_inny_doctype_dozwolony_gdy_doctype_nie_podany_wstecznie(
		self: "TestVolteoListaSzans",
	) -> None:
		# Bez `doctype` (domyslne None, zachowanie sprzed ops#124) porownanie
		# jest pomijane, sprawdzane jest tylko pole.
		filters = [["Volteo Zestaw Item", "status", "=", "Lead"]]
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), [])

	def test_g_krotki_rownowazne_listom(self: "TestVolteoListaSzans") -> None:
		filters = (("status", "=", "Lead"), ("custom_koszty_json", "=", "{}"))
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), ["custom_koszty_json"])

	def test_h_klucz_z_kropka_zawsze_niedozwolony(self: "TestVolteoListaSzans") -> None:
		# "status" jest w PERMITTED, ale dostep przez join ("user.status") omija
		# ograniczenie permlevel niezaleznie od tego, czy "status" samo w sobie
		# jest dozwolone — zawsze blokujemy kropke.
		filters = {"user.status": "Lead"}
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), ["user.status"])

	def test_i_klucz_nie_string_zawsze_niedozwolony(self: "TestVolteoListaSzans") -> None:
		filters = [[123, "=", "Lead"]]
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), [123])

	def test_j_wpis_o_nieoczekiwanym_ksztalcie_niedozwolony(self: "TestVolteoListaSzans") -> None:
		# 0/1/2 elementy. Rdzen sam odrzucilby taki filtr jako niepoprawny
		# (frappe.utils.data.get_filter rzuca dla dlugosci innej niz 3 i
		# innej niz >=4); 4-lub-wiecej i dokladnie 3 to teraz ROZPOZNANE
		# ksztalty (patrz test_f/test_f2/test_f3), nie "nieoczekiwane".
		filters = [[], ["status"], ["a", "b"]]
		wynik = niedozwolone_klucze_filtrow(filters, PERMITTED)
		self.assertEqual(wynik, [[], ["status"], ["a", "b"]])

	def test_k_zagniezdzone_dicty_w_liscie(self: "TestVolteoListaSzans") -> None:
		filters = [{"status": "Lead"}, {"custom_koszty_zysk_plan": [">", 0]}]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED), ["custom_koszty_zysk_plan"]
		)

	def test_l_specjalne_pola_at_me_assign_liked_by_dozwolone(self: "TestVolteoListaSzans") -> None:
		filters = {
			"deal_owner": "@me",
			"_assign": ["like", "%x%"],
			"_liked_by": ["like", "%@me%"],
			"name": ["like", "PRO/%"],
		}
		self.assertEqual(niedozwolone_klucze_filtrow(filters, PERMITTED), [])

	def test_m_duplikaty_niedozwolonych_kluczy_bez_powtorzen(self: "TestVolteoListaSzans") -> None:
		filters = [
			["custom_koszty_zysk_plan", ">", 0],
			["custom_koszty_zysk_plan", "<", 100],
		]
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, PERMITTED), ["custom_koszty_zysk_plan"]
		)

	def test_n_permitted_jako_lista_dziala_tak_samo_jak_zbior(self: "TestVolteoListaSzans") -> None:
		filters = {"status": "Lead", "custom_koszty_zysk_plan": [">", 0]}
		self.assertEqual(
			niedozwolone_klucze_filtrow(filters, list(PERMITTED)),
			["custom_koszty_zysk_plan"],
		)

	def test_o_nie_mutuje_wejsciowego_dict(self: "TestVolteoListaSzans") -> None:
		filters = {"status": "Lead", "custom_koszty_zysk_plan": [">", 0]}
		przed = dict(filters)
		niedozwolone_klucze_filtrow(filters, PERMITTED)
		self.assertEqual(filters, przed)

	def test_p_nie_mutuje_wejsciowej_listy(self: "TestVolteoListaSzans") -> None:
		filters = [["status", "=", "Lead"], ["custom_koszty_zysk_plan", ">", 0]]
		przed = [list(wpis) for wpis in filters]
		niedozwolone_klucze_filtrow(filters, PERMITTED)
		self.assertEqual(filters, przed)

	def test_q_nie_mutuje_permitted(self: "TestVolteoListaSzans") -> None:
		permitted = set(PERMITTED)
		przed = set(permitted)
		niedozwolone_klucze_filtrow({"custom_koszty_zysk_plan": [">", 0]}, permitted)
		self.assertEqual(permitted, przed)


class TestAllowlistySzans(unittest.TestCase):
	"""Allowlisty sortowania/filtrow listy szans dla CRM Deal (ops#81)."""

	def _sprawdz_ksztalt(
		self: "TestAllowlistySzans", nazwa: str, allowlist: tuple
	) -> None:
		for wpis in allowlist:
			self.assertIsInstance(wpis, tuple, f"{nazwa}: {wpis!r} nie jest krotka")
			self.assertEqual(len(wpis), 2, f"{nazwa}: {wpis!r} nie ma dwoch elementow")
			fieldname, etykieta = wpis
			self.assertIsInstance(fieldname, str, f"{nazwa}: fieldname {wpis!r}")
			self.assertIsInstance(
				etykieta, (str, type(None)), f"{nazwa}: etykieta {wpis!r}"
			)

	def test_a_sort_fields_deal_ksztalt_par(self: "TestAllowlistySzans") -> None:
		self._sprawdz_ksztalt("SORT_FIELDS_DEAL", SORT_FIELDS_DEAL)

	def test_b_filter_fields_deal_ksztalt_par(self: "TestAllowlistySzans") -> None:
		self._sprawdz_ksztalt("FILTER_FIELDS_DEAL", FILTER_FIELDS_DEAL)

	def test_c_sort_fields_deal_bez_duplikatow(self: "TestAllowlistySzans") -> None:
		fieldnames = [fieldname for fieldname, _ in SORT_FIELDS_DEAL]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))

	def test_d_filter_fields_deal_bez_duplikatow(self: "TestAllowlistySzans") -> None:
		fieldnames = [fieldname for fieldname, _ in FILTER_FIELDS_DEAL]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))

	def test_e_sort_fields_deal_liczba_i_kolejnosc(self: "TestAllowlistySzans") -> None:
		self.assertEqual(len(SORT_FIELDS_DEAL), 8)
		self.assertEqual(
			[fieldname for fieldname, _ in SORT_FIELDS_DEAL],
			[
				"modified",
				"creation",
				"custom_etap_nr",
				"lead_name",
				"deal_owner",
				"deal_value",
				"custom_rodzaj_umowy",
				"custom_install_postal_code",
			],
		)

	def test_f_filter_fields_deal_liczba_i_kolejnosc(self: "TestAllowlistySzans") -> None:
		self.assertEqual(len(FILTER_FIELDS_DEAL), 14)
		self.assertEqual(
			[fieldname for fieldname, _ in FILTER_FIELDS_DEAL],
			[
				"custom_rodzaj_umowy",
				"status",
				"deal_owner",
				"lead_name",
				"mobile_no",
				"email",
				"custom_install_city",
				"custom_install_postal_code",
				"custom_voivodeship",
				"deal_value",
				"modified",
				"creation",
				"closed_date",
				"_assign",
			],
		)

	def test_g_pola_standardowe_uzyte_w_sort_fields_sa_znane_doc_py(
		self: "TestAllowlistySzans",
	) -> None:
		# "modified" i "creation" nie sa DocFieldami CRM Deal — doc.py rozwiazuje
		# je przez swoja wlasna liste standard_fields, a nie przez meta.
		for fieldname in ("modified", "creation"):
			self.assertIn(fieldname, STANDARDOWE_POLA_DOC_PY)
			self.assertIn(fieldname, [f for f, _ in SORT_FIELDS_DEAL])

	def test_h_pola_standardowe_uzyte_w_filter_fields_sa_znane_doc_py(
		self: "TestAllowlistySzans",
	) -> None:
		for fieldname in ("modified", "creation", "_assign"):
			self.assertIn(fieldname, STANDARDOWE_POLA_DOC_PY)
			self.assertIn(fieldname, [f for f, _ in FILTER_FIELDS_DEAL])

	def test_i_etykiety_nadpisane_tam_gdzie_oczekiwane(self: "TestAllowlistySzans") -> None:
		sort_by_field = dict(SORT_FIELDS_DEAL)
		self.assertEqual(sort_by_field["modified"], "Ostatnia zmiana")
		self.assertEqual(sort_by_field["creation"], "Data utworzenia")
		self.assertEqual(sort_by_field["custom_etap_nr"], "Etap")
		self.assertIsNone(sort_by_field["lead_name"])

		filter_by_field = dict(FILTER_FIELDS_DEAL)
		self.assertEqual(filter_by_field["status"], "Etap")
		self.assertEqual(filter_by_field["_assign"], "Przypisano do")
		self.assertIsNone(filter_by_field["custom_rodzaj_umowy"])


def _sprawdz_ksztalt_par(test_case: unittest.TestCase, nazwa: str, allowlist: tuple) -> None:
	"""Wspolny ksztalt allowlist ops#81/ops#94: krotka par (fieldname, etykieta_lub_None)."""
	for wpis in allowlist:
		test_case.assertIsInstance(wpis, tuple, f"{nazwa}: {wpis!r} nie jest krotka")
		test_case.assertEqual(len(wpis), 2, f"{nazwa}: {wpis!r} nie ma dwoch elementow")
		fieldname, etykieta = wpis
		test_case.assertIsInstance(fieldname, str, f"{nazwa}: fieldname {wpis!r}")
		test_case.assertIsInstance(etykieta, (str, type(None)), f"{nazwa}: etykieta {wpis!r}")


class TestAllowlistyLeadow(unittest.TestCase):
	"""Allowlisty sortowania/filtrow listy leadow dla CRM Lead (ops#94)."""

	def test_a_sort_fields_lead_ksztalt_par(self: "TestAllowlistyLeadow") -> None:
		_sprawdz_ksztalt_par(self, "SORT_FIELDS_LEAD", SORT_FIELDS_LEAD)

	def test_b_filter_fields_lead_ksztalt_par(self: "TestAllowlistyLeadow") -> None:
		_sprawdz_ksztalt_par(self, "FILTER_FIELDS_LEAD", FILTER_FIELDS_LEAD)

	def test_c_sort_fields_lead_bez_duplikatow(self: "TestAllowlistyLeadow") -> None:
		fieldnames = [fieldname for fieldname, _ in SORT_FIELDS_LEAD]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))

	def test_d_filter_fields_lead_bez_duplikatow(self: "TestAllowlistyLeadow") -> None:
		fieldnames = [fieldname for fieldname, _ in FILTER_FIELDS_LEAD]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))

	def test_e_sort_fields_lead_liczba_i_kolejnosc(self: "TestAllowlistyLeadow") -> None:
		self.assertEqual(len(SORT_FIELDS_LEAD), 8)
		self.assertEqual(
			[fieldname for fieldname, _ in SORT_FIELDS_LEAD],
			[
				"modified",
				"creation",
				"status",
				"lead_name",
				"lead_owner",
				"custom_cc",
				"custom_kolejny_kontakt",
				"custom_termin_spotkania",
			],
		)

	def test_f_filter_fields_lead_liczba_i_kolejnosc(self: "TestAllowlistyLeadow") -> None:
		self.assertEqual(len(FILTER_FIELDS_LEAD), 21)
		self.assertEqual(
			[fieldname for fieldname, _ in FILTER_FIELDS_LEAD],
			[
				"status",
				"custom_status_handlowy",
				"custom_cc",
				"lead_owner",
				"lead_name",
				"mobile_no",
				"custom_zasady_dotacji",
				"custom_posiadane_produkty",
				"custom_install_address",
				"custom_nr_domu",
				"custom_install_postal_code",
				"custom_install_city",
				"custom_voivodeship",
				"custom_powiat",
				"custom_status_zrodla",
				"custom_import_source",
				"custom_kolejny_kontakt",
				"custom_termin_spotkania",
				"modified",
				"creation",
				"_assign",
			],
		)

	def test_g_pola_standardowe_uzyte_w_sort_fields_sa_znane_doc_py(
		self: "TestAllowlistyLeadow",
	) -> None:
		for fieldname in ("modified", "creation"):
			self.assertIn(fieldname, STANDARDOWE_POLA_DOC_PY)
			self.assertIn(fieldname, [f for f, _ in SORT_FIELDS_LEAD])

	def test_h_pola_standardowe_uzyte_w_filter_fields_sa_znane_doc_py(
		self: "TestAllowlistyLeadow",
	) -> None:
		for fieldname in ("modified", "creation", "_assign"):
			self.assertIn(fieldname, STANDARDOWE_POLA_DOC_PY)
			self.assertIn(fieldname, [f for f, _ in FILTER_FIELDS_LEAD])

	def test_i_etykiety_nadpisane_tam_gdzie_oczekiwane(self: "TestAllowlistyLeadow") -> None:
		sort_by_field = dict(SORT_FIELDS_LEAD)
		self.assertEqual(sort_by_field["modified"], "Ostatnia zmiana")
		self.assertEqual(sort_by_field["status"], "Status CC")
		self.assertEqual(sort_by_field["custom_cc"], "Przypisany CC")

		filter_by_field = dict(FILTER_FIELDS_LEAD)
		self.assertEqual(filter_by_field["status"], "Status CC")
		self.assertEqual(filter_by_field["_assign"], "Przypisano do")
		self.assertIsNone(filter_by_field["custom_status_handlowy"])

	def test_j_email_poza_obiema_allowlistami(self: "TestAllowlistyLeadow") -> None:
		# ops#94: lista leadow jest "bez e-maila" (kolumny i filtry), patrz
		# komentarz w crm.volteo_lista_szans nad SORT_FIELDS_LEAD.
		self.assertNotIn("email", [f for f, _ in SORT_FIELDS_LEAD])
		self.assertNotIn("email", [f for f, _ in FILTER_FIELDS_LEAD])


class TestPolaZawszeDozwolone(unittest.TestCase):
	"""`POLA_ZAWSZE_DOZWOLONE` (ops#80 follow-up) — bezpiecznik uzywany przez
	`crm.api.doc._pola_dozwolone`. Musi zawierac zarowno standardowe pola
	dokumentu, jak i `frappe.model.child_table_fields`
	(`parent`/`parenttype`/`parentfield`) — bez tych trzech kazdy filtr
	odczytu tabeli podrzednej bez `parenttype` (np. `Volteo Zestaw Item` z
	`ZestawTab.vue`) jest odrzucany, co bylo przyczyna regresji „brak
	zestawu"."""

	def test_a_zawiera_pola_tabeli_podrzednej(self: "TestPolaZawszeDozwolone") -> None:
		for fieldname in ("parent", "parenttype", "parentfield"):
			self.assertIn(fieldname, POLA_ZAWSZE_DOZWOLONE)

	def test_b_zawiera_standardowe_pola_dokumentu(self: "TestPolaZawszeDozwolone") -> None:
		for fieldname in ("_assign", "name", "modified"):
			self.assertIn(fieldname, POLA_ZAWSZE_DOZWOLONE)

	def test_c_jest_frozenset(self: "TestPolaZawszeDozwolone") -> None:
		self.assertIsInstance(POLA_ZAWSZE_DOZWOLONE, frozenset)



class TestPodstawDzis(unittest.TestCase):
	"""`podstaw_dzis` (issue #128, analogiczne do `_podstaw_me` w
	`crm.api.doc` dla "@me") -- rdzen frappe-free, `dzis`/`jutro`/
	`czy_datetime` sa tu wstrzykiwane wprost, tak jak w produkcji przekazuje
	je `crm.api.doc._podstaw_dzis` (`dzis = nowdate()`,
	`jutro = add_days(dzis, 1)`, `czy_datetime` z `frappe.get_meta`)."""

	DZIS = "2026-09-10"
	JUTRO = "2026-09-11"

	def _czy_datetime(self: "TestPodstawDzis", pole: str) -> bool:
		# Lustrzane odbicie realnych pol leadow: custom_kolejny_kontakt jest
		# Date, custom_termin_spotkania i "modified" sa Datetime.
		return pole in {"custom_termin_spotkania", "modified"}

	def test_a_skalar(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": "@dzis"}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": self.DZIS})

	def test_b_operator_wartosc_pole_date(self: "TestPodstawDzis") -> None:
		# custom_kolejny_kontakt to Date, nie Datetime -- operator "<=" zostaje
		# bez zmian, tylko wartosc podstawiona.
		filtry = {"custom_kolejny_kontakt": ["<=", "@dzis"]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": ["<=", self.DZIS]})

	def test_c_operator_lte_na_datetime_przesuwa_na_jutro(self: "TestPodstawDzis") -> None:
		# custom_termin_spotkania to Datetime -- "<= @dzis" objelby TYLKO
		# polnoc, wiec operator zamieniany na "<" z "jutro".
		filtry = {"custom_termin_spotkania": ["<=", "@dzis"]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_termin_spotkania": ["<", self.JUTRO]})

	def test_d_operator_gte_na_datetime_zostaje_bez_zmian(self: "TestPodstawDzis") -> None:
		# ">=" na Datetime poprawnie obejmuje caly dzien od polnocy -- tylko
		# "<=" dostaje specjalne traktowanie.
		filtry = {"custom_termin_spotkania": [">=", "@dzis"]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_termin_spotkania": [">=", self.DZIS]})

	def test_e_between_oba_konce(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": ["between", ["@dzis", "@dzis"]]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": ["between", [self.DZIS, self.DZIS]]})

	def test_f_between_jeden_koniec(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": ["between", ["@dzis", "2026-12-31"]]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": ["between", [self.DZIS, "2026-12-31"]]})

	def test_g_in_lista(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": ["in", ["@dzis", "2026-01-01"]]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": ["in", [self.DZIS, "2026-01-01"]]})

	def test_h_not_in_lista(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": ["not in", ["@dzis"]]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, {"custom_kolejny_kontakt": ["not in", [self.DZIS]]})

	def test_i_brak_literalu_bez_zmian(self: "TestPodstawDzis") -> None:
		filtry = {
			"status": "Odłożony",
			"deal_owner": "@me",
			"lead_name": ["like", "%Kowalski%"],
			"creation": ["between", ["2026-01-01", "2026-01-31"]],
		}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, filtry)

	def test_j_lista_niestandardowej_dlugosci_bez_zmian(self: "TestPodstawDzis") -> None:
		# Ksztalt spoza czterech udokumentowanych (skalar / [op, wartosc] /
		# between / in) -- wraca bez zmian, bez proby zgadywania.
		filtry = {"custom_kolejny_kontakt": ["@dzis"]}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(wynik, filtry)

	def test_k_none_bez_zmian(self: "TestPodstawDzis") -> None:
		filtry = {"custom_kolejny_kontakt": None}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertIsNone(wynik["custom_kolejny_kontakt"])

	def test_l_nie_mutuje_oryginalu(self: "TestPodstawDzis") -> None:
		oryginalna_lista = ["between", ["@dzis", "2026-12-31"]]
		filtry = {"custom_kolejny_kontakt": oryginalna_lista}
		podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertEqual(oryginalna_lista, ["between", ["@dzis", "2026-12-31"]])
		self.assertEqual(filtry, {"custom_kolejny_kontakt": oryginalna_lista})

	def test_m_zwraca_nowy_dict(self: "TestPodstawDzis") -> None:
		filtry = {"status": "Odłożony"}
		wynik = podstaw_dzis(filtry, self.DZIS, self.JUTRO, self._czy_datetime)
		self.assertIsNot(wynik, filtry)

	def test_n_puste_filtry(self: "TestPodstawDzis") -> None:
		self.assertEqual(podstaw_dzis({}, self.DZIS, self.JUTRO, self._czy_datetime), {})

if __name__ == "__main__":
	unittest.main()
