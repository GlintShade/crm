# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kto moze zmieniac doradce szansy (`CRM Deal.deal_owner`) i kto moze nim byc.

Modul celowo nie importuje ``frappe``: logike da sie przetestowac lokalnie.
Odczyt rol i zapis mieszkaja w `crm.api.szansa_doradca` (ops#336).

`deal_owner` ma permlevel 1 (zapis tylko Core Admin), wiec zmiana idzie przez
dedykowany endpoint z wlasna bramka, wzorem `przekaz_handlowcowi` dla leada.
"""

ROLE_ZMIANY_DORADCY: frozenset[str] = frozenset(
	{"System Manager", "Volteo Core Admin", "Volteo Backend"}
)
"""Role, ktore moga zmienic doradce szansy."""

ROLA_DORADCY: str = "Volteo D2D Sales"
"""Rola, ktora musi miec konto wskazane jako doradca."""


def czy_moze_zmienic_doradce(uzytkownik: str, role) -> bool:
	"""True dla Administratora albo konta z jedna z `ROLE_ZMIANY_DORADCY`."""
	if not uzytkownik or uzytkownik == "Guest":
		return False
	if uzytkownik == "Administrator":
		return True
	return bool(set(role or ()) & ROLE_ZMIANY_DORADCY)


def czy_dozwolony_doradca(wlaczony: bool, role) -> bool:
	"""True tylko dla wlaczonego konta z rola `Volteo D2D Sales`."""
	return bool(wlaczony) and ROLA_DORADCY in set(role or ())
