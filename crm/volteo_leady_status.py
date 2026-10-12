# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kto moze zmieniac status CC leada (`CRM Lead.status`).

Modul celowo nie importuje ``frappe``: logike da sie wtedy przetestowac
lokalnie. Odczyt rol i `throw` mieszkaja w `CRMLead.validate()`.

Zasada (uwaga 71, decyzja wlasciciela 2026-10-12): blokada dotyczy WYLACZNIE
konta, ktore ma `Volteo D2D Sales` i zadnej z rol uprzywilejowanych. Inne
role (np. Sales Manager bez D2D) nie sa blokowane.
"""

ROLE_ZMIANY_STATUSU_CC: frozenset[str] = frozenset(
	{"Volteo Call Center", "Volteo Backend", "Volteo Core Admin", "System Manager"}
)
"""Role, ktore zawsze moga zmieniac status CC."""

ROLA_HANDLOWCA: str = "Volteo D2D Sales"
"""Rola handlowca, ktorej (samej) zmiana statusu CC jest zablokowana."""


def czy_moze_zmienic_status_cc(user: str, roles) -> bool:
	"""True, gdy `user` z rolami `roles` wolno zmienic status CC leada."""
	if user == "Administrator":
		return True
	zbior = set(roles or ())
	if zbior & ROLE_ZMIANY_STATUSU_CC:
		return True
	return ROLA_HANDLOWCA not in zbior
