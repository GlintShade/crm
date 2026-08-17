"""Whitelisted API integracji Autenti dla podpisu elektronicznego DWÓCH dokumentów:
UMOWY (`Volteo Umowa`) i formularza kredytowego (`Volteo Kredyt`, od b47).

Oba doctype'y są 1:1 z `CRM Deal` (`autoname: field:deal`), więc nazwa dokumentu
jest tożsama z nazwą szansy — `deal` i `<dokument>_name` poniżej to zawsze ten
sam string, ale sygnatury funkcji trzymają je osobno dla czytelności i
zgodności z odpowiednikiem tego kodu dla `Volteo Oferta`.

Wspólny przepływ obu dokumentów żyje za modułowymi słownikami konfiguracji
(`KONFIG_UMOWA`, `KONFIG_KREDYT`, zebrane w `KONFIGURACJE`) — jedyna różnica
między wysyłką umowy i wysyłką formularza kredytowego to WARTOŚCI w tych
słownikach (doctype, sposób pobrania rekordu, sposób odnalezienia PDF-u do
wysyłki, generatory tytułu/nazw plików, i czy podpisanie przesuwa rurociąg
szansy), nigdy osobna kopia logiki.

Wysyłka do podpisu wysyła DOKŁADNIE te bajty PDF-u, które rep już wygenerował
i przejrzał przez `volteo_umowa_pdf`/`volteo_kredyt_pdf` — NIGDY świeżo
wyrenderowane w tle. Klient musi podpisać to samo, co przedstawiciel widział.

Statusy zapisujemy przez `frappe.db.set_value`, nie przez `doc.save()` — żeby
odpytywanie w tle (`poll_autenti_status`) i wysyłka nigdy nie ścigały się
z równoległym zapisem formularza przez przedstawiciela w przeglądarce.
"""

from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from crm.api.kredyt import DOCTYPE as KREDYT_DOCTYPE
from crm.api.kredyt import _pobierz_kredyt, _sprawdz_rodzaj_oze
from crm.api.pipeline import advance_deal_status
from crm.api.umowa import DOCTYPE as UMOWA_DOCTYPE
from crm.api.umowa import (
	_dane_kontaktu,
	_pobierz_umowe,
	_podstawowy_kontakt,
	_sprawdz_dostep_do_szansy,
	_sprawdz_role,
)
from crm.integrations.autenti import logika
from crm.integrations.autenti.client import AutentiClient


def _autenti_ustawienia() -> dict[str, Any]:
	"""Odczyt Single `Volteo Autenti Settings` przez `get_singles_dict`.

	`get_single_value` kłamie o nieustawionym polu (zwraca 0/"" zamiast None dla
	Single, który nigdy nie był zapisany) — dlatego tu świadomie NIE jest używany.
	"""
	return frappe.db.get_singles_dict("Volteo Autenti Settings") or {}


def _wlaczone() -> bool:
	return bool(_autenti_ustawienia().get("enabled"))


def _pdf_umowy_plik(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca rekord `File` PDF-u umowy (niepodpisanej) tej szansy, albo `None`, gdy go brak."""
	nazwy = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": logika.nazwa_pliku_umowy(deal),
		},
		pluck="name",
		limit=1,
	)
	if not nazwy:
		return None
	return frappe.get_doc("File", nazwy[0])


def _pdf_kredytu_plik(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca rekord `File` NAJNOWSZEGO wygenerowanego PDF-u formularza kredytowego tej
	szansy, albo `None`, gdy go brak.

	W odróżnieniu od `_pdf_umowy_plik` (dopasowanie po dokładnej, stałej nazwie), PDF-y
	formularza kredytowego są zapisywane ZNACZNIKOWANE w czasie
	(`Formularz-kredytowy-<deal>-YYYYMMDD-HHMMSS.pdf`, patrz `volteo_kredyt_pdf` w
	`crm/api/kredyt.py`) — dopasowanie idzie więc po PREFIKSIE, biorąc najnowszy wpis
	wg `creation`.

	Wzorzec eskejpowania `%`/`_` w prefiksie MUSI zostać zsynchronizowany z
	`crm.api.kredyt._usun_stare_pliki_kredytu` — obie funkcje dopasowują ten sam
	zestaw plików tym samym LIKE (jedna sprząta stare, druga szuka najnowszego
	źródła do wysyłki); rozjazd wzorca zepsułby jedną z nich po cichu.
	"""
	prefiks = logika.prefiks_pliku_kredytu(deal)
	wzorzec = prefiks.replace("%", r"\%").replace("_", r"\_") + "%.pdf"
	nazwy = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": ["like", wzorzec],
		},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if not nazwy:
		return None
	return frappe.get_doc("File", nazwy[0])


def _identyfikacja_podpisujacego(deal_doc: "frappe.model.document.Document") -> dict[str, Any] | None:
	"""Dane podstawowego kontaktu szansy do podpisu Autenti: imię, nazwisko, pełne imię
	i nazwisko, e-mail. Używa dokładnie tych samych helperów co `volteo_umowa_pdf`
	(`_podstawowy_kontakt` + `_dane_kontaktu`), żeby podpisujący na dokumencie Autenti
	nigdy nie mógł się rozjechać z klientem widocznym na samej umowie. Wspólna dla
	obu dokumentów — to zawsze ten sam podstawowy kontakt tej samej szansy.

	Zwraca `None` TYLKO gdy szansa nie ma podstawowego kontaktu — brak e-maila jest
	dozwolonym stanem do wyświetlenia (podglądu w `_status_dokumentu`), blokuje
	dopiero samą wysyłkę (`_wyslij_dokument` sprawdza `email` osobno).
	"""
	kontakt = _podstawowy_kontakt(deal_doc)
	if not kontakt:
		return None

	# `_dane_kontaktu` zwraca "" (nigdy None) dla brakujących pól — to poprawne dla
	# `prefill` formularza, ale kontrakt tej funkcji to `str | None`, więc email jest
	# tu jawnie sprowadzany do None, gdy pusty.
	dane = _dane_kontaktu(kontakt)
	first_name = (dane.get("first_name") or "").strip()
	last_name = (dane.get("last_name") or "").strip()
	full_name = f"{first_name} {last_name}".strip()
	email = dane.get("email") or None

	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


def _staly_podpisujacy(ustawienia: dict[str, Any]) -> dict[str, Any] | None:
	"""Stały podpisujący (prezes) z `Volteo Autenti Settings` — SIGNER na każdym
	dokumencie, obok klienta. Zwraca `None`, dopóki imię, nazwisko i e-mail nie są
	wszystkie skompletowane w ustawieniach — częściowo wypełniony rekord nie
	jest wystarczający, żeby dodać stronę do procesu dokumentu."""
	first_name = (ustawienia.get("staly_podpisujacy_imie") or "").strip()
	last_name = (ustawienia.get("staly_podpisujacy_nazwisko") or "").strip()
	email = (ustawienia.get("staly_podpisujacy_email") or "").strip()
	if not (first_name and last_name and email):
		return None
	full_name = f"{first_name} {last_name}".strip()
	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


def _archiwum(ustawienia: dict[str, Any]) -> dict[str, Any] | None:
	"""Stały adres archiwizacyjny z `Volteo Autenti Settings` — VIEWER na każdym
	dokumencie. `first_name`/`last_name`/`full_name` są stałą etykietą ("Archiwum
	ProEnergy"), bo widok Autenti wymaga jakiejś nazwy dla strony, a to nie jest
	osoba. Zwraca `None`, gdy adres e-mail nie jest ustawiony."""
	email = (ustawienia.get("wglad_archiwum_email") or "").strip()
	if not email:
		return None
	return {
		"first_name": "Archiwum",
		"last_name": "ProEnergy",
		"full_name": "Archiwum ProEnergy",
		"email": email,
	}


def _handlowiec(user: str | None) -> dict[str, Any] | None:
	"""Handlowiec — użytkownik CRM wysyłający dokument do podpisu — VIEWER na każdym
	dokumencie. Przyjmuje `user` JAWNIE zamiast czytać `frappe.session.user`
	bezpośrednio: w zadaniu w tle (`_autenti_send_job`) sesja workera nie
	jest sesją wysyłającego, więc tożsamość musi zostać przekazana z żądania
	HTTP (ten sam moment co stemplowanie `sent_by`), nie odczytana ponownie.

	Zwraca `None` dla `Administrator`/`Guest`, brakującego e-maila, albo adresu
	kończącego się na `@example.com` (brak realnej skrzynki) — takiego
	handlowca pomijamy, zamiast dodawać martwego VIEWER-a do procesu.
	"""
	if not user or user in ("Administrator", "Guest"):
		return None
	user_doc = frappe.get_doc("User", user)
	email = (user_doc.email or user or "").strip()
	if not email or email.lower().endswith("@example.com"):
		return None
	first_name = (user_doc.first_name or "").strip()
	last_name = (user_doc.last_name or "").strip()
	full_name = (user_doc.full_name or "").strip() or f"{first_name} {last_name}".strip() or email
	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


KONFIG_UMOWA: dict[str, Any] = {
	"rodzaj": "umowa",
	"doctype": UMOWA_DOCTYPE,
	"pobierz": _pobierz_umowe,
	"znajdz_pdf": _pdf_umowy_plik,
	"nazwa_wysylki": logika.nazwa_pliku_umowy,
	"nazwa_podpisanego": logika.nazwa_pliku_podpisanego,
	"tytul": logika.tytul_dokumentu,
	"awansuj_po_podpisie": True,
	# Pełne zdania, nie budowane z osobnej "etykiety" przez wspólny szablon: polska
	# odmiana (rodzaj gramatyczny rzeczownika, przypadki: "umowę"/"umowy" vs
	# "formularz kredytowy" bez odmiany w tych samych miejscach) sprawia, że
	# jeden dzielony szablon produkuje błędną gramatykę dla jednego z dwóch
	# dokumentów — stąd gotowe, przetestowane literały per dokument.
	"komunikat_brak_rekordu": "Najpierw wygeneruj umowę dla tej szansy sprzedaży.",
	"komunikat_brak_pdf": "Najpierw wygeneruj PDF umowy.",
	"komunikat_w_toku": "Umowa jest już w trakcie podpisywania lub podpisana.",
}
"""Konfiguracja dokumentu UMOWA dla wspólnego przepływu wysyłki/statusu/odpytywania
poniżej. `awansuj_po_podpisie=True`: podpisanie umowy przesuwa rurociąg szansy do
etapu „Umowa Podpisana” (`crm.volteo_pipeline`), analogicznie jak przed b47."""

KONFIG_KREDYT: dict[str, Any] = {
	"rodzaj": "kredyt",
	"doctype": KREDYT_DOCTYPE,
	"pobierz": _pobierz_kredyt,
	"znajdz_pdf": _pdf_kredytu_plik,
	"nazwa_wysylki": logika.nazwa_pliku_kredytu,
	"nazwa_podpisanego": logika.nazwa_pliku_kredytu_podpisanego,
	"tytul": logika.tytul_dokumentu_kredytu,
	"awansuj_po_podpisie": False,
	# Pełne zdania — patrz komentarz przy `KONFIG_UMOWA` powyżej o tym, czemu nie ma
	# tu wspólnego szablonu. "Formularz kredytowy" jest rodzaju męskiego, stąd
	# "został podpisany" (nie "podpisana", jak dla "Umowa").
	"komunikat_brak_rekordu": "Najpierw wypełnij formularz kredytowy dla tej szansy sprzedaży.",
	"komunikat_brak_pdf": "Najpierw wygeneruj PDF formularza kredytowego.",
	"komunikat_w_toku": "Formularz kredytowy jest już w trakcie podpisywania lub został podpisany.",
}
"""Konfiguracja dokumentu KREDYT (od b47). `awansuj_po_podpisie=False` jest
CELOWE: formularz kredytowy nie ma własnego etapu w `crm.volteo_pipeline` (żaden z
OZE_RODZAJE ani CP nie zyskał etapu „Kredyt”) — decyzja właściciela, 2026-08-17.
Jego podpisanie aktualizuje wyłącznie `Volteo Kredyt.autenti_status`/`signed_at` i
podpina podpisany plik; status szansy pozostaje nietknięty."""

KONFIGURACJE: dict[str, dict[str, Any]] = {"umowa": KONFIG_UMOWA, "kredyt": KONFIG_KREDYT}
"""Rejestr wszystkich dokumentów obsługiwanych przez tę integrację, kluczowany
`rodzaj` — `poll_autenti_status` iteruje po tym słowniku, `_autenti_send_job`
wybiera z niego konfigurację po nazwie przekazanej przez kolejkę."""


@frappe.whitelist()
def autenti_is_enabled() -> dict[str, Any]:
	"""Tani, bezstanowy check widoczności funkcji podpisu w UI. Bez gate'u dostępu do
	szansy — to globalny stan integracji, nie dane konkretnego dokumentu."""
	ustawienia = _autenti_ustawienia()
	return {"enabled": bool(ustawienia.get("enabled")), "environment": ustawienia.get("environment")}


def _status_dokumentu(deal: str, konfig: dict[str, Any]) -> dict[str, Any]:
	"""Zwraca pełny stan podpisu Autenti dokumentu `konfig["rodzaj"]` tej szansy.
	Wspólne ciało `autenti_umowa_status`/`autenti_kredyt_status` — obsługuje zarówno
	pierwsze wczytanie zakładki, jak i odpytywanie co 30 s przez frontend — to
	jeden, tani endpoint per dokument, żeby te dwa przypadki nigdy się nie rozjechały.
	"""
	ustawienia = _autenti_ustawienia()
	if not ustawienia.get("enabled"):
		return {"enabled": False}

	dokument = konfig["pobierz"](deal)
	deal_doc = frappe.get_doc("CRM Deal", deal)
	identyfikacja = _identyfikacja_podpisujacego(deal_doc)

	# Informacyjny podgląd pełnej listy odbiorców (klient/prezes/handlowiec/archiwum) —
	# ten sam budulec co w `_autenti_send_job`, więc podgląd nigdy nie rozjeżdża
	# się z tym, co faktycznie trafi do procesu dokumentu. Zwracany zawsze, gdy
	# integracja jest włączona — także po wysyłce, wyłącznie informacyjnie.
	proponowani_odbiorcy = logika.zbuduj_odbiorcow(
		identyfikacja,
		_staly_podpisujacy(ustawienia),
		_handlowiec(frappe.session.user),
		_archiwum(ustawienia),
	)

	return {
		"enabled": True,
		"environment": ustawienia.get("environment"),
		"dokument_exists": dokument is not None,
		"pdf_exists": bool(konfig["znajdz_pdf"](deal)),
		"autenti_status": dokument.get("autenti_status") if dokument else None,
		"signer_name": dokument.get("signer_name") if dokument else None,
		"signer_email": dokument.get("signer_email") if dokument else None,
		"sent_at": dokument.get("sent_at") if dokument else None,
		"signed_at": dokument.get("signed_at") if dokument else None,
		"error_message": dokument.get("error_message") if dokument else None,
		"signed_pdf_file": dokument.get("signed_pdf_file") if dokument else None,
		"proposed_signer": (
			{"full_name": identyfikacja["full_name"], "email": identyfikacja["email"]}
			if identyfikacja
			else None
		),
		"proposed_recipients": proponowani_odbiorcy,
	}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def autenti_umowa_status(deal: str) -> dict[str, Any]:
	"""Zwraca pełny stan podpisu Autenti dla umowy tej szansy. Obsługuje zarówno
	pierwsze wczytanie zakładki, jak i odpytywanie co 30 s przez frontend — to
	jeden, tani endpoint, żeby te dwa przypadki nigdy się nie rozjechały."""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	wynik = _status_dokumentu(deal, KONFIG_UMOWA)
	if "dokument_exists" in wynik:
		# Zgodność wdrożeniowa: `dokument_exists` to nowy, ogólny klucz od b47
		# (dzielony z `autenti_kredyt_status`), ale ewentualny nieodświeżony
		# frontend z okna wdrożenia może jeszcze czytać wyłącznie starą nazwę
		# `umowa_exists` — dublujemy pod nią tę samą wartość, żeby taki frontend
		# nie stracił po cichu przycisku wysyłki.
		wynik["umowa_exists"] = wynik["dokument_exists"]
	return wynik


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def autenti_kredyt_status(deal: str) -> dict[str, Any]:
	"""Odpowiednik `autenti_umowa_status` dla formularza kredytowego (od b47). Celowo
	BEZ bramki `_sprawdz_rodzaj_oze` — analogicznie do `volteo_kredyt_get`
	(`crm/api/kredyt.py`): zakładka Kredyt jest ukrywana dla linii Czyste Powietrze
	w UI, a sam odczyt statusu podpisu nie ujawnia niczego wrażliwego, więc nie ma
	powodu blokować go twardym błędem — np. przy odświeżeniu widoku tuż po
	przełączeniu „Rodzaju umowy” szansy na Czyste Powietrze.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	return _status_dokumentu(deal, KONFIG_KREDYT)


def _wyslij_dokument(deal: str, konfig: dict[str, Any]) -> dict[str, Any]:
	"""Wysyła dokument `konfig["rodzaj"]` tej szansy do podpisu przez Autenti
	(asynchronicznie — kolejkuje `_autenti_send_job` i wraca natychmiast). Wspólne
	ciało `autenti_send_umowa`/`autenti_send_kredyt` — bramki i ich kolejność są
	identyczne dla obu dokumentów.
	"""
	if not _wlaczone():
		frappe.throw(_("Integracja Autenti jest wyłączona."))

	dokument = konfig["pobierz"](deal)
	if dokument is None:
		frappe.throw(_(konfig["komunikat_brak_rekordu"]))

	if not konfig["znajdz_pdf"](deal):
		frappe.throw(_(konfig["komunikat_brak_pdf"]))

	if not logika.mozna_wyslac(dokument.get("autenti_status")):
		frappe.throw(_(konfig["komunikat_w_toku"]))

	deal_doc = frappe.get_doc("CRM Deal", deal)
	podpisujacy = _identyfikacja_podpisujacego(deal_doc)
	if not podpisujacy or not podpisujacy["email"]:
		frappe.throw(_("Kontakt szansy nie ma adresu e-mail — uzupełnij go w CRM."))

	ustawienia = _autenti_ustawienia()
	if not _staly_podpisujacy(ustawienia) or not _archiwum(ustawienia):
		# Prezes podpisuje KAŻDY dokument (patrz docstring modułu i specyfikacja) —
		# ciche wysłanie bez niego byłoby defektem, nie tylko brakiem funkcji.
		frappe.throw(_("Uzupełnij stałego podpisującego i adres archiwum w Ustawieniach Autenti."))

	# Wysyłający jest przechwytywany TERAZ (żądanie HTTP, `frappe.session.user`
	# wiarygodny) i przekazywany do joba jako jawny argument kolejki — job w
	# tle działa w sesji workera, gdzie `frappe.session.user` nie jest już
	# wysyłającym. To ten sam moment/źródło co stemplowanie `sent_by` niżej,
	# celowo bez ponownego odczytu, żeby uniknąć wyścigu.
	wysylajacy = frappe.session.user

	# `frappe.db.set_value` zamiast `doc.save()` — nie ryzykujemy ścigania się
	# z równoległym zapisem formularza przez przedstawiciela w przeglądarce.
	frappe.db.set_value(
		konfig["doctype"],
		deal,
		{
			"autenti_status": "Wysyłanie",
			"signer_name": podpisujacy["full_name"],
			"signer_email": podpisujacy["email"],
			"sent_by": wysylajacy,
			"error_message": None,
		},
		update_modified=False,
	)
	frappe.db.commit()

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_job",
		queue="default",
		timeout=300,
		deal=deal,
		wysylajacy=wysylajacy,
		rodzaj=konfig["rodzaj"],
	)

	return {"autenti_status": "Wysyłanie"}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def autenti_send_umowa(deal: str) -> dict[str, Any]:
	"""Wysyła PDF umowy tej szansy do podpisu przez Autenti (asynchronicznie —
	kolejkuje `_autenti_send_job` i wraca natychmiast)."""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	return _wyslij_dokument(deal, KONFIG_UMOWA)


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def autenti_send_kredyt(deal: str) -> dict[str, Any]:
	"""Odpowiednik `autenti_send_umowa` dla formularza kredytowego (od b47). DODATKOWO
	sprawdza `_sprawdz_rodzaj_oze` przed delegacją — parytet z `volteo_kredyt_pdf`
	(`crm/api/kredyt.py`): formularz kredytowy dotyczy wyłącznie linii OZE, więc próba
	wysłania go do podpisu dla szansy Czyste Powietrze jest błędem danych szansy, nie
	stanem roboczym formularza.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	return _wyslij_dokument(deal, KONFIG_KREDYT)


def _autenti_send_job(deal: str, wysylajacy: str | None = None, rodzaj: str = "umowa") -> None:
	"""Zadanie w tle: pobiera zapisany PDF dokumentu `rodzaj` (NIGDY świeży render —
	patrz docstring modułu) i wywołuje Autenti, żeby utworzyć proces dokumentu, dodać
	CZTERECH odbiorców (klient + prezes jako SIGNER-zy, handlowiec + archiwum jako
	VIEWER-zy — patrz `logika.zbuduj_odbiorcow`), wgrać plik i wysłać (podpis
	równoległy: wszyscy odbiorcy są dodani przed jednym wywołaniem `send()`).
	Status w CRM osiąga „Podpisana” dopiero, gdy zdalny proces jest COMPLETED,
	czyli po podpisaniu przez OBU sygnatariuszy.

	`rodzaj` wybiera konfigurację z `KONFIGURACJE` (`"umowa"`/`"kredyt"`); domyślne
	`"umowa"` jest tu wyłącznie dla zgodności ze starą sygnaturą wywoływaną przez
	`_autenti_send_umowa_job` (patrz jej docstring niżej).

	`wysylajacy` to id użytkownika CRM, który wykonał wysyłkę — przekazywane
	jawnie z `_wyslij_dokument` (patrz jej docstring), bo sesja workera nie
	jest sesją wysyłającego. Nie jest whitelisted — wywoływane wyłącznie przez
	`frappe.enqueue`.
	"""
	konfig = KONFIGURACJE[rodzaj]
	dokument = konfig["pobierz"](deal)
	if dokument is None:
		# Rekord zniknął między enqueue a wykonaniem joba — nie powinno się zdarzyć
		# (formularz się nie usuwa), ale nie ma gdzie zapisać stanu błędu.
		frappe.log_error(
			title=f"Autenti: brak {konfig['doctype']} w jobie wysyłki",
			message=f"Szansa: {deal}",
		)
		return

	try:
		plik = konfig["znajdz_pdf"](deal)
		if plik is None:
			frappe.db.set_value(
				konfig["doctype"],
				deal,
				{"autenti_status": "Błąd", "error_message": "PDF zniknął przed wysyłką."},
				update_modified=False,
			)
			frappe.db.commit()
			return
		pdf_bytes = plik.get_content()

		deal_doc = frappe.get_doc("CRM Deal", deal)
		podpisujacy = _identyfikacja_podpisujacego(deal_doc)
		if not podpisujacy or not podpisujacy["email"]:
			frappe.db.set_value(
				konfig["doctype"],
				deal,
				{"autenti_status": "Błąd", "error_message": "Kontakt szansy nie ma adresu e-mail."},
				update_modified=False,
			)
			frappe.db.commit()
			return

		ustawienia = _autenti_ustawienia()

		# Defensywne powtórzenie bramki z `_wyslij_dokument`: ustawienia mogły się
		# zmienić w oknie między akceptacją żądania a wykonaniem joba w tle. Job nie
		# może rzucić do przeglądarki — jedyna droga to zapisany stan błędu.
		prezes = _staly_podpisujacy(ustawienia)
		archiwum = _archiwum(ustawienia)
		if not prezes or not archiwum:
			frappe.db.set_value(
				konfig["doctype"],
				deal,
				{
					"autenti_status": "Błąd",
					"error_message": "Brak stałego podpisującego lub adresu archiwum w Ustawieniach Autenti.",
				},
				update_modified=False,
			)
			frappe.db.commit()
			return

		handlowiec = _handlowiec(wysylajacy)
		odbiorcy = logika.zbuduj_odbiorcow(podpisujacy, prezes, handlowiec, archiwum)

		signature_type = ustawienia.get("default_signature_type") or "BASIC"
		tytul = konfig["tytul"](podpisujacy["full_name"])

		client = AutentiClient()
		doc_id = client.create_document_process(title=tytul)
		for odbiorca in odbiorcy:
			# first_name/last_name pochodzą osobno z helpera kontaktu/ustawień/User,
			# nigdy z rozbicia pełnego imienia i nazwiska po spacji (zawodzi dla
			# nazwisk wieloczłonowych).
			party_kwargs: dict[str, Any] = {
				"first_name": odbiorca["first_name"] or odbiorca["full_name"],
				"last_name": odbiorca["last_name"],
				"email": odbiorca["email"],
				"role": odbiorca["role"],
			}
			if odbiorca["role"] == "SIGNER":
				party_kwargs["signature_type"] = signature_type
			client.add_party(doc_id, **party_kwargs)
		client.upload_file(doc_id, filename=konfig["nazwa_wysylki"](deal), pdf_bytes=pdf_bytes)
		client.send(doc_id)

		frappe.db.set_value(
			konfig["doctype"],
			deal,
			{
				"autenti_status": "Wysłana",
				"autenti_document_id": doc_id,
				"sent_at": frappe.utils.now(),
				"error_message": None,
			},
			update_modified=False,
		)
		frappe.db.commit()
	except Exception as exc:
		frappe.log_error(
			title=f"Autenti: wysyłka {konfig['doctype']} nie powiodła się",
			message=f"Szansa: {deal}\n{frappe.get_traceback()}",
		)
		frappe.db.set_value(
			konfig["doctype"],
			deal,
			{"autenti_status": "Błąd", "error_message": str(exc)[:500]},
			update_modified=False,
		)
		frappe.db.commit()


def _autenti_send_umowa_job(deal: str, wysylajacy: str | None = None) -> None:
	"""Cienki shim delegujący do `_autenti_send_job(deal, wysylajacy, rodzaj="umowa")`.

	Zachowany pod STARĄ, kropkowaną ścieżką
	(`crm.integrations.autenti.api._autenti_send_umowa_job`) — `frappe.enqueue`
	serializuje dotted path, nie referencję funkcji w pamięci, więc jakikolwiek job
	zakolejkowany pod tą nazwą TUŻ PRZED wdrożeniem tej zmiany (a wykonany PO
	restarcie workerów kolejki) musi nadal trafić do działającej funkcji, zamiast
	dead-letterować na nieistniejącej już nazwie.
	"""
	_autenti_send_job(deal, wysylajacy, rodzaj="umowa")


def _attach_signed_pdf(deal: str, umowa_name: str, doc_id: str, konfig: dict[str, Any]) -> None:
	"""Pobiera podpisany PDF z Autenti i podpina go jako prywatny `File` do rekordu
	dokumentu `konfig["doctype"]`, zapisując jego url w `signed_pdf_file`. `deal` i
	`umowa_name` są zawsze tym samym stringiem (oba doctype'y są 1:1 z `CRM Deal`,
	`autoname: field:deal`) — trzymane osobno dla czytelności, na wzór odpowiednika
	dla oferty.

	Cały błąd jest łapany i logowany, nigdy nie propaguje — utrata samego załącznika
	nie może cofnąć już zapisanego przejścia statusu na „Podpisana”.
	"""
	try:
		client = AutentiClient()
		file_id = client.get_signed_file_id(doc_id)
		if not file_id:
			frappe.log_error(
				title="Autenti: brak podpisanego pliku",
				message=f"{konfig['doctype']}: {umowa_name}\nProces dokumentu: {doc_id}\nBrak jeszcze pliku podpisanego.",
			)
			return

		content = client.download_file_content(doc_id, file_id)

		plik = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": konfig["nazwa_podpisanego"](deal),
				"attached_to_doctype": konfig["doctype"],
				"attached_to_name": umowa_name,
				"is_private": 1,
				"content": content,
			}
		)
		plik.insert(ignore_permissions=True)

		frappe.db.set_value(konfig["doctype"], umowa_name, "signed_pdf_file", plik.file_url, update_modified=False)
		frappe.db.commit()
	except Exception:
		frappe.log_error(
			title="Autenti: pobranie podpisanego pliku nie powiodło się",
			message=f"{konfig['doctype']}: {umowa_name}\nProces dokumentu: {doc_id}\n{frappe.get_traceback()}",
		)
		frappe.db.commit()


def poll_autenti_status() -> None:
	"""Zadanie harmonogramu (co 10 min, patrz `hooks.py`): sprawdza status wszystkich
	dokumentów w stanie „Wysłana” przez API Autenti — dla KAŻDEGO skonfigurowanego
	typu dokumentu w `KONFIGURACJE` — i aktualizuje odpowiedni rekord
	(`Volteo Umowa`/`Volteo Kredyt`).

	Skan każdego doctype'u jest owinięty WŁASNYM try/except: schemat `Volteo Kredyt`
	(kolumny `autenti_status`/`autenti_document_id`) może na danej instalacji nie być
	jeszcze wdrożony (np. okno między deployem obrazu z tym kodem a odpaleniem
	skryptu ops dodającego pola) — brakująca kolumna przy skanowaniu jednego
	doctype'u nie może zablokować odpytania drugiego, już działającego.
	"""
	if not _wlaczone():
		return

	client = AutentiClient()
	for konfig in KONFIGURACJE.values():
		try:
			wiersze = frappe.get_all(
				konfig["doctype"],
				filters={"autenti_status": "Wysłana", "autenti_document_id": ["is", "set"]},
				fields=["name", "autenti_document_id"],
			)
			if not wiersze:
				continue

			for wiersz in wiersze:
				try:
					zdalny = client.get_status(wiersz.autenti_document_id)
					zdalny_status = zdalny.get("status")
					nowy_status = logika.STATUS_MAP.get(zdalny_status)
					if not nowy_status:
						if zdalny_status in logika.PENDING_REMOTE_STATUSES:
							# Nieterminalny stan zdalny — dokument zasadnie czeka na podpis
							# dni, więc NIGDY nie logujemy tego jako błąd (zalałoby Error Log).
							continue
						frappe.log_error(
							title="Autenti: nierozpoznany status",
							message=f"{konfig['doctype']}: {wiersz.name}\nProces dokumentu: {wiersz.autenti_document_id}\n"
							f"Nierozpoznany zdalny status: {zdalny_status}",
						)
						continue

					aktualizacja: dict[str, Any] = {"autenti_status": nowy_status}
					if nowy_status == "Podpisana":
						aktualizacja["signed_at"] = frappe.utils.now()
					frappe.db.set_value(konfig["doctype"], wiersz.name, aktualizacja, update_modified=False)
					frappe.db.commit()

					if nowy_status == "Podpisana":
						if konfig["awansuj_po_podpisie"]:
							# Automatyzacja: przesuwa status szansy do przodu, o ile włączona w
							# panelu admina i przejście jest do przodu w JEJ rurociągu; nigdy
							# nie rzuca — awaria automatyzacji nie może cofnąć już zapisanego
							# statusu podpisu ani zablokować pobrania podpisanego pliku poniżej.
							# Ten worker nie ma sesji wołającego (scheduler), więc `doc.save()`
							# wewnątrz `advance_deal_status` zapisuje jako wołający zadania w
							# tle. Formularz kredytowy (`konfig["awansuj_po_podpisie"] is
							# False`) celowo NIGDY tu nie trafia — nie ma własnego etapu w
							# `crm.volteo_pipeline` (decyzja właściciela, 2026-08-17).
							advance_deal_status(wiersz.name, "Umowa Podpisana", "umowa_podpisana")
							frappe.db.commit()
						_attach_signed_pdf(wiersz.name, wiersz.name, wiersz.autenti_document_id, konfig)
				except Exception:
					frappe.log_error(
						title="Autenti: odpytanie statusu nie powiodło się",
						message=f"{konfig['doctype']}: {wiersz.name}\n{frappe.get_traceback()}",
					)
					frappe.db.commit()
		except Exception:
			frappe.log_error(
				title=f"Autenti: odpytanie statusu {konfig['doctype']} nie powiodło się",
				message=frappe.get_traceback(),
			)
