import frappe

from crm.api.contact import delete_shadow_contact
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = (
	"shadow@hier.test",
	"website@hier.test",
	"referenced@hier.test",
)
TEST_CONTACT_FIRST_NAMES = (
	"Real Shadow Test Client",
	"Website Shadow Test Client",
	"Referenced Shadow Test Client",
)


class TestContactUserShadow(FrappeTestCase):
	def tearDown(self):
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist cleanup of committed fixtures

	def test_system_user_contact_is_removed(self):
		from frappe.core.doctype.user.user import create_contact

		user_doc = make_user("shadow@hier.test", user_type="System User")
		create_contact(user=user_doc, ignore_mandatory=True)

		self.assertEqual(frappe.db.count("Contact", {"user": "shadow@hier.test"}), 0)

	def test_contact_without_user_is_untouched(self):
		contact = make_contact("Real Shadow Test Client")

		self.assertTrue(frappe.db.exists("Contact", contact.name))

	def test_website_user_contact_is_untouched(self):
		user = make_user("website@hier.test", user_type="Website User")
		contact = make_contact("Website Shadow Test Client", user=user.name)

		self.assertTrue(frappe.db.exists("Contact", contact.name))

	def test_referenced_user_contact_is_untouched(self):
		user = make_user("referenced@hier.test", user_type="System User")
		# Create the Contact before linking it to the User so the after_insert hook
		# cannot remove it before the reference is constructed.
		contact = make_contact("Referenced Shadow Test Client")

		deal = frappe.get_doc({"doctype": "CRM Deal"})
		deal.flags.ignore_mandatory = True
		deal.flags.ignore_links = True
		deal.append("contacts", {"contact": contact.name})
		deal.insert(ignore_permissions=True)

		frappe.db.set_value("Contact", contact.name, "user", user.name)
		# Call the deferred worker directly: it is the one that re-checks references,
		# so this exercises the reference guard without depending on the queue.
		delete_shadow_contact(contact.name)

		self.assertTrue(frappe.db.exists("Contact", contact.name))

	def test_delete_shadow_contact_missing_contact_is_noop(self):
		# A realistic race for a queued job: by the time it runs, the Contact
		# named in the job may already be gone. Must not raise.
		delete_shadow_contact("nonexistent-contact-hier-test")


def delete_test_documents():
	"""Remove Contacts, deals, and Users created by these tests."""
	contact_names = set(
		frappe.get_all(
			"Contact",
			filters={"user": ["in", TEST_USERS]},
			pluck="name",
		)
	)
	contact_names.update(
		frappe.get_all(
			"Contact",
			filters={"first_name": ["in", TEST_CONTACT_FIRST_NAMES]},
			pluck="name",
		)
	)

	deal_names = []
	if contact_names:
		deal_names = frappe.get_all(
			"CRM Contacts",
			filters={"contact": ["in", list(contact_names)]},
			pluck="parent",
		)
	for deal_name in deal_names:
		if frappe.db.exists("CRM Deal", deal_name):
			frappe.delete_doc("CRM Deal", deal_name, force=True, ignore_permissions=True)

	for contact_name in contact_names:
		if frappe.db.exists("Contact", contact_name):
			frappe.delete_doc("Contact", contact_name, force=True, ignore_permissions=True)

	for email in TEST_USERS:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)


def make_user(email, user_type="System User", roles=None):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	u = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
			"user_type": user_type,
		}
	).insert(ignore_permissions=True)
	for role in roles or []:
		u.add_roles(role)
	return u


def make_contact(first_name, user=None):
	data = {"doctype": "Contact", "first_name": first_name, "last_name": "Test"}
	if user:
		data["user"] = user
	return frappe.get_doc(data).insert(ignore_permissions=True)
