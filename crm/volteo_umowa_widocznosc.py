# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Frappe-free decision rule for access to `Volteo Umowa` (ops#380).

Read: whoever can see the parent deal can read its contract (and download
its private files). Write through the generic API: only the author of the
record, and only while he still has write access to the deal.
"""

# Access types treated as read; everything else (write, create, delete,
# submit...) is subject to the author rule.
PTYPY_ODCZYTU = frozenset({"read", "select", "report", "export", "print", "email", "share"})

# Marker read by the ops script `ops/crm-umowa-widocznosc.py` before it removes
# `if_owner` from the DocPerm of `Volteo D2D Sales`. Without this version of the
# hook, removing `if_owner` would open write to every rep who sees the deal.
ZAPIS_TYLKO_AUTOR = True


def czy_odczyt(ptype: str) -> bool:
	return ptype in PTYPY_ODCZYTU


def czy_autor(user: str, autor: str | None) -> bool:
	"""Empty author means the document is not saved yet (the current user is
	creating it)."""
	return (not autor) or autor == user


def decyzja(ptype: str, widzi_szanse: bool, moze_pisac_szanse: bool, user: str, autor: str | None) -> bool:
	if not widzi_szanse:
		return False
	if czy_odczyt(ptype):
		return True
	return bool(moze_pisac_szanse) and czy_autor(user, autor)
