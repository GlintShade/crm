import unittest

from crm.volteo_leady_telefon import normalizuj_filtr_telefonu


def _f(wzorzec, op="LIKE"):
	return {"mobile_no": [op, wzorzec]}


class TestNormalizujFiltrTelefonu(unittest.TestCase):
	def test_spacje(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%604 932 720%")), _f("%604932720%"))

	def test_myslniki(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%604-932-720%")), _f("%604932720%"))

	def test_prefiks_48(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%+48 604 932 720%")), _f("%48604932720%"))

	def test_kropki_i_nawiasy(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%(604).932.720%")), _f("%604932720%"))

	def test_same_cyfry_bez_zmian(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%604932720%")), _f("%604932720%"))

	def test_litery_usuniete(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%tel 604%")), _f("%604%"))

	def test_pusty_po_oczyszczeniu_usuwa_klucz(self):
		self.assertEqual(normalizuj_filtr_telefonu({**_f("%- -%"), "status": "Nowy"}), {"status": "Nowy"})

	def test_sam_procent_usuwa_klucz(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%")), {})

	def test_operator_like_malymi_literami(self):
		self.assertEqual(normalizuj_filtr_telefonu(_f("%604 9%", op="like")), _f("%6049%", op="like"))

	def test_inny_operator_bez_zmian(self):
		f = _f("%604 932%", op="not like")
		self.assertEqual(normalizuj_filtr_telefonu(f), f)

	def test_rownosc_bez_zmian(self):
		f = {"mobile_no": "+48 604 932 720"}
		self.assertEqual(normalizuj_filtr_telefonu(f), f)

	def test_inne_pole_bez_zmian(self):
		f = {"first_name": ["LIKE", "%a b%"]}
		self.assertEqual(normalizuj_filtr_telefonu(f), f)

	def test_brak_klucza(self):
		self.assertEqual(normalizuj_filtr_telefonu({"status": "Nowy"}), {"status": "Nowy"})

	def test_nie_mutuje_wejscia(self):
		f = _f("%604 932%")
		normalizuj_filtr_telefonu(f)
		self.assertEqual(f, _f("%604 932%"))

	def test_none(self):
		self.assertEqual(normalizuj_filtr_telefonu(None), {})


if __name__ == "__main__":
	unittest.main()
