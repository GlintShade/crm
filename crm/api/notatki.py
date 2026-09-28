# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""API i hooki dokumentu `Volteo Notatka` -- fundament systemu notatek na
szansie, jeden doctype dla wszystkich zakladek (uwaga 43, baza pod uwage 40).
Frontend to osobne issue; ten modul jest kompletny sam w sobie (dodanie
notatki z pliku sondy jako handlowiec i jako Backend, odrzucenie
niedozwolonych operacji serwerowo).

Frontend woła te endpointy WYŁĄCZNIE pełną kropkowaną ścieżką
(`crm.api.notatki.*`) -- gołe nazwy metod dają HTTP 417, pułapka
udokumentowana przy innych whitelisted API forka (`Volteo Umowa`/
`Volteo Kredyt`/`crm.api.montaz`).

Doctype tworzy `ops/crm-notatki.py` w `proenergy-crm-ops` -- w tym forku go
nie ma; `doc_events` na nieistniejącym doctype są bezpieczne (patrz komentarz
przy innych Volteo doctype'ach w `crm/hooks.py`).

Bez pola Attach na notatce -- rdzeń Frappe tworzy drugi wiersz `File` przy
każdym zapisie dokumentu z Attach (znany tryb powielania na
`Volteo Faktura.plik`). Załączniki idą jako `File` podpięte pod `CRM Deal` ze
znacznikiem w `attached_to_field`, dokładnie jak galeria "Zdjęcia z
realizacji" (`crm.api.montaz`): upload roboczy wymaga write na `CRM Deal`
(handlowiec ma write na swojej szansie, na samej notatce celowo nie ma write),
uprawnienia pliku = uprawnienia szansy (odczyt przez `frappe.db.get_all`, nie
`frappe.get_all`, z tego samego powodu co `crm.api.activities.get_attachments`
i `crm.api.montaz.zdjecia_montazu` -- `File` ma uprawnienia owner-based, więc
zwykły `get_all` ukryłby handlowcowi pliki wgrane przez kolegów na tej samej
szansie), kasacja szansy kasuje pliki rdzeniem (kaskada w `crm.api.doc`).

Znacznik roboczy (`ZNACZNIK_ROBOCZY`) jest przepinany na znacznik docelowy
(`zbuduj_znacznik(notatka.name)`) przez `frappe.db.set_value` bezpośrednio na
kolumnie, NIE przez `File.save()` -- z dwóch powodów: (1) walidacja rdzenia
`SPECIAL_CHAR_PATTERN` nie dotyka wtedy zmiennego sufiksu nazwy notatki (ten
sam wzorzec sprawdzania jest robiony tylko raz, na etapie insertu pliku, nie
przy każdym przepięciu), (2) `crm.permissions.file_privacy` wymusza
`is_private=1` już przy PIERWSZYM zapisie pliku (upload roboczy), więc
`handle_is_private_changed` (rdzeń Frappe, patrz pułapka opisana w
`crm.api.montaz`) nigdy nie odpala się przy przepięciu -- `is_private` się
wtedy nie zmienia, zmienia się tylko `attached_to_field`.
"""

import frappe
from frappe import _

from crm.api.comment import extract_mentions
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.volteo_notatki import (
	DOCTYPE,
	DOZWOLONE_ROZSZERZENIA,
	ZAKLADKI,
	ZNACZNIK_ROBOCZY,
	normalizuj_komentarz_audytu,
	normalizuj_notatke,
	rozbij_znacznik,
	rozszerzenie,
	tekst_pusty,
	typy_dla,
	zbuduj_powiadomienie,
	zbuduj_znacznik,
	zbuduj_zrodla,
)

_POLA_WPISU = ["name", "zakladka", "typ", "data_zdarzenia", "tekst", "kredyt", "owner", "creation"]
_POLA_PLIKU = ["name", "file_name", "file_url", "file_type", "file_size", "owner", "creation"]

#: (doctype audytu, klucz zrodla feedu) -- kolejnosc jak w
#: `crm.volteo_notatki.ZRODLA_FEEDU` (Audyt przed AudytCP).
_DOCTYPY_AUDYTU_FEEDU = (("Volteo Audyt", "Audyt"), ("Volteo Audyt CP", "AudytCP"))


@frappe.whitelist()
def lista(deal: str, zakladka: str | None = None) -> dict:
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	filtry: dict = {"deal": deal}
	if zakladka:
		filtry["zakladka"] = zakladka

	# frappe.get_list (z hookiem widoczności, NIE frappe.get_all) -- notatka
	# jest widoczna dokładnie tak, jak jej szansa nadrzędna
	# (crm.permissions.faktura_visibility.get_notatka_permission_query_conditions).
	wpisy = frappe.get_list(
		DOCTYPE,
		filters=filtry,
		fields=_POLA_WPISU,
		order_by="data_zdarzenia desc, creation desc",
		limit_page_length=0,
	)

	autorzy: dict[str, str] = {}
	if wpisy:
		for wiersz in frappe.get_all(
			"User",
			filters={"name": ["in", list({w.owner for w in wpisy})]},
			fields=["name", "full_name"],
		):
			autorzy[wiersz.name] = wiersz.full_name

	# frappe.db.get_all (nie frappe.get_all): uprawnienia File są owner-based,
	# a wszystkie te pliki należą do RÓŻNYCH autorów na TEJ SAMEJ szansie.
	pliki_wszystkie = (
		frappe.db.get_all(
			"File",
			filters={"attached_to_doctype": "CRM Deal", "attached_to_name": deal},
			fields=["attached_to_field", *_POLA_PLIKU],
		)
		or []
	)

	pliki_per_notatka: dict[str, list] = {}
	robocze = []
	for plik in pliki_wszystkie:
		if plik.attached_to_field == ZNACZNIK_ROBOCZY:
			if plik.owner == frappe.session.user:
				robocze.append({klucz: plik[klucz] for klucz in _POLA_PLIKU})
			continue
		notatka_name = rozbij_znacznik(plik.attached_to_field)
		if not notatka_name:
			continue
		pliki_per_notatka.setdefault(notatka_name, []).append(
			{klucz: plik[klucz] for klucz in _POLA_PLIKU}
		)

	wynik = [
		{
			**wpis,
			"autor_nazwa": autorzy.get(wpis.owner) or wpis.owner,
			"pliki": pliki_per_notatka.get(wpis.name, []),
		}
		for wpis in wpisy
	]

	return {
		"wpisy": wynik,
		"robocze": robocze,
		"can_add": bool(frappe.has_permission(DOCTYPE, "create"))
		and bool(frappe.has_permission("CRM Deal", "read", deal)),
		"can_delete": bool(frappe.has_permission(DOCTYPE, "delete")),
	}


@frappe.whitelist()
def feed(deal: str) -> dict:
	"""Zakladka „Notatki" (issue ops#201, uwaga 40, faza 1 = tylko OZE): jeden
	strumien laczacy WSZYSTKIE notatki `Volteo Notatka` szansy (kazda
	zakladka naraz, nie tylko jedna jak `lista()`) z komentarzami watku
	„Komentarze" zakladki Audyt (`Volteo Audyt`/`Volteo Audyt CP`).
	Wylacznie widok -- bramkuje wylacznie odczyt, zaden zapis nie idzie przez
	ten endpoint.

	Kazde zrodlo komentarzy audytu jest w OSOBNYM `try/except` (wzor
	`crm.api.activities.get_volteo_linked_activities`): blad jednego zrodla
	(np. brak doctype'u na starszym srodowisku) nie psuje calego feedu, tylko
	pomija to jedno zrodlo i loguje `frappe.log_error`. Brak uprawnienia do
	dokumentu audytu (`frappe.has_permission`, wzor
	`crm.api.volteo_leady.komentarze`) rowniez tylko POMIJA to zrodlo -- w
	odroznieniu od `komentarze()`, ktora w tym samym przypadku RZUCA, bo tam
	caly widok jest jednym zrodlem; tu jedno pominiete zrodlo nie powinno
	psuc feedu zlozonego z wielu.

	Nazwiska: JEDNO zbiorcze zapytanie `User.full_name` po wszystkich
	autorach (notatek i komentarzy razem), tak jak w `lista()` -- nigdy
	`comment_by` z samego `Comment` (ten sam powod co w
	`crm.volteo_notatki.normalizuj_komentarz_audytu`: jedno zrodlo prawdy o
	imieniu i nazwisku, ktore odzwierciedla ewentualna zmiane nazwiska po
	fakcie).
	"""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	try:
		notatki_raw = (
			frappe.get_list(
				DOCTYPE,
				filters={"deal": deal},
				fields=_POLA_WPISU,
				order_by="data_zdarzenia desc, creation desc",
				limit_page_length=0,
			)
			if frappe.db.exists("DocType", DOCTYPE)
			else []
		)
	except Exception:
		frappe.log_error(title="Notatki: feed nie mógł pobrać Volteo Notatka", message=frappe.get_traceback())
		notatki_raw = []

	wlasciciele: set[str] = {w.owner for w in notatki_raw}

	pliki_per_notatka: dict[str, list] = {}
	if notatki_raw:
		try:
			pliki_notatek = (
				frappe.db.get_all(
					"File",
					filters={"attached_to_doctype": "CRM Deal", "attached_to_name": deal},
					fields=["attached_to_field", *_POLA_PLIKU],
				)
				or []
			)
			for plik in pliki_notatek:
				notatka_name = rozbij_znacznik(plik.attached_to_field)
				if not notatka_name:
					continue
				pliki_per_notatka.setdefault(notatka_name, []).append(
					{klucz: plik[klucz] for klucz in _POLA_PLIKU}
				)
		except Exception:
			frappe.log_error(
				title="Notatki: feed nie mógł pobrać plików notatek", message=frappe.get_traceback()
			)

	komentarze_raw: list[dict] = []
	for doctype_audytu, zrodlo in _DOCTYPY_AUDYTU_FEEDU:
		try:
			if not frappe.db.exists("DocType", doctype_audytu):
				continue
			# Autoname `field:deal`: dokument audytu (jesli istnieje) nazywa
			# sie dokladnie jak szansa -- `frappe.has_permission` na
			# nieistniejacym dokumencie rzuca DoesNotExistError zamiast
			# PermissionError, wiec istnienie sprawdzamy najpierw (wzor
			# `crm.api.volteo_leady.komentarze`).
			if not frappe.db.exists(doctype_audytu, deal):
				continue
			if not frappe.has_permission(doctype_audytu, "read", deal):
				continue
			wiersze = frappe.get_all(
				"Comment",
				filters={
					"reference_doctype": doctype_audytu,
					"reference_name": deal,
					"comment_type": "Comment",
				},
				fields=["name", "owner", "creation", "content"],
				order_by="creation asc",
				limit_page_length=200,
			)
		except Exception:
			frappe.log_error(
				title="Notatki: feed nie mógł pobrać komentarzy audytu",
				message=f"doctype={doctype_audytu}\n{frappe.get_traceback()}",
			)
			continue

		for wiersz in wiersze:
			wlasciciele.add(wiersz.owner)
			komentarze_raw.append({**wiersz, "zrodlo": zrodlo})

	autorzy: dict[str, str] = {}
	if wlasciciele:
		for wiersz in frappe.get_all(
			"User", filters={"name": ["in", list(wlasciciele)]}, fields=["name", "full_name"]
		):
			autorzy[wiersz.name] = wiersz.full_name

	pliki_per_komentarz: dict[str, list] = {}
	if komentarze_raw:
		try:
			pliki_komentarzy = (
				frappe.db.get_all(
					"File",
					filters={
						"attached_to_doctype": "Comment",
						"attached_to_name": ["in", [k["name"] for k in komentarze_raw]],
					},
					fields=["attached_to_name", *_POLA_PLIKU],
				)
				or []
			)
			for plik in pliki_komentarzy:
				pliki_per_komentarz.setdefault(plik.attached_to_name, []).append(
					{klucz: plik[klucz] for klucz in _POLA_PLIKU}
				)
		except Exception:
			frappe.log_error(
				title="Notatki: feed nie mógł pobrać plików komentarzy audytu",
				message=frappe.get_traceback(),
			)

	wpisy_znormalizowane: list[dict] = []
	liczniki: dict[str, int] = {}

	for wpis in notatki_raw:
		wzbogacony = {
			**wpis,
			"autor_nazwa": autorzy.get(wpis.owner) or wpis.owner,
			"pliki": pliki_per_notatka.get(wpis.name, []),
		}
		znormalizowany = normalizuj_notatke(wzbogacony)
		wpisy_znormalizowane.append(znormalizowany)
		liczniki[znormalizowany["zrodlo"]] = liczniki.get(znormalizowany["zrodlo"], 0) + 1

	for komentarz in komentarze_raw:
		wzbogacony = {
			**komentarz,
			"autor_nazwa": autorzy.get(komentarz["owner"]) or komentarz["owner"],
			"pliki": pliki_per_komentarz.get(komentarz["name"], []),
		}
		znormalizowany = normalizuj_komentarz_audytu(wzbogacony, komentarz["zrodlo"])
		wpisy_znormalizowane.append(znormalizowany)
		liczniki[znormalizowany["zrodlo"]] = liczniki.get(znormalizowany["zrodlo"], 0) + 1

	wpisy_znormalizowane.sort(key=lambda wpis: wpis.get("data") or "", reverse=True)

	return {
		"wpisy": wpisy_znormalizowane,
		"zrodla": zbuduj_zrodla(liczniki),
		"can_delete": bool(frappe.has_permission(DOCTYPE, "delete")),
	}


@frappe.whitelist(methods=["POST"])
def dodaj(
	deal: str,
	zakladka: str,
	tekst: str,
	typ: str = "Notatka",
	pliki: str | list | None = None,
	kredyt: str | None = None,
) -> dict:
	pliki_lista = frappe.parse_json(pliki or [])

	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"deal": deal,
			"zakladka": zakladka,
			"typ": typ,
			"tekst": tekst,
			"kredyt": kredyt,
		}
	)
	# BEZ ignore_permissions: DocPerm create (Volteo D2D Sales / Volteo
	# Backend / admini) i widoczność-po-szansie (has_notatka_permission,
	# fail-closed) decydują, czy insert w ogóle przejdzie; validate() (hook w
	# tym module) sprawdza tekst/zakladkę/typ/kredyt.
	doc.insert()

	for plik_name in pliki_lista:
		plik = frappe.db.get_value(
			"File",
			plik_name,
			["name", "attached_to_doctype", "attached_to_name", "attached_to_field", "owner", "file_name"],
			as_dict=True,
			for_update=True,
		)
		if not plik:
			frappe.throw(_("Załącznik {0} nie istnieje.").format(plik_name))
		if (
			plik.attached_to_doctype != "CRM Deal"
			or plik.attached_to_name != deal
			or plik.attached_to_field != ZNACZNIK_ROBOCZY
			or plik.owner != frappe.session.user
		):
			frappe.throw(_("Nieprawidłowy załącznik."))
		if rozszerzenie(plik.file_name) not in DOZWOLONE_ROZSZERZENIA:
			frappe.throw(_("Niedozwolone rozszerzenie pliku: {0}.").format(plik.file_name))
		frappe.db.set_value(
			"File", plik_name, "attached_to_field", zbuduj_znacznik(doc.name), update_modified=False
		)

	pliki_wynik = []
	if pliki_lista:
		pliki_wynik = (
			frappe.db.get_all(
				"File",
				filters={
					"attached_to_doctype": "CRM Deal",
					"attached_to_name": deal,
					"attached_to_field": zbuduj_znacznik(doc.name),
				},
				fields=_POLA_PLIKU,
			)
			or []
		)

	return {
		"name": doc.name,
		"zakladka": doc.zakladka,
		"typ": doc.typ,
		"data_zdarzenia": doc.data_zdarzenia,
		"tekst": doc.tekst,
		"kredyt": doc.kredyt,
		"owner": doc.owner,
		"creation": doc.creation,
		"autor_nazwa": frappe.get_cached_value("User", doc.owner, "full_name") or doc.owner,
		"pliki": pliki_wynik,
	}


@frappe.whitelist(methods=["POST"])
def usun_plik_roboczy(deal: str, name: str) -> None:
	plik = frappe.db.get_value(
		"File",
		name,
		["attached_to_doctype", "attached_to_name", "attached_to_field", "owner"],
		as_dict=True,
	)
	if (
		not plik
		or plik.attached_to_doctype != "CRM Deal"
		or plik.attached_to_name != deal
		or plik.attached_to_field != ZNACZNIK_ROBOCZY
		or plik.owner != frappe.session.user
	):
		frappe.throw(_("Załącznik nie istnieje."), frappe.DoesNotExistError)
	frappe.delete_doc("File", name, ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def usun(deal: str, name: str) -> None:
	if not frappe.db.exists(DOCTYPE, {"name": name, "deal": deal}):
		frappe.throw(_("Notatka nie istnieje."), frappe.DoesNotExistError)
	# BEZ ignore_permissions: DocPerm delete (wyłącznie System Manager /
	# Volteo Core Admin -- decyzja właściciela "bez edycji i bez usuwania z
	# UI", serwerowo D2D i Backend mają read+create) decyduje, czy to w ogóle
	# przejdzie. on_trash (poniżej) sprząta załączniki.
	frappe.delete_doc(DOCTYPE, name)


def sprzatnij_robocze() -> int:
	"""Job dzienny (`scheduler_events["daily"]` w `crm/hooks.py`): kasuje
	`File` ze znacznikiem `ZNACZNIK_ROBOCZY` starsze niż 24h -- upload
	rozpoczęty, ale nigdy nie dopięty do żadnej notatki (rep otworzył okno
	dodawania notatki, wgrał plik, zamknął okno bez zapisu). Zwraca liczbę
	skasowanych wierszy."""
	odciecie = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-24)
	nazwy = frappe.get_all(
		"File",
		filters={"attached_to_field": ZNACZNIK_ROBOCZY, "creation": ["<", odciecie]},
		pluck="name",
	)
	for nazwa in nazwy:
		frappe.delete_doc("File", nazwa, ignore_permissions=True)
	return len(nazwy)


# ---------------------------------------------------------------------------
# doc_events("Volteo Notatka") -- wpięte w crm/hooks.py
# ---------------------------------------------------------------------------


def validate(doc, method: str | None = None) -> None:
	if tekst_pusty(doc.get("tekst")):
		frappe.throw(_("Treść notatki nie może być pusta."))
	if doc.get("zakladka") not in ZAKLADKI:
		frappe.throw(_("Nieznana zakładka notatki: {0}").format(doc.get("zakladka")))
	dozwolone_typy = typy_dla(doc.get("zakladka"))
	if doc.get("typ") not in dozwolone_typy:
		frappe.throw(
			_("Typ „{0}” nie jest dozwolony dla zakładki {1}.").format(doc.get("typ"), doc.get("zakladka"))
		)
	if doc.get("kredyt"):
		kredyt_deal = frappe.db.get_value("Volteo Kredyt", doc.get("kredyt"), "deal")
		if kredyt_deal != doc.get("deal"):
			frappe.throw(_("Wybrany formularz kredytowy nie należy do tej szansy."))


def after_insert(doc, method: str | None = None) -> None:
	# Błąd wysyłki powiadomienia NIGDY nie wycofuje samej notatki -- to log
	# procesu handlowego, nie dokument finansowy; utrata notatki byłaby
	# gorsza niż utrata jednego powiadomienia o wzmiance (ta sama zasada co
	# crm.api.trify.after_insert).
	try:
		autor_nazwa = frappe.get_cached_value("User", doc.owner, "full_name") or doc.owner
		for wzmianka in extract_mentions(doc.get("tekst")):
			if not wzmianka.email:
				continue
			notify_user(
				zbuduj_powiadomienie(doc.owner, autor_nazwa, doc.deal, doc.name, doc.zakladka, wzmianka.email)
			)
	except Exception:
		frappe.log_error(title="Notatki: powiadomienie o wzmiance", message=frappe.get_traceback())


def on_trash(doc, method: str | None = None) -> None:
	znacznik = zbuduj_znacznik(doc.name)
	for plik_name in frappe.get_all(
		"File",
		filters={"attached_to_doctype": "CRM Deal", "attached_to_name": doc.deal, "attached_to_field": znacznik},
		pluck="name",
	):
		frappe.delete_doc("File", plik_name, ignore_permissions=True)


def odlacz_kredyt(doc, method: str | None = None) -> None:
	"""doc_events("Volteo Kredyt")["on_trash"] -- zeruje `kredyt` we
	wszystkich notatkach wskazujących na kasowany formularz kredytowy, żeby
	`LinkExistsError` rdzenia nie zablokował usunięcia `Volteo Kredyt`
	(notatka przeżywa usunięcie formularza, traci tylko powiązanie -- ten
	sam wzorzec co reszta modułu: kasacja rodzica nigdy nie kasuje notatek
	poza kaskadą całej szansy)."""
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	for name in frappe.get_all(DOCTYPE, filters={"kredyt": doc.name}, pluck="name"):
		frappe.db.set_value(DOCTYPE, name, "kredyt", None, update_modified=False)
