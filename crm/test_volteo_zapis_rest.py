# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_zapis_rest import czy_zapis_rest


class TestCzyZapisRest(unittest.TestCase):
	def test_put_resource(self):
		self.assertTrue(czy_zapis_rest("PUT", "/api/resource/CRM Lead/CRM-LEAD-1"))

	def test_post_resource(self):
		self.assertTrue(czy_zapis_rest("POST", "/api/resource/CRM Deal"))

	def test_post_v1_resource(self):
		self.assertTrue(czy_zapis_rest("POST", "/api/v1/resource/CRM Deal"))

	def test_get_i_delete_nie_sa_zapisem(self):
		self.assertFalse(czy_zapis_rest("GET", "/api/resource/CRM Lead"))
		self.assertFalse(czy_zapis_rest("DELETE", "/api/resource/CRM Lead/x"))

	def test_v2_nie_blokowany(self):
		self.assertFalse(czy_zapis_rest("PUT", "/api/v2/document/CRM Lead/x"))

	def test_api_method_nie_blokowany(self):
		self.assertFalse(czy_zapis_rest("POST", "/api/method/frappe.client.set_value"))

	def test_wielkosc_liter_metody(self):
		self.assertTrue(czy_zapis_rest("put", "/api/resource/CRM Lead/x"))
		self.assertTrue(czy_zapis_rest("Post", "/api/resource/CRM Lead"))

	def test_puste_wartosci(self):
		self.assertFalse(czy_zapis_rest("", "/api/resource/CRM Lead"))
		self.assertFalse(czy_zapis_rest("PUT", ""))
		self.assertFalse(czy_zapis_rest(None, None))


if __name__ == "__main__":
	unittest.main()
