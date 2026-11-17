"""Widocznosc dzwoneczka `CRM Notification` (ops#375), czysta logika bez frappe.

Powiadomienie jest wylacznie dla adresata (`to_user`). Wszyscy poza
administratorem systemu widza i zmieniaja tylko swoje wiersze. Adapter z
`import frappe` jest w `crm/permissions/notification_visibility.py`.
"""

ROLE_WSZYSTKIE_POWIADOMIENIA = frozenset({"System Manager"})
"""Role, ktore widza powiadomienia wszystkich. Celowo bez `Volteo Backend`."""

PTYPY_BEZ_OGRANICZEN = frozenset({"create"})
"""Tworzenie zostaje bez opinii: powiadomienie powstaje dla kogos innego."""


def czy_widzi_wszystkie(user: str, role) -> bool:
	"""True dla `Administrator` i dla roli z `ROLE_WSZYSTKIE_POWIADOMIENIA`."""
	if user == "Administrator":
		return True
	return bool(set(role or ()) & ROLE_WSZYSTKIE_POWIADOMIENIA)


def czy_adresat(user: str, to_user: str | None) -> bool:
	"""True, gdy `to_user` to ten sam uzytkownik (puste `to_user` nie pasuje)."""
	return bool(user) and bool(to_user) and user == to_user


def decyzja_dokumentu(user: str, role, ptype: str, nazwa: str | None, to_user: str | None) -> bool | None:
	"""Decyzja dla `has_permission`: `False` (odmowa) albo `None` (bez opinii).

	Nigdy nie zwraca `True`, bo pierwszy wynik haka jest ostateczny, a hak nie
	moze nic nadawac ponad DocPerm.
	"""
	if czy_widzi_wszystkie(user, role):
		return None
	if ptype in PTYPY_BEZ_OGRANICZEN:
		return None
	if not nazwa:
		return None
	if czy_adresat(user, to_user):
		return None
	return False
