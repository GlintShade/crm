import unittest

from crm.volteo_lista_szans import niedozwolone_klucze_filtrow

PERMITTED = {"name", "status", "deal_owner", "_assign", "_liked_by", "custom_rodzaj_umowy"}


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


if __name__ == "__main__":
	unittest.main()
