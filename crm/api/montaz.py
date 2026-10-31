"""Galeria "Zdjęcia z realizacji" w zakładce Montaż szansy (ops#191).

Jedna galeria per szansa (nie per wpis strumienia Montaż), widoczna dla
każdego z prawem odczytu szansy, edytowalna (dodawanie, usuwanie) przez
każdego z prawem zapisu szansy - dokładnie te same uprawnienia, jakich szansa
już wymaga gdzie indziej, decyzja właściciela 2026-09-25. Od b66 galeria
przyjmuje też filmy, nie tylko zdjęcia (te same rozszerzenia wideo co sloty
Audytu z `allowVideo`, b63 ops#190) - klasyfikacja idzie przez
`crm.volteo_pliki.czy_media_montazu` (frappe-free, obraz albo wideo).

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

Sekcja "Protokol montazu" (ops#307): ten sam wzorzec "File + znacznik, zero
schematu", znacznik `ZNACZNIK_PROTOKOLU_MONTAZU`, te same uprawnienia (odczyt
szansy -> widok, zapis szansy -> dodawanie i usuwanie). Dopuszczone tylko PDF,
JPG i PNG (`crm.volteo_pliki.czy_plik_protokolu`). Wszystkie pulapki powyzej
dotycza ja tak samo.

Runda 2 (ops#307): protokol widza wszyscy z prawem odczytu szansy, ale
dodawac i usuwac moga tylko Administrator, System Manager, Volteo Core Admin i
Volteo Backend (`czy_admin_lub_bypass`, jedyna bramka). Egzekwuja to trzy
miejsca: `usun_protokol_montazu`, hook `File.before_insert`
(`strzez_protokolu_przed_wgraniem`, zamyka bezposredni `upload_file`) i hook
`has_permission` na `File` (`uprawnienie_pliku_protokolu`, zamyka REST DELETE;
musi byc tu, bo `frappe.delete_doc` sprawdza uprawnienie przed `on_trash`).
Obie sekcje Montazu zamiast ogolnego komentarza "Attachment" zostawiaja wlasny
slad Volteo w Aktywnosci (`slad_po_wgraniu`, `slad_po_usunieciu`).
Oba hooki pomijaja slad, gdy szansa juz nie istnieje: rdzen w `delete_doc`
robi `delete_from_table` przed `remove_all`, wiec przy usuwaniu szansy File
kasuja sie juz po zniknieciu wiersza szansy.
"""

import frappe
from frappe import _

from crm.permissions.org_hierarchy import czy_admin_lub_bypass
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_pliki import ETYKIETY_SLADU_MONTAZU, czy_media_montazu, czy_plik_protokolu

ZNACZNIK_ZDJEC_MONTAZU = "zdjecia_montaz"
ZNACZNIK_PROTOKOLU_MONTAZU = "protokol_montaz"

KOMUNIKAT_PROTOKOLU = "Protokół montażu może zmieniać tylko administracja i backoffice."

_POLA = ["name", "file_name", "file_url", "file_size", "creation", "owner"]


def _pliki_ze_znacznikiem(deal: str, znacznik: str, filtr) -> list:
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	wiersze = (
		frappe.db.get_all(
			"File",
			filters={
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": deal,
				"attached_to_field": znacznik,
			},
			fields=_POLA,
			order_by="creation asc",
			limit_page_length=0,
		)
		or []
	)
	return [wiersz for wiersz in wiersze if filtr(wiersz.file_name)]


def _usun_ze_znacznikiem(deal: str, znacznik: str, name: str) -> None:
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
		or plik.attached_to_field != znacznik
	):
		frappe.throw(_("Plik nie istnieje."), frappe.DoesNotExistError)

	frappe.delete_doc("File", name, ignore_permissions=True)


@frappe.whitelist()
def zdjecia_montazu(deal: str) -> dict:
	return {
		"zdjecia": _pliki_ze_znacznikiem(deal, ZNACZNIK_ZDJEC_MONTAZU, czy_media_montazu),
		"can_edit": bool(frappe.has_permission("CRM Deal", "write", deal)),
	}


@frappe.whitelist(methods=["POST"])
def usun_zdjecie_montazu(deal: str, name: str) -> None:
	_usun_ze_znacznikiem(deal, ZNACZNIK_ZDJEC_MONTAZU, name)


@frappe.whitelist()
def protokol_montazu(deal: str) -> dict:
	return {
		"pliki": _pliki_ze_znacznikiem(deal, ZNACZNIK_PROTOKOLU_MONTAZU, czy_plik_protokolu),
		"can_edit": bool(czy_admin_lub_bypass()),
	}


@frappe.whitelist(methods=["POST"])
def usun_protokol_montazu(deal: str, name: str) -> None:
	if not czy_admin_lub_bypass():
		frappe.throw(_(KOMUNIKAT_PROTOKOLU), frappe.PermissionError)
	_usun_ze_znacznikiem(deal, ZNACZNIK_PROTOKOLU_MONTAZU, name)


def _to_plik_protokolu(doc) -> bool:
	return (
		doc.attached_to_doctype == "CRM Deal" and doc.attached_to_field == ZNACZNIK_PROTOKOLU_MONTAZU
	)


def strzez_protokolu_przed_wgraniem(doc, method=None):
	"""`File.before_insert`: wgranie pliku protokolu tylko dla administracji i backoffice."""
	if _to_plik_protokolu(doc) and not czy_admin_lub_bypass():
		frappe.throw(_(KOMUNIKAT_PROTOKOLU), frappe.PermissionError)


def uprawnienie_pliku_protokolu(doc, ptype=None, user=None):
	"""`has_permission` na `File`: False tylko dla delete pliku protokolu przez kogos spoza
	administracji i backoffice; w kazdym innym przypadku None (decyduje Frappe)."""
	if ptype == "delete" and _to_plik_protokolu(doc) and not czy_admin_lub_bypass(user):
		return False
	return None


def _usun_ogolny_komentarz(doc, typ: str, pasuje) -> None:
	"""Kasuje ogolny komentarz rdzenia, ktory kontroler `File` dopiero co zapisal.

	Zwykle `frappe.db.delete` jest tu bezpieczne: `update_comment_in_doc` w rdzeniu
	(`comment.py`) ignoruje kazdy `comment_type` inny niz "Comment", wiec zadna pamiec
	podreczna `_comments` na szansie nie jest zaangazowana (`remove_comment_from_cache`
	tez dotyczy tylko "Comment"). Kasujemy tylko wiersz pasujacy do TEGO pliku."""
	wiersze = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "CRM Deal",
			"reference_name": doc.attached_to_name,
			"comment_type": typ,
		},
		fields=["name", "content"],
		order_by="creation desc",
		limit=1,
	)
	if wiersze and pasuje(wiersze[0].content or ""):
		frappe.db.delete("Comment", {"name": wiersze[0].name})


def _slad_montazu(doc, akcja: str) -> None:
	zapisz_slad(
		doc.attached_to_name,
		tekst_sladu(
			"montaz_plik",
			akcja=akcja,
			sekcja=ETYKIETY_SLADU_MONTAZU[doc.attached_to_field],
			nazwa=doc.file_name,
		),
	)


def _to_plik_montazu(doc) -> bool:
	return doc.attached_to_doctype == "CRM Deal" and doc.attached_to_field in ETYKIETY_SLADU_MONTAZU


def slad_po_wgraniu(doc, method=None):
	"""`File.after_insert`: wlasny slad zamiast ogolnego komentarza "Attachment"."""
	if not _to_plik_montazu(doc):
		return
	# Rdzen Frappe w delete_doc najpierw robi delete_from_table (wiersz szansy
	# znika), a dopiero potem remove_all (kasuje podpiete File, a z nimi uruchamia
	# nasz hook). Komentarz z linkiem do nieistniejacej szansy wywalilby usuwanie.
	if not frappe.db.exists("CRM Deal", doc.attached_to_name):
		return
	nazwa = frappe.utils.escape_html(doc.file_name or "")
	_usun_ogolny_komentarz(doc, "Attachment", lambda tresc: nazwa in tresc)
	_slad_montazu(doc, "dodano")


def slad_po_usunieciu(doc, method=None):
	"""`File.on_trash`: wlasny slad zamiast ogolnego komentarza "Attachment Removed"."""
	if not _to_plik_montazu(doc):
		return
	# Rdzen Frappe w delete_doc najpierw robi delete_from_table (wiersz szansy
	# znika), a dopiero potem remove_all (kasuje podpiete File, a z nimi uruchamia
	# nasz hook). Komentarz z linkiem do nieistniejacej szansy wywalilby usuwanie.
	if not frappe.db.exists("CRM Deal", doc.attached_to_name):
		return
	_usun_ogolny_komentarz(doc, "Attachment Removed", lambda tresc: tresc == doc.file_name)
	_slad_montazu(doc, "usunięto")
