# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Blanket enforcement: every File document must be private. No doctype
exemptions, no user exemptions -- owner decision.

Placement is driven by reading the real controller
(frappe/core/doctype/file/file.py, v15.117.0). Two facts about it matter:

1. Frappe's hook ordering: for a given doc event, the controller's own
   method always runs to completion before any app-hooked function for that
   same event fires. File.before_insert() calls save_file() (which writes
   the physical bytes using whatever `is_private` the caller passed) INSIDE
   itself, so an app-hooked "before_insert" function is invoked only after
   that write has already happened. It cannot stop a file arriving with
   is_private=0 from being written into the public `files/` directory
   first. All enforce_private_on_insert can do is normalize the in-memory
   flag early and cheaply; it is not, by itself, sufficient.

2. File.validate() only self-corrects is_private via
   handle_is_private_changed(), and only when
   `not self.is_new() and self.has_value_changed("is_private")`. On insert
   self.is_new() is True, so the controller never calls it -- nothing there
   fixes the public write from (1). On update, has_value_changed() compares
   against the value already committed to the database.

Consequently the actual enforcement point is `before_validate`, not
`before_insert` or `validate`:

- Insert: before_validate runs after naming but before File.validate() and
  before the row is written to the database. Forcing is_private=1 and
  relocating the file here means the DB row is correct from the moment it
  exists -- no follow-up fixup or after_insert patch is needed. As a
  backstop, File.validate_file_path() (part of the controller's own
  validate(), which runs right after us) throws loudly if file_url and
  is_private ever end up disagreeing about the storage directory, so a bug
  here fails the whole save instead of silently persisting an inconsistent
  row.
- Update (e.g. a raw `frappe.client.set_value("File", ..., "is_private", 0)`
  flip -- that call goes through doc.save(), which runs before_validate then
  validate): resetting is_private back to 1 in before_validate means that by
  the time the controller's own validate() runs its
  `has_value_changed("is_private")` check, it sees no change from what is
  already on disk, so it never invokes its own handle_is_private_changed().
  Hooking plain "validate" instead would run after the controller's own
  validate() for the same event, letting it flip the file public first and
  then flipping it back -- a pointless private->public->private move with a
  real (if narrow) window where the file sits in the public directory. Using
  before_validate avoids that window entirely rather than merely closing it
  after the fact.

Physical relocation, when one is actually needed, is delegated to
File.handle_is_private_changed() rather than reimplemented here: that
method also calls update_existing_file_docs(), which rewrites every other
File row sharing the same content_hash (Frappe allows several File rows to
point at one physical file on disk), so a shared file doesn't end up with
sibling rows referencing a path that no longer exists.
"""

import frappe


def enforce_private_on_insert(doc, method=None):
	"""before_insert: early, cheap normalization only.

	Cannot prevent the initial write from landing in the public directory
	when a file arrives with is_private=0 -- see module docstring point 1.
	The correction that actually matters happens in
	enforce_private_on_validate. This just avoids anything between
	before_insert and before_validate observing a stale falsy flag.
	"""
	doc.is_private = 1


def enforce_private_on_validate(doc, method=None):
	"""before_validate: the actual enforcement point, for every insert and
	every save.

	Guarantees, for every File row: is_private == 1; file_url under
	/private/files/ for locally stored files; the physical file lives in
	private/files/ on disk.
	"""
	doc.is_private = 1

	if doc.is_folder:
		# Folders have no physical content and no file_url of their own;
		# forcing the flag above is all "private" means for them.
		return

	if doc.is_remote_file:
		# http(s) attach-by-link (or attach-by-print with no content yet):
		# nothing physical to move, the row-level flag is enough.
		return

	if not doc.file_url or doc.file_url.startswith("/private/files/"):
		# Either nothing to reconcile yet, or already private.
		return

	if not doc.file_url.startswith("/files/"):
		# Not a shape we recognise (should not happen for a locally stored,
		# non-remote file) -- leave it to File.validate_file_url(), which
		# runs right after us as part of the controller's own validate(),
		# to reject it explicitly rather than guessing at a move here.
		return

	try:
		# is_private is already 1 (set above) and file_url still points at
		# the public path, so this moves public -> private, updates
		# file_url, and propagates to any sibling File rows sharing the
		# same physical content.
		doc.handle_is_private_changed()
	except Exception:
		frappe.log_error(
			title="File privacy enforcement failed",
			message=(
				f"Could not relocate File {doc.name!r} ({doc.file_url!r}) to private storage."
			),
		)
		# Never leave is_private=1 persisted next to a public file_url or a
		# physical file still sitting in the public directory -- surface
		# the failure instead of silently saving an inconsistent row.
		raise
