import unittest

from crm.volteo_lista_szans import (
	FILTER_FIELDS_DEAL,
	SORT_FIELDS_DEAL,
	niedozwolone_klucze_filtrow,
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
		filters = [["status"], ["a", "b", "c", "d", "e"]]
		wynik = niedozwolone_klucze_filtrow(filters, PERMITTED)
		self.assertEqual(wynik, [["status"], ["a", "b", "c", "d", "e"]])

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


if __name__ == "__main__":
	unittest.main()
