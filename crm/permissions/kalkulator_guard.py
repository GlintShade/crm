# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Standing daily guard for the Kalkulator pricing-secrecy doctypes.

`Volteo Komponent` (component costs) and `Volteo Kalkulator Stale` (margin
constants) must NEVER carry a `Volteo D2D Sales` or `Volteo Backend`
permission — those roles must stay limited to System Manager + Volteo Core
Admin only (see the Kalkulator commission-secrecy plan, Part 1b / Part 5 #2).

`Volteo Oferta` is different: D2D and Backend legitimately hold permlevel-0
read (the client-facing quote fields) and that must stay untouched. But its
`base_gross_pln`, `commission_pln`, and `breakdown_json` fields are locked at
permlevel=1 to keep the internal cost/margin breakdown admin-only. So for
Oferta this guard only strips a stray D2D/Backend perm row at permlevel >= 1
— the level that would expose those locked fields — leaving permlevel-0 rows
alone.

A deploy-time ops script already strips stray grants at build/deploy time,
but an admin can still fat-finger a new DocPerm/Custom DocPerm row onto
either doctype via the Desk UI between deploys. This module is registered
as a daily scheduled job (see `scheduler_events["daily"]` in `crm/hooks.py`)
that reconciles away any such stray grant automatically, so the leak window
is never open longer than a day regardless of deploy cadence.

Deliberately narrow and defensive:
  * Only ever touches the three doctypes named above.
  * Only ever deletes rows granting the two named roles — nothing else — and
    for Oferta only at permlevel >= 1.
  * Never raises into the scheduler: any failure is caught and logged via
    `frappe.log_error` so a bug here can't take down other scheduled jobs.
  * Idempotent — running it against an already-clean site is a no-op.
"""

import frappe

GUARDED_DOCTYPES = ("Volteo Komponent", "Volteo Kalkulator Stale")

# Oferta keeps legitimate permlevel-0 D2D/Backend read; only permlevel >= 1
# rows (which would expose the locked cost/margin fields) are stray.
OFERTA_DOCTYPE = "Volteo Oferta"

BLOCKED_ROLES = ("Volteo D2D Sales", "Volteo Backend")

# Custom doctypes normally store their perm rows in `DocPerm` (parent=doctype),
# but check `Custom DocPerm` too in case a stray override row was added there.
PERM_DOCTYPES = ("DocPerm", "Custom DocPerm")


def reconcile_kalkulator_perms():
	"""Strip any stray D2D/Backend permission from the Kalkulator doctypes.

	Full strip on `Volteo Komponent` / `Volteo Kalkulator Stale` (no D2D/
	Backend access at any level). On `Volteo Oferta`, only permlevel >= 1
	rows are stripped — legitimate permlevel-0 client-facing read is left
	untouched.

	Safe to run repeatedly (idempotent) and safe to fail: all errors are
	caught and logged rather than propagated, so a bug here never breaks
	the daily scheduler run for other jobs.
	"""
	try:
		for dt in GUARDED_DOCTYPES:
			if not frappe.db.exists("DocType", dt):
				continue

			for perm_doctype in PERM_DOCTYPES:
				stray_rows = frappe.get_all(
					perm_doctype,
					filters={
						"parent": dt,
						"role": ["in", BLOCKED_ROLES],
					},
					pluck="name",
				)
				for row_name in stray_rows:
					frappe.delete_doc(
						perm_doctype,
						row_name,
						force=1,
						ignore_permissions=True,
					)

			frappe.clear_cache(doctype=dt)

		if frappe.db.exists("DocType", OFERTA_DOCTYPE):
			for perm_doctype in PERM_DOCTYPES:
				stray_rows = frappe.get_all(
					perm_doctype,
					filters={
						"parent": OFERTA_DOCTYPE,
						"role": ["in", BLOCKED_ROLES],
						"permlevel": [">=", 1],
					},
					pluck="name",
				)
				for row_name in stray_rows:
					frappe.delete_doc(
						perm_doctype,
						row_name,
						force=1,
						ignore_permissions=True,
					)

			frappe.clear_cache(doctype=OFERTA_DOCTYPE)

		frappe.db.commit()
	except Exception:
		frappe.log_error(title="kalkulator_guard reconcile failed")
