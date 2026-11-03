import unittest

from crm.volteo_panel_boczny import plan_sekcji_utraty

WLASNA = {"name": "powod", "columns": [{"name": "c", "fields": ["lost_reason", "lost_notes"]}]}
WLASNA_DICT = {"name": "powod", "columns": [{"name": "c", "fields": [{"fieldname": "lost_notes"}]}]}
UPSTREAM = {"name": "lost_reason_section", "columns": [{"name": "x", "fields": ["lost_reason"]}]}
KONTAKTY = {"name": "contacts_section", "columns": []}
INNA = {"name": "inna", "columns": [{"name": "c", "fields": ["status"]}]}


class TestPlanSekcjiUtraty(unittest.TestCase):
	def test_wlasna_sekcja_utracony_bez_wstawiania(self):
		self.assertIsNone(plan_sekcji_utraty([INNA, WLASNA], True))

	def test_wlasna_sekcja_pola_dict(self):
		self.assertIsNone(plan_sekcji_utraty([INNA, WLASNA_DICT], True))

	def test_wlasna_sekcja_i_zabladzona_upstream_usuwana(self):
		for utracony in (True, False):
			wynik = plan_sekcji_utraty([INNA, WLASNA, UPSTREAM], utracony)
			self.assertEqual([s["name"] for s in wynik], ["inna", "powod"])

	def test_bez_wlasnej_wstawia_na_poczatek(self):
		wynik = plan_sekcji_utraty([INNA], True)
		self.assertEqual([s["name"] for s in wynik], ["lost_reason_section", "inna"])

	def test_bez_wlasnej_wstawia_po_contacts(self):
		wynik = plan_sekcji_utraty([KONTAKTY, INNA], True)
		self.assertEqual([s["name"] for s in wynik], ["contacts_section", "lost_reason_section", "inna"])

	def test_bez_wlasnej_usuwa_gdy_nie_utracony(self):
		wynik = plan_sekcji_utraty([INNA, UPSTREAM], False)
		self.assertEqual([s["name"] for s in wynik], ["inna"])

	def test_bez_zmian(self):
		self.assertIsNone(plan_sekcji_utraty([INNA], False))
		self.assertIsNone(plan_sekcji_utraty([INNA, UPSTREAM], True))


if __name__ == "__main__":
	unittest.main()
