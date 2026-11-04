# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Decyzja: czy pominac zakladanie kontaktu-cienia uzytkownika systemowego (ops#327).

Modul frappe-free. Frappe przy kazdym zapisie ``User`` kolejkuje ``create_contact``,
a fork i tak usuwal taki kontakt (``crm.api.contact.delete_shadow_contact``).
Zamiast wstawiac i kasowac, nie wstawiamy go wcale.
"""

POMIJANE_KONTA = ("Administrator", "Guest")
TYP_UZYTKOWNIKA_SYSTEMOWEGO = "System User"


def czy_pominac_kontakt_cien(user, user_type, enabled, ma_linki, wymuszony):
	"""True, gdy Contact jest kontaktem-cieniem uzytkownika systemowego.

	``enabled`` jest przyjmowane, ale celowo nie wplywa na wynik: kontakt-cien
	konta wylaczonego jest tak samo niechciany (``delete_shadow_contact`` tez nie
	patrzy na ``enabled``), a wylaczony pracownik nie ma wracac na liste Klienci.
	"""
	if wymuszony:
		return False
	if not user or user in POMIJANE_KONTA:
		return False
	if user_type != TYP_UZYTKOWNIKA_SYSTEMOWEGO:
		return False
	if ma_linki:
		return False
	return True
