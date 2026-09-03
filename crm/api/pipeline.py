# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Warstwa frappe-owa nad `crm.volteo_pipeline` — pasek postępu rurociągu na
szansie sprzedaży, automatyczne przesuwanie statusu i dyspozytor powiadomień.

KSZTAŁT rurociągu (kolejność kroków, notatki „co dalej”) żyje wyłącznie w
`crm.volteo_pipeline` (frappe-free, testowalne bez frappe zainstalowanego
lokalnie). Ten moduł tylko odczytuje/zapisuje dokumenty `CRM Deal` i tworzy
powiadomienia — żadnej wiedzy o KOLEJNOŚCI statusów tu nie ma.

Frontend woła `volteo_pipeline_get` po PEŁNEJ, kropkowanej ścieżce
`crm.api.pipeline.volteo_pipeline_get` — gołe nazwy metod działają wyłącznie
dla Server Scriptów; skopiowanie wzorca wywołania z innej zakładki (bez
pełnej ścieżki) daje w runtime HTTP 417 mimo zielonych bramek lokalnych
(patrz `crm.api.umowa` i historia z `AudytTab.vue`).

Payload zwraca KSZTAŁT rurociągu (`steps`, `notes`) i osobno migawkę stanu
serwera w chwili odpytania (`status`, `current_index`, `off_pipeline*`,
`note`) — ta druga grupa pól zostaje z przyczyn diagnostycznych (sondy),
ale front NIE czyta jej już do wyznaczenia bieżącego kroku: `resource.reload()`
po zmianie statusu ściga się z zapisem samej tej zmiany (SAVE jeszcze
w locie), więc serwer potrafi oddać STARY status i front rysowałby pasek
jeden krok za późno. Bieżący indeks/tryb/notatka/odznaka liczą się teraz
po stronie klienta z `props.status` (prawda kliencka, ustawiona przez
dropdown natychmiast) i `notes`, patrz `frontend/src/utils/dealPipeline.js`.
"""

import json
from typing import Any

import frappe
from frappe import _

from crm.permissions.org_hierarchy import BYPASS_ROLES
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_pipeline import (
	NOTATKI,
	OZE_RODZAJE,
	dozwolone_stany,
	grupa_for,
	is_forward,
	notatka_for,
	parsuj_podzadania,
	pipeline_for,
	pipeline_key_for,
	podzadania_for,
	podzadanie_def,
	step_index,
)


def _sprawdz_dostep_do_szansy(deal: str, ptype: str = "read") -> None:
	"""Sprawdza istnienie szansy i uprawnienie `ptype` (domyślnie `read`) wywołującego do niej."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Szansa sprzedaży nie istnieje."), frappe.DoesNotExistError)
	if not frappe.has_permission("CRM Deal", ptype, deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)


@frappe.whitelist()
def volteo_pipeline_get(deal: str) -> dict[str, Any]:
	"""Zwraca KSZTAŁT paska rurociągu dla rodzaju umowy tej szansy (`steps`,
	`notes`, `group`, `subtasks`) plus migawkę stanu serwera w chwili odpytania
	(`status`, `current_index`, `off_pipeline*`, `note`).

	`subtasks` to katalog podzadań (`crm.volteo_pipeline.podzadania_for`) —
	zależy TYLKO od rodzaju umowy, więc istniejący cache payloadu per-rodzaj
	na froncie pozostaje ważny. Pusty dict dla rodzajów bez katalogu (OZE, na
	razie). Odczyt bieżącego STANU podzadań (zaakceptowane/błąd/nd) to osobny
	endpoint — poza zakresem tej funkcji.

	`group` to uporządkowany podzbiór statusów (kroki rurociągu plus statusy
	terminalne) do rozwijanej listy statusu na formularzu tej szansy — pusty,
	gdy rodzaj umowy nie ma rurociągu.

	Pusty `steps` (rodzaj umowy szansy bez rurociągu — np. nieustawiony) jest
	poprawną odpowiedzią, nie błędem: frontend ukrywa wtedy pasek zamiast go
	renderować pusty.

	Migawkowe pola (`status`, `current_index`, `off_pipeline`,
	`off_pipeline_type`, `note`) zostają dla sond/diagnostyki i pozostają
	poprawne w chwili odpytania — ale komponent paska już ich NIE używa do
	wyznaczenia bieżącego kroku, bo `resource.reload()` po zmianie statusu
	ściga się z zapisem samej tej zmiany i potrafi trafić na jeszcze-nie-
	zacommitowany stary status (patrz moduł, nagłówek pliku). Bieżący
	indeks/tryb/notatkę front liczy z `props.status` (klient) i `steps`/`notes`
	(ten payload) — stąd `notes` jest jedynym NOWYM polem, którego front
	faktycznie potrzebuje.
	"""
	_sprawdz_dostep_do_szansy(deal)

	rodzaj, status = frappe.db.get_value("CRM Deal", deal, ["custom_rodzaj_umowy", "status"])

	rurociag = pipeline_for(rodzaj)
	kroki = [{"status": nazwa, "index": indeks} for indeks, nazwa in enumerate(rurociag or ())]
	biezacy_indeks = step_index(rodzaj, status)

	klucz_rurociagu = pipeline_key_for(rodzaj)
	notatki = dict(NOTATKI.get(klucz_rurociagu, {})) if klucz_rurociagu else {}

	poza_rurociagiem = bool(rurociag) and biezacy_indeks == -1
	typ_poza_rurociagiem = None
	if poza_rurociagiem:
		typ_statusu = frappe.db.get_value("CRM Deal Status", status, "type")
		typ_poza_rurociagiem = typ_statusu if typ_statusu in ("Lost", "Won") else None

	return {
		"rodzaj": rodzaj,
		"status": status,
		"steps": kroki,
		"notes": notatki,
		"group": list(grupa_for(rodzaj) or ()),
		"current_index": biezacy_indeks,
		"off_pipeline": poza_rurociagiem,
		"off_pipeline_type": typ_poza_rurociagiem,
		"note": notatka_for(rodzaj, status),
		"subtasks": podzadania_for(rodzaj),
	}


@frappe.whitelist()
def volteo_podzadania_get(deal: str) -> dict[str, Any]:
	"""Zwraca bieżący STAN podzadań tej szansy (`crm.volteo_pipeline.parsuj_podzadania`
	na `custom_podzadania_json`), plus czy wywołujący ma prawo go zmieniać.

	Wymaga tylko `read` do szansy (jak `volteo_pipeline_get`) — samo podglądanie stanu
	podzadań (waiting/accepted/error/nd) nie jest tajemnicą kosztową/prowizyjną, więc
	handlowiec może je widzieć; `editable` mówi frontowi, czy pokazać kontrolki zmiany
	stanu, a faktyczny zapis i tak jest osobno bramkowany rolą w `volteo_podzadania_set`.

	Front woła po PEŁNEJ, kropkowanej ścieżce `crm.api.pipeline.volteo_podzadania_get`
	(patrz nagłówek modułu).
	"""
	_sprawdz_dostep_do_szansy(deal)

	raw = frappe.db.get_value("CRM Deal", deal, "custom_podzadania_json")
	return {
		"stan": parsuj_podzadania(raw),
		"editable": bool(set(frappe.get_roles()) & BYPASS_ROLES),
	}


@frappe.whitelist()
def volteo_podzadania_set(
	deal: str,
	zadanie: str,
	stan: str,
	data: str | None = None,
	note: str | None = None,
) -> dict[str, Any]:
	"""Ustawia (albo cofa, dla `stan="brak"`) stan jednego podzadania CP w mapie
	`custom_podzadania_json` tej szansy — read-modify-write jak `volteo_audyt_set_verdict`
	w `ops/crm-audyt.py`, ale jako zwykłe API forka (importy dozwolone, to nie Server Script).

	Zapis zarezerwowany dla ról backoffice/core-admin (`BYPASS_ROLES`) — brama roli jest
	PIERWSZYM sprawdzeniem, przed nawet istnieniem szansy, więc handlowiec (`Volteo D2D Sales`)
	dostaje `frappe.PermissionError` niezależnie od tego, czy `deal` w ogóle istnieje.

	Walidacja fail-fast w kolejności: rola → istnienie szansy + prawo `write` → istnienie
	definicji podzadania dla rodzaju umowy szansy → dozwolony `stan` (`dozwolone_stany`
	definicji, plus `"brak"` do cofnięcia) → `data` tylko gdy definicja ma `z_data=True` i musi
	parsować się jako data → `note` do 500 znaków po przycięciu białych znaków.

	Pusty/`None` `data` na wpisie z `z_data=True` USUWA istniejącą datę wpisu (wpis jest
	w całości nadpisywany nowym, nie łatany) — tak samo `note`. Zmiana jest zapisywana
	`frappe.db.set_value(..., update_modified=False)` (bez commitu — framework commituje na
	końcu requestu) i odnotowywana jako komentarz `Info` przez `zapisz_slad` — ślad trafia
	do Aktywności szansy przez czytnik komentarzy Info (`crm.api.activities`), bo
	`db.set_value` pomija tworzenie wersji/timeline.

	Sonda żywa (lokalnie, po dodaniu pola przez skrypt ops): rola `Volteo D2D Sales` musi
	dostać `frappe.PermissionError`; zapis rolą backoffice/core-admin musi wpisać się do
	`custom_podzadania_json` i pojawić w aktywności szansy jako komentarz.

	Front woła po PEŁNEJ, kropkowanej ścieżce `crm.api.pipeline.volteo_podzadania_set`
	(patrz nagłówek modułu).
	"""
	if not (set(frappe.get_roles()) & BYPASS_ROLES):
		frappe.throw(_("Brak uprawnień do zmiany stanu podzadań."), frappe.PermissionError)

	_sprawdz_dostep_do_szansy(deal, "write")

	rodzaj = frappe.db.get_value("CRM Deal", deal, "custom_rodzaj_umowy")
	definicja = podzadanie_def(rodzaj, zadanie)
	if definicja is None:
		frappe.throw(_("Nieznane zadanie: {0}").format(zadanie))

	stany_ok = dozwolone_stany(definicja) | {"brak"}
	if stan not in stany_ok:
		frappe.throw(_("Nieprawidłowy stan podzadania: {0}").format(stan))

	data = (data or "").strip() or None
	note = (note or "").strip() or None

	if data and not definicja.get("z_data"):
		frappe.throw(_("To zadanie nie przyjmuje daty."))
	if data:
		try:
			frappe.utils.getdate(data)
		except (ValueError, TypeError):
			frappe.throw(_("Nieprawidłowa data."))

	if note and len(note) > 500:
		frappe.throw(_("Notatka jest za długa (maksymalnie 500 znaków)."))

	raw = frappe.db.get_value("CRM Deal", deal, "custom_podzadania_json")
	mapa_biezaca = parsuj_podzadania(raw)
	mapa = dict(mapa_biezaca)

	if stan == "brak":
		mapa.pop(zadanie, None)
		tekst_komentarza = tekst_sladu("podzadanie", label=definicja["label"], stan=None, cofnieto=True)
	else:
		wpis = {"stan": stan, "by": frappe.session.user, "at": frappe.utils.now()}
		if data:
			wpis["data"] = data
		if note:
			wpis["note"] = note
		mapa[zadanie] = wpis

		tekst_komentarza = tekst_sladu("podzadanie", label=definicja["label"], stan=stan, note=note)

	frappe.db.set_value("CRM Deal", deal, "custom_podzadania_json", json.dumps(mapa), update_modified=False)
	zapisz_slad(deal, tekst_komentarza)

	return {"ok": True, "zadanie": zadanie, "stan": stan, "stan_mapa": mapa}


@frappe.whitelist()
def volteo_pipeline_grupy() -> dict[str, list[str]]:
	"""Zwraca słownik rodzaj umowy → grupa statusów (rurociąg plus statusy
	terminalne) dla KAŻDEGO `custom_rodzaj_umowy`, który ma rurociąg.

	Słownictwo na poziomie rodzaju, nie konkretnej szansy — potrzebne do
	zawężenia rozwijanej listy statusu na stronach `Deal`/`MobileDeal` oraz
	w modalach tworzenia/konwersji szansy, które jeszcze nie mają `deal`
	(więc `volteo_pipeline_get` tam nie zadziała). Odczyt bez sekretów —
	sama nazewnictwo statusów — więc jedyną bramką jest zalogowanie, bez
	dodatkowego sprawdzania uprawnień do konkretnego dokumentu.

	Front woła po PEŁNEJ, kropkowanej ścieżce
	`crm.api.pipeline.volteo_pipeline_grupy` (patrz nagłówek modułu).

	Kolejność wyjścia jest deterministyczna: rodzaje OZE w kolejności opcji
	pola Select (Fotowoltaika, Fotowoltaika + Magazyn, Magazyn energii), na
	końcu Czyste Powietrze.
	"""
	kolejnosc_oze = ("Fotowoltaika", "Fotowoltaika + Magazyn", "Magazyn energii")
	assert set(kolejnosc_oze) == OZE_RODZAJE, "kolejność OZE w volteo_pipeline_grupy rozjechała się z OZE_RODZAJE"
	rodzaje = (*kolejnosc_oze, "Czyste Powietrze")
	return {rodzaj: list(grupa_for(rodzaj) or ()) for rodzaj in rodzaje}


def advance_deal_status(deal: str, target_status: str, automation_key: str) -> bool:
	"""Automatycznie przesuwa status szansy do przodu w jej rurociągu, jeśli
	automatyzacja `automation_key` jest włączona i przejście jest do przodu.

	Wołane z punktów zaczepienia (generowanie PDF-u umowy, odebranie statusu
	„Podpisana” z Autenti) — NIGDY nie wolno jej pozwolić rzucić wyjątkiem:
	nieudana automatyzacja statusu nie może zepsuć operacji, która ją wywołała
	(wygenerowanie PDF-u / odpytanie Autenti). Stąd całe ciało w try/except.
	Zwraca `True`, jeśli status faktycznie został przesunięty, inaczej `False`
	(automatyzacja wyłączona/brak wiersza, przejście nie jest do przodu, albo
	dowolny inny błąd — zalogowany, nigdy niepodniesiony).
	"""
	try:
		# Fail-closed: brakujący wiersz (doctype może jeszcze nie istnieć na
		# świeżym dev-site — zakłada go dopiero skrypt ops) albo `wlaczona=0`
		# dają `None`/`0`, oba traktowane jako „nie uruchamiaj”.
		if not frappe.db.get_value("Volteo Automatyzacja", automation_key, "wlaczona"):
			return False

		doc = frappe.get_doc("CRM Deal", deal)
		if not is_forward(doc.custom_rodzaj_umowy, doc.status, target_status):
			return False

		# Celowo `doc.save()`, NIE `frappe.db.set_value` — tylko `.save()`
		# przechodzi przez `add_status_change_log` na kontrolerze `CRMDeal`,
		# więc automatyczne przejście zostaje odnotowane tak samo jak ręczne.
		doc.status = target_status
		doc.save(ignore_permissions=True)
		return True
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Volteo Pipeline: automatyzacja {automation_key} nie powiodła się")
		return False


_KANALY_STUB_DOKUMENTACJA = (
	"Scaffolding pod przyszłe kanały — nic tu jeszcze nie wysyła. E-mail czeka na "
	"własny silnik domenowy, SMS na integrację SMSAPI.pl (patrz REVISIT.md)."
)


def _wyslij_email_stub(recipient: str, deal: str, tekst_html: str) -> None:
	"""Zaślepka kanału e-mail. Integracja jeszcze nieistniejąca — patrz moduł, przypis
	`_KANALY_STUB_DOKUMENTACJA`. Świadomy no-op, nie błąd."""
	return


def _wyslij_sms_stub(recipient: str, deal: str, tekst_html: str) -> None:
	"""Zaślepka kanału SMS (SMSAPI.pl, planowane). Świadomy no-op, nie błąd —
	patrz moduł, przypis `_KANALY_STUB_DOKUMENTACJA`."""
	return


def _bell_notification(recipient: str, deal: str, tekst_html: str) -> None:
	"""Tworzy dzwoneczek `CRM Notification` dla jednego odbiorcy — wzorzec
	1:1 z `crm.fcrm.doctype.crm_notification.crm_notification.notify_user`
	i jego użyciem w `crm.api.todo.notify_assigned_user`, z tym że tu nadawcą
	jest zawsze bieżąca sesja (wołający joba/hooka), a nie właściciel dokumentu.
	Deduplikacja przez `frappe.db.exists` na tym samym zestawie wartości, żeby
	powtórne wywołanie tej samej automatyzacji (np. dwukrotny poll Autenti)
	nie zasypało odbiorcy identycznymi powiadomieniami.
	"""
	wartosci = frappe._dict(
		doctype="CRM Notification",
		from_user=frappe.session.user,
		to_user=recipient,
		type="Assignment",
		message=tekst_html,
		notification_text=tekst_html,
		notification_type_doctype="CRM Deal",
		notification_type_doc=deal,
		reference_doctype="CRM Deal",
		reference_name=deal,
	)
	if frappe.db.exists("CRM Notification", wartosci):
		return
	frappe.get_doc(wartosci).insert(ignore_permissions=True)


_KANALY = {
	"kanal_bell": _bell_notification,
	"kanal_email": _wyslij_email_stub,
	"kanal_sms": _wyslij_sms_stub,
}
"""Rejestr kanałów, klucz = nazwa flagi na `Volteo Automatyzacja`. Pluggable
scaffolding: dodanie realnego kanału e-mail/SMS to podmiana jednej wartości
w tym dict, bez zmiany `dispatch_notification`."""


def dispatch_notification(rule_key: str, deal: str, tekst_html: str) -> None:
	"""Wysyła powiadomienie o automatycznym zdarzeniu na rurociągu do odbiorców
	reguły `rule_key` (wiersz `Volteo Automatyzacja`), przez włączone kanały.

	Tak samo jak `advance_deal_status`, NIGDY nie rzuca — brak/wyłączona reguła,
	brak odbiorców i błąd pojedynczego kanału są po cichu pomijane/logowane, bo
	wołający (hook generowania PDF-u / poll Autenti) nie może zostać przerwany
	przez usterkę samego powiadomienia.
	"""
	try:
		regula = frappe.db.get_value(
			"Volteo Automatyzacja",
			rule_key,
			["wlaczona", "odbiorca_handlowiec", "kanal_bell", "kanal_email", "kanal_sms"],
			as_dict=True,
		)
		if not regula or not regula.wlaczona:
			return

		odbiorcy = set(
			frappe.get_all(
				"Volteo Automatyzacja Odbiorca",
				filters={"parent": rule_key, "parenttype": "Volteo Automatyzacja"},
				pluck="uzytkownik",
			)
		)
		if regula.odbiorca_handlowiec:
			wlasciciel = frappe.db.get_value("CRM Deal", deal, "deal_owner")
			if wlasciciel:
				odbiorcy.add(wlasciciel)

		# Bez samego wywołującego (np. handlowiec, który właśnie sam podpisał
		# akcję wyzwalającą automatyzację, nie musi dostać dzwoneczka o niej)
		# i bez pustych/`None` wpisów.
		odbiorcy = {o for o in odbiorcy if o and o != frappe.session.user}
		if not odbiorcy:
			return

		for flaga, kanal in _KANALY.items():
			if not regula.get(flaga):
				continue
			for odbiorca in odbiorcy:
				kanal(odbiorca, deal, tekst_html)
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Volteo Pipeline: dyspozytor powiadomień {rule_key} nie powiódł się")
