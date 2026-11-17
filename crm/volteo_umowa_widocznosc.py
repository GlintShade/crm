# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Frappe-free decision rule for access to `Volteo Umowa` (ops#380).

Read: whoever can see the parent deal can read its contract (and download
its private files). Write through the generic API is closed for non-bypass
users: the only thing they may do is create the record (author, with write
access to the deal). Every other write-type access (write, delete, submit...)
is denied, also for the author: a rep saves the form only through
`crm.api.umowa.volteo_umowa_save`, which authorises the author and the assigned
rep itself. Reason: the author used to clear `autenti_status` with
`frappe.client.set_value` and so bypassed the signed-form lock (ops#371).
"""

# Access types treated as read; everything else is denied, except `create`
# (see `decyzja`).
PTYPY_ODCZYTU = frozenset({"read", "select", "report", "export", "print", "email", "share"})

# Marker read by the ops script `ops/crm-umowa-widocznosc.py` before it removes
# `if_owner` from the DocPerm of `Volteo D2D Sales`. Without this version of the
# hook, removing `if_owner` would open write to every rep who sees the deal.
# Since ops#380 round 3 the rule is stricter than the name says (no generic
# write at all, not even for the author), so the guarantee still holds.
ZAPIS_TYLKO_AUTOR = True
ZAPIS_TYLKO_PRZEZ_API = True


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
	if ptype != "create":
		return False
	return bool(moze_pisac_szanse) and czy_autor(user, autor)
