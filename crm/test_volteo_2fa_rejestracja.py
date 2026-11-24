import unittest

from crm import volteo_2fa_rejestracja as r


class TestOkno(unittest.TestCase):
	def test_koniec_okna_to_24h(self):
		self.assertEqual(r.koniec_okna(1000.0), 1000.0 + 86400)

	def test_okno_otwarte_przed_koncem(self):
		self.assertTrue(r.okno_otwarte(str(2000.0), 1999.0))

	def test_okno_zamkniete_po_koncu_i_w_chwili_konca(self):
		self.assertFalse(r.okno_otwarte("2000", 2000.0))
		self.assertFalse(r.okno_otwarte("2000", 2001.0))

	def test_brak_lub_smieci_to_zamkniete(self):
		for z in (None, "", "abc"):
			self.assertFalse(r.okno_otwarte(z, 1.0))

	def test_qr_tylko_bez_rejestracji_i_w_oknie(self):
		self.assertTrue(r.pokazac_qr(False, "2000", 1.0))
		self.assertFalse(r.pokazac_qr(True, "2000", 1.0))
		self.assertFalse(r.pokazac_qr(False, "2000", 3000.0))
		self.assertFalse(r.pokazac_qr(False, None, 1.0))

	def test_mail_po_rejestracji(self):
		self.assertTrue(r.wyslac_mail_po_rejestracji(True, "2000"))
		self.assertFalse(r.wyslac_mail_po_rejestracji(False, "2000"))
		self.assertFalse(r.wyslac_mail_po_rejestracji(True, None))

	def test_pierwsze_haslo(self):
		self.assertTrue(r.pierwsze_haslo_otwiera_okno(True, False, False))
		self.assertFalse(r.pierwsze_haslo_otwiera_okno(True, True, False))
		self.assertFalse(r.pierwsze_haslo_otwiera_okno(False, False, False))
		self.assertFalse(r.pierwsze_haslo_otwiera_okno(True, False, True))


if __name__ == "__main__":
	unittest.main()
