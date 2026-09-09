# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from crm.tests import CRMTestCase as FrappeTestCase


class TestCRMLead(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		"""Set up test records once for all tests"""
		if not frappe.db.exists("Salutation", "Mr"):
			frappe.get_doc({"doctype": "Salutation", "salutation": "Mr"}).insert(ignore_permissions=True)
			frappe.db.commit()  # nosemgrep

		super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test records after all tests"""
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()

	def test_lead_creation_with_first_name(self):
		"""Test creating a lead with first name"""
		lead = create_lead(
			first_name="John",
			last_name="Doe",
			email="john.doe@example.com",
			mobile_no="+1234567890",
		)

		self.assertTrue(lead.name)
		self.assertEqual(lead.first_name, "John")
		self.assertEqual(lead.last_name, "Doe")
		self.assertEqual(lead.email, "john.doe@example.com")
		self.assertEqual(lead.lead_name, "John Doe")

	def test_lead_name_with_salutation(self):
		"""Test lead name generation with salutation"""
		lead = create_lead(
			salutation="Mr",
			first_name="James",
			middle_name="Robert",
			last_name="Smith",
			email="james.smith@example.com",
		)

		self.assertEqual(lead.lead_name, "Mr James Robert Smith")
		self.assertEqual(lead.first_name, "James")
		self.assertEqual(lead.middle_name, "Robert")
		self.assertEqual(lead.last_name, "Smith")

	def test_invalid_email_validation(self):
		"""Test that invalid email raises validation error"""
		with self.assertRaises(frappe.exceptions.ValidationError):
			create_lead(
				first_name="Invalid",
				email="not-an-email",
			)

	def test_set_lead_name_scenarios(self):
		"""Test various scenarios for setting lead_name"""
		# Test 1: lead_name from organization when no first_name
		lead1 = frappe.get_doc({"doctype": "CRM Lead", "organization": "Tech Corp"})
		lead1.flags.ignore_mandatory = True
		lead1.insert()
		self.assertEqual(lead1.lead_name, "Tech Corp")
		self.assertEqual(lead1.title, "Tech Corp")

		# Test 2: lead_name from email prefix when no first_name or organization
		lead2 = frappe.get_doc({"doctype": "CRM Lead", "email": "contact@company.com"})
		lead2.flags.ignore_mandatory = True
		lead2.insert()
		self.assertEqual(lead2.lead_name, "contact")
		self.assertEqual(lead2.title, "contact")

		# Test 3: Throws error without first_name, organization, or email
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			create_lead()
		self.assertIn(
			"A Lead requires either a person's name or an organization's name", str(context.exception)
		)

		# Test 4: lead_name set to 'Unnamed Lead' with ignore_mandatory flag
		lead3 = frappe.get_doc({"doctype": "CRM Lead"})
		lead3.flags.ignore_mandatory = True
		lead3.insert()
		self.assertEqual(lead3.lead_name, "Unnamed Lead")
		self.assertEqual(lead3.title, "Unnamed Lead")

	def test_lead_title_generation(self):
		"""Test that title is set correctly"""
		lead = create_lead(
			first_name="Alice",
			organization="Acme Corp",
			email="alice@acme.com",
		)

		# Title should be organization if provided, otherwise lead_name
		self.assertEqual(lead.title, "Acme Corp")

		lead2 = create_lead(
			first_name="Bob",
			email="bob@example.com",
		)

		self.assertEqual(lead2.title, "Bob")

	def test_lead_owner_cannot_be_same_as_email(self):
		"""Test that lead owner cannot be same as lead email address"""

		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			create_lead(
				first_name="Test",
				email="crm.user1@example.com",
				lead_owner="crm.user1@example.com",
			)
		self.assertIn("Lead Owner cannot be same as the Lead Email Address", str(context.exception))

	def test_update_lead_owner(self):
		"""Test that updating lead owner assigns and shares with the new owner"""
		# Create a lead without owner
		lead = create_lead(
			first_name="Owner",
			last_name="Test",
			email="ownertest@example.com",
		)

		self.assertFalse(lead.lead_owner)

		# Update lead owner
		lead.lead_owner = "Administrator"
		lead.save()

		# Verify owner was updated
		lead.reload()
		self.assertEqual(lead.lead_owner, "Administrator")

		# Verify agent was assigned
		assignees = lead.get_assigned_users()
		self.assertIn("Administrator", assignees)
		initial_assignees_count = len(assignees)

		# Verify document was shared with agent
		docshare = frappe.db.exists(
			"DocShare",
			{"user": "Administrator", "share_name": lead.name, "share_doctype": "CRM Lead"},
		)
		self.assertTrue(docshare)

		# Try to assign the same agent again - should not duplicate
		lead.assign_agent("Administrator")
		assignees_after = lead.get_assigned_users()
		self.assertEqual(len(assignees_after), initial_assignees_count)
		self.assertIn("Administrator", assignees_after)

		# Share with same agent again - should not duplicate docshare
		initial_docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": lead.name, "share_doctype": "CRM Lead"},
		)
		initial_docshare_count = len(initial_docshares)
		lead.share_with_agent("Administrator")
		after_docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": lead.name, "share_doctype": "CRM Lead"},
		)
		self.assertEqual(len(after_docshares), initial_docshare_count)

		lead.lead_owner = "crm.user1@example.com"
		lead.save()
		lead.reload()

		# Verify new owner is assigned and shared
		self.assertEqual(lead.lead_owner, "crm.user1@example.com")
		new_docshare = frappe.db.exists(
			"DocShare",
			{"user": "crm.user1@example.com", "share_name": lead.name, "share_doctype": "CRM Lead"},
		)
		self.assertTrue(new_docshare)

		# Verify old owner's share was removed
		old_docshare = frappe.db.exists(
			"DocShare",
			{"user": "Administrator", "share_name": lead.name, "share_doctype": "CRM Lead"},
		)
		self.assertFalse(old_docshare)

	def test_lead_creation_with_owner(self):
		"""Test creating a lead with lead owner assigns agent on insert"""
		lead = create_lead(
			first_name="Owned",
			last_name="Lead",
			email="ownedlead@example.com",
			lead_owner="Administrator",
		)

		# Verify lead was created with owner
		self.assertEqual(lead.lead_owner, "Administrator")

		# Verify agent was assigned during after_insert
		assignees = lead.get_assigned_users()
		self.assertIn("Administrator", assignees)


def create_lead(**kwargs):
	"""Helper function to create a CRM Lead for testing"""
	data = {"doctype": "CRM Lead"}
	data.update(kwargs)
	return frappe.get_doc(data).insert()
