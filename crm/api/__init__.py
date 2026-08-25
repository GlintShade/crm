import re

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.core.api.file import get_max_file_size
from frappe.translate import get_all_translations
from frappe.utils import cint, cstr, split_emails, validate_email_address

from crm.utils import is_frappe_version

# Light sanity check only — digits, "+", spaces, dashes, parentheses; not a
# strict phone-format validator (international formats vary too widely for
# that). Reject only obvious garbage, e.g. letters or a length outside a
# plausible phone number.
_MOBILE_NO_PATTERN = re.compile(r"^[\d+\-\s()]+$")


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
def get_user_signature():
	user = frappe.session.user
	user_email_signature = (
		frappe.db.get_value(
			"User",
			user,
			"email_signature",
		)
		if user
		else None
	)

	signature = user_email_signature or frappe.db.get_value(
		"Email Account",
		{"default_outgoing": 1, "add_signature": 1},
		"signature",
	)

	if not signature:
		return

	soup = BeautifulSoup(signature, "html.parser")
	html_signature = soup.find("div", {"class": "ql-editor read-mode"})
	_signature = None
	if html_signature:
		_signature = html_signature.renderContents()
	content = ""
	if cstr(_signature) or signature:
		content = f'<br><p class="signature">{signature}</p>'
	return content


VOLTEO_LINIA_POLA = {
	"OZE": "custom_linia_oze",
	"Czyste Powietrze": "custom_linia_cp",
}


def volteo_ma_linie(linia: str) -> bool:
	"""True if the current user may use the given product line ("OZE" / "Czyste Powietrze").

	Users holding any of System Manager / Volteo Core Admin / Volteo Backend
	bypass the per-user flags entirely — the flags only ever restrict D2D
	reps (issue #16, `custom_linia_oze` / `custom_linia_cp` on `User`).
	Plain helper, not whitelisted: callers are the whitelisted endpoints
	that already gate on KALKULATOR_ROLE / similar, so this only narrows
	further.

	`linia` is validated against a closed allowlist (`VOLTEO_LINIA_POLA`) —
	an unrecognised value is a caller bug, not silently mapped to either
	line, and throws rather than guessing.
	"""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if role_uzytkownika & {"System Manager", "Volteo Core Admin", "Volteo Backend"}:
		return True

	fieldname = VOLTEO_LINIA_POLA.get(linia)
	if fieldname is None:
		frappe.throw(_("Nieznana linia produktowa: {0}").format(linia))

	return bool(frappe.db.get_value("User", frappe.session.user, fieldname))


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	allowed_modules = []

	if is_frappe_version("15"):
		allowed_modules = frappe.config.get_modules_from_all_apps_for_user()
	elif is_frappe_version("16", above=True):
		from frappe.utils.modules import get_modules_from_all_apps_for_user

		allowed_modules = get_modules_from_all_apps_for_user()

	allowed_modules = [x["module_name"] for x in allowed_modules]
	if "FCRM" not in allowed_modules:
		return False

	roles = frappe.get_roles()
	if any(role in ["System Manager", "Sales User", "Sales Manager"] for role in roles):
		return True

	return False


@frappe.whitelist(allow_guest=True, methods=["POST"])
def accept_invitation(key: str | None = None):
	if not key:
		frappe.throw(_("Invalid or expired key"))

	result = frappe.db.get_all("CRM Invitation", filters={"key": key}, pluck="name")
	if not result:
		frappe.throw(_("Invalid or expired key"))
	invitation = frappe.get_doc("CRM Invitation", result[0])
	invitation.accept()
	invitation.reload()

	if invitation.status == "Accepted":
		frappe.local.login_manager.login_as(invitation.email)
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/crm"


@frappe.whitelist()
def invite_by_email(
	emails: str,
	role: str,
	volteo_role: str | None = None,
	hierarchy_parent: str | None = None,
	first_name: str | None = None,
	last_name: str | None = None,
	mobile_no: str | None = None,
	linia_oze: int = 1,
	linia_cp: int = 1,
):
	frappe.only_for(["Sales Manager", "System Manager", "Volteo Core Admin"], True)

	user_roles = frappe.get_roles(frappe.session.user)

	if role == "System Manager" and "System Manager" not in user_roles:
		frappe.throw(_("You are not allowed to invite System Managers"), frappe.PermissionError)

	if role == "Sales Manager" and "System Manager" not in user_roles:
		frappe.throw(_("You are not allowed to invite Sales Managers"), frappe.PermissionError)

	if role not in ["System Manager", "Sales Manager", "Sales User"]:
		frappe.throw(_("Cannot invite for this role"), frappe.PermissionError)

	# Volteo-specific role assigned alongside the stock CRM role above. Kept
	# to an explicit allowlist — anything outside it is a hard error, never a
	# silent skip.
	if volteo_role not in (None, "", "Volteo D2D Sales", "Volteo Backend"):
		frappe.throw(_("Cannot invite for this Volteo role"), frappe.PermissionError)

	if volteo_role == "Volteo Backend" and not (
		"System Manager" in user_roles or "Volteo Core Admin" in user_roles
	):
		frappe.throw(_("You are not allowed to invite Backoffice users"), frappe.PermissionError)

	if hierarchy_parent and not frappe.db.exists("CRM Sales Hierarchy", hierarchy_parent):
		frappe.throw(_("Sales Hierarchy node {0} does not exist").format(hierarchy_parent))

	# The invite form is single-person: the inviter (not the invitee) now
	# supplies the invitee's name, since it feeds User.full_name and the NDA
	# gate compares against that identity (see
	# crm.api.oswiadczenie._pelne_imie_i_nazwisko). Both are mandatory —
	# an invite with a placeholder or missing name would make the NDA gate
	# either unpassable or pass with a throwaway identity.
	first_name = (first_name or "").strip()
	last_name = (last_name or "").strip()
	if not first_name or not last_name:
		frappe.throw(_("First and last name are required"))

	# Phone is optional (issue #17); when supplied, only a light sanity
	# check — not a strict format validator, since international formats
	# vary too widely for that. Garbage (letters, implausible length) is
	# rejected outright rather than silently stored.
	mobile_no = (mobile_no or "").strip()
	if mobile_no and not (
		7 <= len(mobile_no) <= 20 and _MOBILE_NO_PATTERN.match(mobile_no)
	):
		frappe.throw(_("Enter a valid phone number"))

	# Product-line selection (issue #17): the inviter sets which of
	# OZE / Czyste Powietrze the invitee may use, mirroring
	# `custom_linia_oze` / `custom_linia_cp` on `User` (issue #16). Client
	# may send these as strings, so coerce deliberately with `cint` before
	# the falsy check.
	linia_oze = cint(linia_oze)
	linia_cp = cint(linia_cp)
	if not linia_oze and not linia_cp:
		frappe.throw(_("Wybierz co najmniej jedną linię produktową"))

	if not emails:
		return
	email_string = validate_email_address(emails, throw=False)
	email_list = split_emails(email_string)
	if not email_list:
		return
	if len(email_list) > 1:
		frappe.throw(_("Invite one person at a time"))
	existing_members = frappe.db.get_all("User", filters={"email": ["in", email_list]}, pluck="email")
	existing_invites = frappe.db.get_all(
		"CRM Invitation",
		filters={
			"email": ["in", email_list],
			"role": ["in", ["System Manager", "Sales Manager", "Sales User"]],
		},
		pluck="email",
	)

	to_invite = list(set(email_list) - set(existing_members) - set(existing_invites))

	for email in to_invite:
		frappe.get_doc(
			doctype="CRM Invitation",
			email=email,
			role=role,
			volteo_role=volteo_role or "",
			hierarchy_parent=hierarchy_parent or "",
			first_name=first_name,
			last_name=last_name,
			mobile_no=mobile_no,
			linia_oze=1 if linia_oze else 0,
			linia_cp=1 if linia_cp else 0,
		).insert(ignore_permissions=True)

	return {
		"existing_members": existing_members,
		"existing_invites": existing_invites,
		"to_invite": to_invite,
	}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_attachment(doctype: str, docname: str, file_url: str):
	if not frappe.has_permission(doctype, doc=docname, ptype="write"):
		frappe.throw(_("You don't have permission to delete this attachment"), frappe.PermissionError)

	file_name = frappe.db.get_value(
		"File",
		{"file_url": file_url, "attached_to_doctype": doctype, "attached_to_name": docname},
		"name",
	)
	if file_name:
		frappe.delete_doc("File", file_name)


@frappe.whitelist()
def get_file_uploader_defaults(doctype: str):
	max_number_of_files = None
	make_attachments_public = False
	if doctype:
		meta = frappe.get_meta(doctype)
		max_number_of_files = meta.get("max_attachments")
		make_attachments_public = meta.get("make_attachments_public")

	return {
		"allowed_file_types": frappe.get_system_settings("allowed_file_extensions"),
		"max_file_size": get_max_file_size(),
		"max_number_of_files": max_number_of_files,
		"make_attachments_public": bool(make_attachments_public),
	}
