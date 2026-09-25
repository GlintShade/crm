"""Galeria "Zdjęcia z realizacji" w zakładce Montaż szansy (ops#191).

Jedna galeria per szansa (nie per wpis strumienia Montaż), widoczna dla
każdego z prawem odczytu szansy, edytowalna (dodawanie, usuwanie) przez
każdego z prawem zapisu szansy - dokładnie te same uprawnienia, jakich szansa
już wymaga gdzie indziej, decyzja właściciela 2026-09-25.

Decyzja modelu danych: "File + znacznik, zero schematu". Zdjęcia to zwykłe
wiersze `File` podpięte pod `CRM Deal` (`attached_to_doctype`/
`attached_to_name`), rozróżnione od zwykłych załączników szansy jednym
znacznikiem, `attached_to_field = ZNACZNIK_ZDJEC_MONTAZU`. Bez nowego
doctype'u, bez skryptu ops, bez DocPerm - rdzeń Frappe 15
(`File.validate_attachment_references`, `file.py:176`) sprawdza
`attached_to_field` tylko pod kątem znaków specjalnych, nie wobec meta
doctype'u, więc dowolna wartość tego pola jest dozwolona.

PUŁAPKA `handle_is_private_changed`: gdy istniejący wiersz `File` ze
znacznikiem w `attached_to_field` zmienia `is_private` z 0 na 1, rdzeń Frappe
próbuje wykonać `frappe.db.set_value("CRM Deal", name, "zdjecia_montaz",
url)` - czyli zapisać URL w kolumnie o nazwie znacznika, która na `CRM Deal`
nie istnieje. Nasz upload zawsze wysyła `is_private=1` od razu (patrz
`FilesUploader`/`filesUploaderHandler.ts`), więc ta ścieżka przy normalnym
uploadzie się nie odpala. Ręczny upload publicznego pliku z tym samym
znacznikiem (poza tym modułem) skończyłby się zamkniętym błędem kolumny przy
pierwszej próbie uczynienia go prywatnym - to akceptowalne, bo taka ścieżka
nie istnieje nigdzie w tym forku.

PUŁAPKA dedupu `File` po `content_hash`: rdzeń Frappe deduplikuje pliki o
identycznej zawartości globalnie - dwa uploady tego samego zdjęcia (nawet do
dwóch różnych szans) mogą dać dwa wiersze `File` wskazujące na ten sam
`file_url`. Dlatego usuwanie identyfikuje wiersz po `name` (unikalny klucz
`File`), nigdy po `file_url`.

Frontend woła te endpointy WYŁĄCZNIE pełną kropkowaną ścieżką
(`crm.api.montaz.*`) - gołe nazwy metod dają HTTP 417, pułapka udokumentowana
przy innych whitelisted API forka (`Volteo Umowa`/`Volteo Kredyt`).

`frappe.db.get_all` (nie `frappe.get_all`) w `zdjecia_montazu`: uprawnienia
`File` są owner-based, więc zwykłe `get_all` ukryłoby handlowcowi zdjęcia
wgrane przez kolegów na tej samej szansie - ten sam powód, dla którego
`crm.api.activities.get_attachments` robi to samo. Read na samej szansie jest
sprawdzany jawnie, `frappe.db.get_all` pomija natomiast uprawnienia `File`.

Nie używać `crm.api.delete_attachment` (usuwa po `file_url`, pierwszy
pasujący wiersz - przy dedupie po `content_hash` mógłby trafić w cudzy plik).
"""

import frappe
from frappe import _

ZNACZNIK_ZDJEC_MONTAZU = "zdjecia_montaz"

_ROZSZERZENIA_OBRAZOW = frozenset({"jpg", "jpeg", "png", "webp", "gif"})

_POLA = ["name", "file_name", "file_url", "file_size", "creation", "owner"]


def czy_obraz(file_name: str | None) -> bool:
	"""Czy nazwa pliku ma jedno z rozszerzeń obrazów dopuszczonych w galerii."""
	if not file_name or "." not in file_name:
		return False
	rozszerzenie = file_name.rsplit(".", 1)[-1].lower()
	return rozszerzenie in _ROZSZERZENIA_OBRAZOW


@frappe.whitelist()
def zdjecia_montazu(deal: str) -> dict:
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	wiersze = (
		frappe.db.get_all(
			"File",
			filters={
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": deal,
				"attached_to_field": ZNACZNIK_ZDJEC_MONTAZU,
			},
			fields=_POLA,
			order_by="creation asc",
			limit_page_length=0,
		)
		or []
	)

	return {
		"zdjecia": [wiersz for wiersz in wiersze if czy_obraz(wiersz.file_name)],
		"can_edit": bool(frappe.has_permission("CRM Deal", "write", deal)),
	}


@frappe.whitelist(methods=["POST"])
def usun_zdjecie_montazu(deal: str, name: str) -> None:
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	plik = frappe.db.get_value(
		"File",
		name,
		["attached_to_doctype", "attached_to_name", "attached_to_field"],
		as_dict=True,
	)
	if (
		not plik
		or plik.attached_to_doctype != "CRM Deal"
		or plik.attached_to_name != deal
		or plik.attached_to_field != ZNACZNIK_ZDJEC_MONTAZU
	):
		frappe.throw(_("Zdjęcie nie istnieje."), frappe.DoesNotExistError)

	frappe.delete_doc("File", name, ignore_permissions=True)
