# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kto moze zmieniac status CC leada (`CRM Lead.status`).

Modul celowo nie importuje ``frappe``: logike da sie wtedy przetestowac
lokalnie. Odczyt rol i `throw` mieszkaja w `CRMLead.validate()`.

Zasada (uwaga 71, decyzja wlasciciela 2026-10-12): blokada dotyczy WYLACZNIE
konta, ktore ma `Volteo D2D Sales` i zadnej z rol uprzywilejowanych. Inne
role (np. Sales Manager bez D2D) nie sa blokowane.

Uwaga 81 (decyzja wlasciciela 2026-10-31): administracja wskazuje, ktory
handlowiec moze zmieniac status CC. Flaga `User.custom_zmiana_statusu_cc`
zdejmuje blokade dla wybranego handlowca; dla pozostalych decyduja role.
"""

ROLE_ZMIANY_STATUSU_CC: frozenset[str] = frozenset(
	{"Volteo Call Center", "Volteo Backend", "Volteo Core Admin", "System Manager"}
)
"""Role, ktore zawsze moga zmieniac status CC."""

ROLA_HANDLOWCA: str = "Volteo D2D Sales"
"""Rola handlowca, ktorej (samej) zmiana statusu CC jest zablokowana."""


def lead_bezposredni_wlasny(user: str, przydzial_bezposredni, lead_owner) -> bool:
	"""True, gdy lead ma znacznik reguly bezposredniej i jego wlascicielem jest `user`.

	`przydzial_bezposredni` to `CRM Lead.custom_przydzial_bezposredni` (Check, moze
	przyjsc jako 0/1, "0"/"1" albo None, gdy pola jeszcze nie ma w bazie).
	"""
	if not user or not lead_owner or user != lead_owner:
		return False
	try:
		return int(przydzial_bezposredni or 0) == 1
	except (TypeError, ValueError):
		return False


def czy_moze_zmienic_status_cc(
	user: str,
	roles,
	flaga_uzytkownika: bool = False,
	lead_bezposredni_wlasny: bool = False,
) -> bool:
	"""True, gdy `user` z rolami `roles` wolno zmienic status CC leada.

	`flaga_uzytkownika` to `User.custom_zmiana_statusu_cc` (uwaga 81).
	`lead_bezposredni_wlasny` (ops#351): lead ma `custom_przydzial_bezposredni = 1`
	i `lead_owner == user` (patrz `lead_bezposredni_wlasny()` wyzej); wtedy
	handlowiec zmienia status tego leada.
	"""
	if user == "Administrator":
		return True
	if flaga_uzytkownika or lead_bezposredni_wlasny:
		return True
	zbior = set(roles or ())
	if zbior & ROLE_ZMIANY_STATUSU_CC:
		return True
	return ROLA_HANDLOWCA not in zbior
