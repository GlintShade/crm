import json

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.desk.form.load import get_docinfo
from frappe.query_builder import JoinType
from frappe.translate import get_translated_doctypes

from crm.fcrm.doctype.crm_call_log.crm_call_log import parse_call_log


@frappe.whitelist()
def get_activities(name: str):
	if frappe.db.exists("CRM Deal", name):
		return get_deal_activities(name)
	elif frappe.db.exists("CRM Lead", name):
		return get_lead_activities(name)
	else:
		frappe.throw(_("Document not found"), frappe.DoesNotExistError)


def get_deal_activities(name: str):
	if not frappe.has_permission("CRM Deal", "read", name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	get_docinfo("", "CRM Deal", name)
	docinfo = frappe.response["docinfo"]
	deal_meta = frappe.get_meta("CRM Deal")
	deal_fields = {
		field.fieldname: {"label": field.label, "options": field.options} for field in deal_meta.fields
	}
	avoid_fields = [
		"lead",
		"response_by",
		"sla_creation",
		"sla",
		"first_response_time",
		"first_responded_on",
	]

	doc = frappe.db.get_values("CRM Deal", name, ["creation", "owner", "lead"])[0]
	lead = doc[2]

	activities = []
	calls = []
	notes = []
	tasks = []
	attachments = []
	creation_text = _("created this deal")

	if lead:
		activities, calls, notes, tasks, attachments = get_lead_activities(lead)
		creation_text = _("converted the lead to this deal")

	activities.append(
		{
			"activity_type": "creation",
			"creation": doc[0],
			"owner": doc[1],
			"data": creation_text,
			"is_lead": False,
		}
	)

	docinfo.versions.reverse()

	for version in docinfo.versions:
		data = json.loads(version.data)

		# Frappe records custom_zestaw (BOM) child-table row adds/removes/
		# edits under 'added' / 'removed' / 'row_changed' -- NOT under
		# 'changed' (simple field diffs), which is all the rest of this loop
		# reads. A real BOM edit's Version can carry BOTH 'row_changed' AND
		# 'changed' at once (e.g. editing a zestaw row alongside a plain deal
		# field), so this must run unconditionally for every version, BEFORE
		# the `if not data.get("changed")` gate below -- gating it on that
		# check (as this code previously did) silently dropped exactly that
		# case. See extract_zestaw_version_summary for the diff-shape
		# assumptions.
		zestaw = extract_zestaw_version_summary(data)
		if zestaw:
			activities.append(
				{
					"name": f"volteo-zestaw-{name}-{version.creation}",
					"activity_type": "volteo_linked",
					"creation": version.creation,
					"owner": version.owner,
					"is_lead": False,
					"data": {
						"source": "custom_zestaw",
						"label": _("Zestaw"),
						"title": None,
						"action": "changed",
						"doc_name": name,
						"summary": zestaw["summary"],
						"text": zestaw["text"],
					},
				}
			)

		if not data.get("changed"):
			continue

		if change := data.get("changed")[0]:
			field = deal_fields.get(change[0], None)

			if not field or change[0] in avoid_fields or (not change[1] and not change[2]):
				continue

			field_label = field.get("label") or change[0]
			field_option = field.get("options") or None

			activity_type = "changed"
			data = {
				"field": change[0],
				"field_label": field_label,
				"old_value": change[1],
				"value": change[2],
			}

			if not change[1] and change[2]:
				activity_type = "added"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[2],
				}
			elif change[1] and not change[2]:
				activity_type = "removed"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[1],
				}

			if data.get("value") and field_option and is_translatable(field_option):
				data["value"] = _(data["value"])

				if data.get("old_value"):
					data["old_value"] = _(data["old_value"])

		activity = {
			"activity_type": activity_type,
			"creation": version.creation,
			"owner": version.owner,
			"data": data,
			"is_lead": False,
			"options": field_option,
		}
		activities.append(activity)

	for comment in docinfo.comments:
		activity = {
			"name": comment.name,
			"activity_type": "comment",
			"creation": comment.creation,
			"owner": comment.owner,
			"content": comment.content,
			"attachments": get_attachments("Comment", comment.name),
			"is_lead": False,
		}
		activities.append(activity)

	for communication in docinfo.communications + docinfo.automated_messages:
		activity = {
			"activity_type": "communication",
			"communication_type": communication.communication_type,
			"communication_date": communication.communication_date or communication.creation,
			"creation": communication.creation,
			"data": {
				"subject": communication.subject,
				"content": communication.content,
				"sender_full_name": communication.sender_full_name,
				"sender": communication.sender,
				"recipients": communication.recipients,
				"cc": communication.cc,
				"bcc": communication.bcc,
				"attachments": get_attachments("Communication", communication.name),
				"read_by_recipient": communication.read_by_recipient,
				"delivery_status": communication.delivery_status,
			},
			"is_lead": False,
		}
		activities.append(activity)

	for attachment_log in docinfo.attachment_logs:
		activity = {
			"name": attachment_log.name,
			"activity_type": "attachment_log",
			"creation": attachment_log.creation,
			"owner": attachment_log.owner,
			"data": parse_attachment_log(attachment_log.content, attachment_log.comment_type),
			"is_lead": False,
		}
		activities.append(activity)

	calls = calls + get_linked_calls(name).get("calls", [])
	notes = notes + get_linked_notes(name) + get_linked_calls(name).get("notes", [])
	tasks = tasks + get_linked_tasks(name) + get_linked_calls(name).get("tasks", [])
	attachments = attachments + get_attachments("CRM Deal", name)
	activities = activities + get_volteo_linked_activities(name)

	activities.sort(key=lambda x: x["creation"], reverse=True)
	activities = handle_multiple_versions(activities)

	return activities, calls, notes, tasks, attachments


def get_lead_activities(name: str):
	if not frappe.has_permission("CRM Lead", "read", name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	get_docinfo("", "CRM Lead", name)
	docinfo = frappe.response["docinfo"]
	lead_meta = frappe.get_meta("CRM Lead")
	lead_fields = {
		field.fieldname: {"label": field.label, "options": field.options} for field in lead_meta.fields
	}
	avoid_fields = [
		"converted",
		"response_by",
		"sla_creation",
		"sla",
		"first_response_time",
		"first_responded_on",
	]

	doc = frappe.db.get_values("CRM Lead", name, ["creation", "owner"])[0]
	activities = [
		{
			"activity_type": "creation",
			"creation": doc[0],
			"owner": doc[1],
			"data": _("created this lead"),
			"is_lead": True,
		}
	]

	docinfo.versions.reverse()

	for version in docinfo.versions:
		data = json.loads(version.data)
		if not data.get("changed"):
			continue

		if change := data.get("changed")[0]:
			field = lead_fields.get(change[0], None)

			if not field or change[0] in avoid_fields or (not change[1] and not change[2]):
				continue

			field_label = field.get("label") or change[0]
			field_option = field.get("options") or None

			activity_type = "changed"
			data = {
				"field": change[0],
				"field_label": field_label,
				"old_value": change[1],
				"value": change[2],
			}

			if not change[1] and change[2]:
				activity_type = "added"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[2],
				}
			elif change[1] and not change[2]:
				activity_type = "removed"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[1],
				}

			if data.get("value") and field_option and is_translatable(field_option):
				data["value"] = _(data["value"])

				if data.get("old_value"):
					data["old_value"] = _(data["old_value"])

		activity = {
			"activity_type": activity_type,
			"creation": version.creation,
			"owner": version.owner,
			"data": data,
			"is_lead": True,
			"options": field_option,
		}
		activities.append(activity)

	for comment in docinfo.comments:
		activity = {
			"name": comment.name,
			"activity_type": "comment",
			"creation": comment.creation,
			"owner": comment.owner,
			"content": comment.content,
			"attachments": get_attachments("Comment", comment.name),
			"is_lead": True,
		}
		activities.append(activity)

	for communication in docinfo.communications + docinfo.automated_messages:
		activity = {
			"activity_type": "communication",
			"communication_type": communication.communication_type,
			"communication_date": communication.communication_date or communication.creation,
			"creation": communication.creation,
			"data": {
				"subject": communication.subject,
				"content": communication.content,
				"sender_full_name": communication.sender_full_name,
				"sender": communication.sender,
				"recipients": communication.recipients,
				"cc": communication.cc,
				"bcc": communication.bcc,
				"attachments": get_attachments("Communication", communication.name),
				"read_by_recipient": communication.read_by_recipient,
				"delivery_status": communication.delivery_status,
			},
			"is_lead": True,
		}
		activities.append(activity)

	for attachment_log in docinfo.attachment_logs:
		activity = {
			"name": attachment_log.name,
			"activity_type": "attachment_log",
			"creation": attachment_log.creation,
			"owner": attachment_log.owner,
			"data": parse_attachment_log(attachment_log.content, attachment_log.comment_type),
			"is_lead": True,
		}
		activities.append(activity)

	calls = get_linked_calls(name).get("calls", [])
	notes = get_linked_notes(name) + get_linked_calls(name).get("notes", [])
	tasks = get_linked_tasks(name) + get_linked_calls(name).get("tasks", [])
	attachments = get_attachments("CRM Lead", name)

	activities.sort(key=lambda x: x["creation"], reverse=True)
	activities = handle_multiple_versions(activities)

	return activities, calls, notes, tasks, attachments


# ---------------------------------------------------------------------------
# Linked-record activity aggregation (Volteo fix #4d)
#
# The Deal "Aktywność" timeline only reflects the CRM Deal's own docinfo
# (its comments/communications/version log). This section folds in events
# from the deal's linked Volteo records — Faktura, Montaż updates, Audyt —
# plus custom_zestaw (BOM) child-table edits (handled inline in the version
# loop above via extract_zestaw_version_summary). Every source below is
# independently defensive: a missing doctype/field on a fresh site, or an
# unrecognised Version payload, can never break the rest of get_deal_activities().
# ---------------------------------------------------------------------------

VOLTEO_LINKED_SOURCES = [
	# "text_fields" are the extra fields fetched (defensively -- only if the
	# live meta actually has them) to compose data["text"] (FIX G). Volteo
	# Audyt has no fixed field name here; its candidates are resolved
	# dynamically against meta in get_volteo_linked_activities below.
	{"doctype": "Volteo Faktura", "label": _("Faktura"), "link_field": "deal", "text_fields": ["numer", "status"]},
	{
		"doctype": "Volteo Montaz Update",
		"label": _("Montaż"),
		"link_field": "deal",
		"text_fields": ["typ", "tekst"],
	},
	{"doctype": "Volteo Audyt", "label": _("Audyt"), "link_field": "deal", "text_fields": []},
]

CUSTOM_ZESTAW_FIELDNAME = "custom_zestaw"


def get_volteo_linked_activities(name: str):
	"""Creation + change events for the deal's linked Volteo records.

	Record visibility uses frappe.get_list (permission-respecting) so a user
	only sees linked records they're actually allowed to read — important for
	Volteo Faktura, which carries its own deal-scoped read restriction (the
	cross-rep invoice-leak fix in the immediately preceding commit). The
	per-record Version lookup below uses frappe.get_all instead: the Version
	doctype has no per-role permission model of its own, gating already
	happened at the record-read step above, and this mirrors how the deal's
	own docinfo.versions are fetched elsewhere in this file.
	"""
	linked_activities = []

	for source in VOLTEO_LINKED_SOURCES:
		dt = source["doctype"]
		label = source["label"]
		link_field = source["link_field"]
		track_changes = False
		title_field = None

		try:
			if not frappe.db.exists("DocType", dt):
				continue

			meta = frappe.get_meta(dt)
			title_field = meta.title_field
			track_changes = bool(meta.track_changes)

			# Extra fields needed to compose data["text"] (FIX G), resolved
			# defensively against the live meta -- a configured field that
			# doesn't actually exist on this site's doctype is silently
			# dropped rather than blowing up the frappe.get_list() call below.
			if dt == "Volteo Audyt":
				# No fixed field name is guaranteed here; probe for the most
				# meaningful Select fields this doctype tends to carry.
				text_fieldnames = [fn for fn in ("rodzaj_instalacji", "status") if meta.get_field(fn)]
			else:
				text_fieldnames = [fn for fn in (source.get("text_fields") or []) if meta.get_field(fn)]

			fields = ["name", "owner", "creation", "modified"]
			if title_field and title_field not in fields:
				fields.append(title_field)
			for fieldname in text_fieldnames:
				if fieldname not in fields:
					fields.append(fieldname)

			records = frappe.get_list(
				dt,
				filters={link_field: name},
				fields=fields,
				order_by="creation asc",
				limit_page_length=200,
				ignore_permissions=False,
			)
		except Exception:
			frappe.log_error(
				title="Volteo linked activities: failed to list source",
				message=f"doctype={dt}\n{frappe.get_traceback()}",
			)
			continue

		fields_map = {}
		if track_changes:
			try:
				fields_map = {
					field.fieldname: (field.label or field.fieldname) for field in meta.fields
				}
			except Exception:
				fields_map = {}

		for rec in records:
			title = None
			try:
				if title_field:
					val = rec.get(title_field)
					# A title_field whose value equals the record's own name
					# (e.g. Volteo Audyt: autoname "field:deal", title_field
					# "deal" — the title would just repeat the current deal's
					# id) isn't a useful title; leave it unset instead.
					if val and str(val) != rec.name:
						title = val
			except Exception:
				title = None

			try:
				linked_activities.append(
					{
						"name": f"volteo-{dt}-{rec.name}",
						"activity_type": "volteo_linked",
						"creation": rec.creation,
						"owner": rec.owner,
						"is_lead": False,
						"data": {
							"source": dt,
							"label": label,
							"title": title,
							"action": "added",
							"doc_name": rec.name,
							"text": compose_volteo_linked_text(dt, "added", rec),
						},
					}
				)
			except Exception:
				frappe.log_error(
					title="Volteo linked activities: failed to build creation event",
					message=f"doctype={dt} record={rec.name}\n{frappe.get_traceback()}",
				)
				continue

			if not track_changes:
				continue

			try:
				versions = frappe.get_all(
					"Version",
					filters={"ref_doctype": dt, "docname": rec.name},
					fields=["owner", "creation", "data"],
					order_by="creation asc",
					limit_page_length=50,
				)
			except Exception:
				frappe.log_error(
					title="Volteo linked activities: failed to list versions",
					message=f"doctype={dt} record={rec.name}\n{frappe.get_traceback()}",
				)
				continue

			for version in versions:
				try:
					summary = None
					try:
						vdata = json.loads(version.data)
						summary = summarize_version_changes(vdata, fields_map)
					except Exception:
						summary = None  # unrecognised payload -> still emit a generic event below

					if summary == "":
						continue  # genuine no-op version, skip it

					linked_activities.append(
						{
							"name": f"volteo-{dt}-{rec.name}-{version.creation}",
							"activity_type": "volteo_linked",
							"creation": version.creation,
							"owner": version.owner,
							"is_lead": False,
							"data": {
								"source": dt,
								"label": label,
								"title": title,
								"action": "changed",
								"doc_name": rec.name,
								"summary": summary,
								"text": compose_volteo_linked_text(dt, "changed", rec, summary),
							},
						}
					)
				except Exception:
					frappe.log_error(
						title="Volteo linked activities: failed to build change event",
						message=f"doctype={dt} record={rec.name}\n{frappe.get_traceback()}",
					)
					continue

	return linked_activities


def compose_volteo_linked_text(dt: str, action: str, rec: dict, summary: str | None = None):
	"""Compose the authoritative Polish display string for a volteo_linked
	activity's data["text"] (FIX G) -- rendered as-is (impersonal, gray) after
	the bold actor name in the Deal Activities feed, replacing the old
	frontend label/action/title/summary stitching.

	`rec` is the per-source record dict fetched in get_volteo_linked_activities
	(carries whichever text-field names were resolved against that doctype's
	live meta -- a field simply absent from `rec` reads back as None via
	.get(), never a KeyError). `summary` is the changed-fields summary already
	computed by summarize_version_changes for 'changed' events (None/unused
	for 'added').

	Defensive end-to-end: any lookup issue is swallowed and None returned, so
	the caller falls back to a generic label-based string instead of breaking
	the feed.
	"""
	try:
		if dt == "Volteo Faktura":
			numer = rec.get("numer")
			status = rec.get("status")
			if action == "added":
				text = _("dodano fakturę {0}").format(numer or "—")
				if status:
					text += " (" + status + ")"
				return text
			text = _("zaktualizowano fakturę {0}").format(numer or "—")
			if summary:
				text += " — " + summary
			return text

		if dt == "Volteo Montaz Update":
			typ = rec.get("typ")
			tekst = (rec.get("tekst") or "").strip()
			snippet = tekst[:80] + "…" if len(tekst) > 80 else tekst
			text = _("dodano wpis montażu: {0}").format(typ or "—")
			if snippet:
				text += " — „" + snippet + "”"
			return text

		if dt == "Volteo Audyt":
			if action == "added":
				field_value = rec.get("rodzaj_instalacji") or rec.get("status")
				text = _("dodano audyt")
				if field_value:
					text += ": " + field_value
				return text
			text = _("zaktualizowano audyt")
			if summary:
				text += " — " + summary
			return text
	except Exception:
		return None

	return None


def summarize_version_changes(data: dict, fields_map: dict):
	"""Compact one-line summary of changed field labels from a Version.data
	diff dict (the same 'changed': [[fieldname, old, new], ...] shape parsed
	by the deal/lead version loops above).

	Returns "" for a genuine no-op version (caller should skip it) or a
	summary string. The caller treats its own json-parse failure separately
	(kept as None) so it can still emit a generic 'changed' event per spec.
	"""
	if not isinstance(data, dict):
		return ""

	labels = []
	for change in data.get("changed") or []:
		if not change:
			continue
		fieldname = change[0] if len(change) > 0 else None
		old_value = change[1] if len(change) > 1 else None
		new_value = change[2] if len(change) > 2 else None
		if not fieldname or (not old_value and not new_value):
			continue
		labels.append(fields_map.get(fieldname) or fieldname)

	if not labels:
		return ""

	seen = []
	for field_label in labels:
		if field_label not in seen:
			seen.append(field_label)

	shown = seen[:5]
	summary = ", ".join(shown)
	extra = len(seen) - len(shown)
	if extra > 0:
		summary += " " + _("+{0} more").format(extra)
	return summary


def extract_zestaw_version_summary(data: dict):
	"""Best-effort summary + display text for custom_zestaw (BOM) child-table
	row activity found in a CRM Deal Version diff (FIX H).

	The version loop in get_deal_activities() above only reads data['changed']
	(simple field diffs); Frappe records custom_zestaw row add/remove/edit
	activity under 'added' / 'removed' / 'row_changed' instead, so this scans
	all three for custom_zestaw entries. Confirmed against a live probe:

	  - 'row_changed' entries look like
	    ["custom_zestaw", <row_index>, "<row_name>", [["typ", old, new], ...]]
	    -- counted by entry[0] == CUSTOM_ZESTAW_FIELDNAME.
	  - 'added' / 'removed' shapes weren't directly confirmed by the probe;
	    the entry[0] == CUSTOM_ZESTAW_FIELDNAME check is a reasonable guess
	    mirrored from 'row_changed' and kept defensive -- if it doesn't match
	    a given site's actual shape, those counts are simply 0 rather than an
	    error. Child fields are typ / nazwa / ilosc.

	Returns None if the version carries no recognisable custom_zestaw
	activity (caller should skip it entirely), otherwise a dict:
	  {"summary": "zmieniono 2 poz., dodano 1 poz.", "text": "zmieniono zestaw (BOM): zmieniono 2 poz., dodano 1 poz."}
	'summary' is the Polish, comma-joined "dodano/usunięto/zmieniono N poz."
	string (kept as data["summary"] for backward compatibility). 'text' is
	the authoritative data["text"] display string (FIX G): 'summary' prefixed
	with a single verb -- "dodano zestaw (BOM): " for a pure addition,
	"usunięto zestaw (BOM): " for a pure removal, "zmieniono zestaw (BOM): "
	otherwise (any row_changed activity, or a mix of adds/removes).
	"""
	try:
		if not isinstance(data, dict):
			return None

		def rows_for(entries):
			count = 0
			for entry in entries or []:
				if not entry or entry[0] != CUSTOM_ZESTAW_FIELDNAME:
					continue
				rows = entry[1] if len(entry) > 1 else None
				count += len(rows) if isinstance(rows, list) else 1
			return count

		added = rows_for(data.get("added"))
		removed = rows_for(data.get("removed"))
		changed = sum(
			1 for entry in (data.get("row_changed") or []) if entry and entry[0] == CUSTOM_ZESTAW_FIELDNAME
		)

		parts = []
		if added:
			parts.append(_("dodano {0} poz.").format(added))
		if removed:
			parts.append(_("usunięto {0} poz.").format(removed))
		if changed:
			parts.append(_("zmieniono {0} poz.").format(changed))

		if not parts:
			return None

		summary = ", ".join(parts)

		if added and not removed and not changed:
			verb = _("dodano zestaw (BOM): ")
		elif removed and not added and not changed:
			verb = _("usunięto zestaw (BOM): ")
		else:
			verb = _("zmieniono zestaw (BOM): ")

		return {"summary": summary, "text": verb + summary}
	except Exception:
		return None


def get_attachments(doctype: str, name: str):
	return (
		frappe.db.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": name},
			fields=[
				"name",
				"file_name",
				"file_type",
				"file_url",
				"file_size",
				"is_private",
				"modified",
				"creation",
				"owner",
			],
		)
		or []
	)


def handle_multiple_versions(versions: list):
	activities = []
	grouped_versions = []
	old_version = None
	for version in versions:
		is_version = version["activity_type"] in ["changed", "added", "removed"]
		if not is_version:
			activities.append(version)
		if not old_version:
			old_version = version
			if is_version:
				grouped_versions.append(version)
			continue
		if is_version and old_version.get("owner") and version["owner"] == old_version["owner"]:
			grouped_versions.append(version)
		else:
			if grouped_versions:
				activities.append(parse_grouped_versions(grouped_versions))
			grouped_versions = []
			if is_version:
				grouped_versions.append(version)
		old_version = version
		if version == versions[-1] and grouped_versions:
			activities.append(parse_grouped_versions(grouped_versions))

	return activities


def parse_grouped_versions(versions: list):
	version = versions[0]
	if len(versions) == 1:
		return version
	other_versions = versions[1:]
	version["other_versions"] = other_versions
	return version


def get_linked_calls(name: str):
	calls = frappe.db.get_all(
		"CRM Call Log",
		filters={"reference_docname": name},
		fields=[
			"name",
			"caller",
			"receiver",
			"from",
			"to",
			"duration",
			"start_time",
			"end_time",
			"status",
			"type",
			"recording_url",
			"creation",
			"note",
		],
	)

	linked_calls = frappe.db.get_all(
		"Dynamic Link", filters={"link_name": name, "parenttype": "CRM Call Log"}, pluck="parent"
	)

	notes = []
	tasks = []

	if linked_calls:
		CallLog = frappe.qb.DocType("CRM Call Log")
		Link = frappe.qb.DocType("Dynamic Link")
		query = (
			frappe.qb.from_(CallLog)
			.select(
				CallLog.name,
				CallLog.caller,
				CallLog.receiver,
				CallLog["from"],
				CallLog.to,
				CallLog.duration,
				CallLog.start_time,
				CallLog.end_time,
				CallLog.status,
				CallLog.type,
				CallLog.recording_url,
				CallLog.creation,
				CallLog.note,
				Link.link_doctype,
				Link.link_name,
			)
			.join(Link, JoinType.inner)
			.on(Link.parent == CallLog.name)
			.where(CallLog.name.isin(linked_calls))
		)
		_calls = query.run(as_dict=True)

		for call in _calls:
			if call.get("link_doctype") == "FCRM Note":
				notes.append(call.link_name)
			elif call.get("link_doctype") == "CRM Task":
				tasks.append(call.link_name)

		_calls = [call for call in _calls if call.get("link_doctype") not in ["FCRM Note", "CRM Task"]]
		if _calls:
			calls = calls + _calls

	if notes:
		notes = frappe.db.get_all(
			"FCRM Note",
			filters={"name": ("in", notes)},
			fields=["name", "title", "content", "owner", "modified"],
		)

	if tasks:
		tasks = frappe.db.get_all(
			"CRM Task",
			filters={"name": ("in", tasks)},
			fields=[
				"name",
				"title",
				"description",
				"assigned_to",
				"due_date",
				"priority",
				"status",
				"modified",
			],
		)

	calls = [parse_call_log(call) for call in calls] if calls else []

	return {"calls": calls, "notes": notes, "tasks": tasks}


def get_linked_notes(name: str):
	notes = frappe.db.get_all(
		"FCRM Note",
		filters={"reference_docname": name},
		fields=["name", "title", "content", "owner", "modified", "creation"],
	)
	return notes or []


def get_linked_tasks(name: str):
	tasks = frappe.db.get_all(
		"CRM Task",
		filters={"reference_docname": name},
		fields=[
			"name",
			"title",
			"description",
			"assigned_to",
			"due_date",
			"priority",
			"status",
			"modified",
			"creation",
		],
	)
	return tasks or []


def parse_attachment_log(html: str, type: str):
	soup = BeautifulSoup(html, "html.parser")
	a_tag = soup.find("a")
	type = "added" if type == "Attachment" else "removed"
	if not a_tag:
		return {
			"type": type,
			"file_name": html.replace("Removed ", ""),
			"file_url": "",
			"is_private": False,
		}

	is_private = False
	if "private/files" in a_tag["href"]:
		is_private = True

	return {
		"type": type,
		"file_name": a_tag.text,
		"file_url": a_tag["href"],
		"is_private": is_private,
	}


def is_translatable(doctype: str) -> bool:
	return doctype in get_translated_doctypes()
