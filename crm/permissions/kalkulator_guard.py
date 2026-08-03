# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Standing daily guard for the Kalkulator pricing-secrecy doctypes.

`Volteo Komponent` (component costs), `Volteo Kalkulator Stale` (margin
constants), `Volteo CP Pozycja` (priced catalogue costs), and `Volteo CP Stale`
(calculator constants) must NEVER carry a `Volteo D2D Sales` or `Volteo Backend`
permission — those roles must stay limited to System Manager + Volteo Core
Admin only (see the Kalkulator commission-secrecy plan, Part 1b / Part 5 #2).

`Volteo Oferta` is different: D2D and Backend legitimately hold permlevel-0
read (the client-facing quote fields) and that must stay untouched. But its
`base_gross_pln`, `commission_pln`, and `breakdown_json` fields are locked at
permlevel=1 to keep the internal cost/margin breakdown admin-only. `Volteo CP
Oferta` follows the same model: `wklad_wlasny` and `prowizja_handlowa` are
legitimate permlevel-0 read fields, while `breakdown_json`, `koszt_calkowity`,
and `marza` are locked at permlevel=1. So for both Oferta doctypes this guard
only strips a stray D2D/Backend perm row at permlevel >= 1 — the level that
would expose those locked fields — leaving permlevel-0 rows alone.

A deploy-time ops script already strips stray grants at build/deploy time,
but an admin can still fat-finger a new DocPerm/Custom DocPerm row onto
any of these doctypes via the Desk UI between deploys. This module is registered
as a daily scheduled job (see `scheduler_events["daily"]` in `crm/hooks.py`)
that reconciles away any such stray grant automatically, so the leak window
is never open longer than a day regardless of deploy cadence.

Deliberately narrow and defensive:
  * Only ever touches the six doctypes named above.
  * Only ever deletes rows granting the two named roles — nothing else — and
    for the Oferta doctypes only at permlevel >= 1.
  * Never raises into the scheduler: any failure is caught and logged via
    `frappe.log_error` so a bug here can't take down other scheduled jobs.
  * Idempotent — running it against an already-clean site is a no-op.
"""

import frappe

GUARDED_DOCTYPES = (
	"Volteo Komponent",
	"Volteo Kalkulator Stale",
	"Volteo CP Pozycja",
	"Volteo CP Stale",
)

# Oferta keeps legitimate permlevel-0 D2D/Backend read; only permlevel >= 1
# rows (which would expose the locked cost/margin fields) are stray.
OFERTA_DOCTYPES = ("Volteo Oferta", "Volteo CP Oferta")

# Volteo CP Limity is the government's published subsidy-cap matrix, not company
# secrets; do not guard it, because backoffice must edit it when the programme changes.

BLOCKED_ROLES = ("Volteo D2D Sales", "Volteo Backend")

# Custom doctypes normally store their perm rows in `DocPerm` (parent=doctype),
# but check `Custom DocPerm` too in case a stray override row was added there.
PERM_DOCTYPES = ("DocPerm", "Custom DocPerm")


def reconcile_kalkulator_perms():
	"""Strip any stray D2D/Backend permission from the Kalkulator doctypes.

	Full strip on the four guarded doctypes (no D2D/Backend access at any
	level). On the two Oferta doctypes, only permlevel >= 1 rows are stripped —
	legitimate permlevel-0 client-facing read is left untouched.

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

		for dt in OFERTA_DOCTYPES:
			if not frappe.db.exists("DocType", dt):
				continue

			for perm_doctype in PERM_DOCTYPES:
				stray_rows = frappe.get_all(
					perm_doctype,
					filters={
						"parent": dt,
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

			frappe.clear_cache(doctype=dt)

		frappe.db.commit()
	except Exception:
		frappe.log_error(title="kalkulator_guard reconcile failed")
