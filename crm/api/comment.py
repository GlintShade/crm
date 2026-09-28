from collections.abc import Iterable

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.desk.form.utils import add_comment as frappe_add_comment
from frappe.utils import get_fullname

from crm.fcrm.doctype.crm_notification.crm_notification import notify_user


def on_update(self, method):
	# VOLTEO (issue #205): wzmianka nigdy nie moze wywalic zapisu komentarza.
	# `on_update` biegnie w tej samej transakcji co insert/save Comment, wiec
	# nieobsluzony wyjatek tutaj cofa caly zapis -- dokladnie to, co dzialo
	# sie z pierwsza wzmianka w komentarzu audytu (Volteo Audyt / Volteo
	# Audyt CP nie maja pol lead_name/organization, patrz notify_mentions
	# nizej). Zewnetrzny try/except to siatka bezpieczenstwa ponad
	# wewnetrznymi try/except w notify_mentions -- na wypadek bledu, ktorego
	# tamte nie przewidzialy.
	try:
		notify_mentions(self)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "notify_mentions: nieoczekiwany blad")


# VOLTEO (issue #205): doctype'y komentowane przez ten sam generyczny watek
# co CRM Lead/CRM Deal, ale bez pol lead_name/organization. Sa 1:1 z CRM Deal
# (autoname "field:deal"), wiec `reference_doc.name` == nazwa szansy; pole
# `deal` czytamy explicite na wypadek zmiany autoname w przyszlosci.
AUDYT_DOCTYPES = ("Volteo Audyt", "Volteo Audyt CP")


def notify_mentions(doc):
	"""
	Extract mentions from `content`, and notify.
	`content` must have `HTML` content.
	"""
	content = getattr(doc, "content", None)
	if not content:
		return
	mentions = extract_mentions(content)
	if not mentions:
		return

	try:
		reference_doc = frappe.get_doc(doc.reference_doctype, doc.reference_name)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "notify_mentions: brak dokumentu referencyjnego")
		return

	for mention in mentions:
		try:
			_notify_mention(doc, reference_doc, mention)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "notify_mentions: wzmianka nie zostala wyslana")


def _notify_mention(doc, reference_doc, mention):
	owner = frappe.get_cached_value("User", doc.owner, "full_name")
	doctype = doc.reference_doctype

	# Domyslnie (CRM Lead/CRM Deal): dzwonek prowadzi wprost na komentowany
	# dokument, a hash w get_hash() wskazuje na sam komentarz (jego `name`).
	notification_type_doctype = "Comment"
	notification_type_doc = doc.name
	redirect_to_doctype = doc.reference_doctype
	redirect_to_docname = doc.reference_name

	if doctype.startswith("CRM "):
		doctype = doctype[4:].lower()
		name = (
			reference_doc.get("lead_name")
			if doctype == "lead"
			else reference_doc.get("organization") or reference_doc.get("lead_name")
		)
	elif doctype in AUDYT_DOCTYPES:
		# Dzwonek prowadzi na sama szanse (CRM Deal), a hash -- na zakladke
		# Audyt/AudytCP; wzorem galezi Trify (notification_type_doctype
		# rozpoznawany w crm.api.notifications.get_hash), nie na komentarz.
		#
		# `notification_type_doc` MUSI byc nazwa istniejacego dokumentu
		# `notification_type_doctype` -- `CRM Notification.notification_type_doc`
		# to Dynamic Link. Zostawienie tu `doc.name` (nazwa Commentu) rzucalo
		# `LinkValidationError` przy kazdej wzmiance w audycie (brak
		# `Volteo Audyt`/`Volteo Audyt CP` o nazwie rownej nazwie komentarza),
		# polykany przez try/except w notify_mentions -- notyfikacja nigdy nie
		# powstawala, bez sladu w Error Log (sonda odslonila to w rundzie
		# 2026-09-28, A2/B2 FAIL). `doc.reference_name` to nazwa dokumentu
		# audytu (autoname "field:deal", wiec rowna nazwie szansy) -- ten sam
		# dokument, ktory faktycznie istnieje, dokladnie jak Trify daje
		# `reference_docname = docname` swojego wlasnego wpisu.
		#
		# Skutek uboczny: `notify_user()` odrzuca duplikat przez
		# `frappe.db.exists("CRM Notification", values)`, a `values` nie
		# zawiera juz nazwy Commentu (byla unikalna per komentarz) -- teraz
		# dwie ROZNE wzmianki na TYM SAMYM audycie koliduja tylko wtedy, gdy
		# maja identyczny `message` (tresc HTML komentarza) I tego samego
		# `assigned_to`. `message = doc.content`, wiec dwa komentarze musialyby
		# byc bajt w bajt identyczne (ten sam znacznik wzmianki + ten sam
		# otaczajacy tekst), co w praktyce nie zdarza sie przy prawdziwym
		# wpisywaniu tekstu -- akceptowany, brzegowy kompromis tego samego
		# mechanizmu dedupu, ktory dziala tak samo dla Trify/Notatek.
		deal = reference_doc.get("deal") or doc.reference_name
		name = deal
		doctype = "audycie szansy"
		notification_type_doctype = doc.reference_doctype
		notification_type_doc = doc.reference_name
		redirect_to_doctype = "CRM Deal"
		redirect_to_docname = deal
	else:
		name = reference_doc.get("name") or doc.reference_name

	notification_text = f"""
        <div class="mb-2 leading-5 text-ink-gray-5">
            <span class="font-medium text-ink-gray-9">{ owner }</span>
            <span>{ _('mentioned you in {0}').format(doctype) }</span>
            <span class="font-medium text-ink-gray-9">{ name }</span>
        </div>
    """
	notify_user(
		{
			"owner": doc.owner,
			"assigned_to": mention.email,
			"notification_type": "Mention",
			"message": doc.content,
			"notification_text": notification_text,
			"reference_doctype": notification_type_doctype,
			"reference_docname": notification_type_doc,
			"redirect_to_doctype": redirect_to_doctype,
			"redirect_to_docname": redirect_to_docname,
		}
	)


def extract_mentions(html):
	if not html:
		return []
	soup = BeautifulSoup(html, "html.parser")
	mentions = []
	for d in soup.find_all("span", attrs={"data-type": "mention"}):
		mentions.append(frappe._dict(full_name=d.get("data-label"), email=d.get("data-id")))
	return mentions


@frappe.whitelist()
def add_comment(reference_doctype: str, reference_name: str, content: str, attachments: list | None = None):
	"""Add a comment to the given document

	:param reference_doctype: Reference Doctype
	:param reference_name: Reference Document Name
	:param content: Comment Content (HTML)
	:param attachments: List of File names or dicts with keys "fname" and "fcontent"
	:return: Comment Document
	"""
	comment = frappe_add_comment(
		reference_doctype,
		reference_name,
		content,
		comment_email=frappe.session.user,
		comment_by=get_fullname(frappe.session.user),
	)

	if attachments and comment.name:
		add_attachments(comment.name, attachments)

	return comment


def add_attachments(name: str, attachments: Iterable[str | dict]) -> None:
	"""Add attachments to the given Comment

	:param name: Comment name
	:param attachments: File names or dicts with keys "fname" and "fcontent"
	"""
	# loop through attachments
	for a in attachments:
		if isinstance(a, str):
			attach = frappe.db.get_value("File", {"name": a}, ["file_url", "is_private"], as_dict=1)
			file_args = {
				"file_url": attach.file_url,
				# Never inherit the source File's is_private -- no public files, ever.
				# (crm.permissions.file_privacy re-enforces this on save regardless,
				# but this stays hard-coded so intent doesn't depend on the hook.)
				"is_private": 1,
			}
		elif isinstance(a, dict) and "fcontent" in a and "fname" in a:
			# dict returned by frappe.attach_print()
			file_args = {
				"file_name": a["fname"],
				"content": a["fcontent"],
				"is_private": 1,
			}
		else:
			continue

		file_args.update(
			{
				"attached_to_doctype": "Comment",
				"attached_to_name": name,
				"folder": "Home/Attachments",
			}
		)

		_file = frappe.new_doc("File")
		_file.update(file_args)
		_file.save(ignore_permissions=True)
