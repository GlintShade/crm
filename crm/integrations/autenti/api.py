"""Whitelisted API integracji Autenti dla podpisu elektronicznego DWÓCH dokumentów:
UMOWY (`Volteo Umowa`) i formularza kredytowego (`Volteo Kredyt`, od b47).

UMOWA pozostaje 1:1 z `CRM Deal` (`autoname: field:deal`) -- nazwa dokumentu jest
tożsama z nazwą szansy, `deal` i nazwa rekordu poniżej to zawsze ten sam string.

FORMULARZ KREDYTOWY od ops#158/#159 jest N:1 -- jedna szansa może mieć wiele
rekordów `Volteo Kredyt`, każdy z własną, wygenerowaną (hashową) nazwą, więc
`deal` sam w sobie już NIE wskazuje jednoznacznie "ten jeden" formularz. Od
ops#160 wspólny przepływ tego modułu operuje więc na NAZWIE REKORDU (`nazwa`),
nie na `deal`, i wyprowadza `deal` z załadowanego rekordu (`dokument.deal`) w
miejscach, które go faktycznie potrzebują (ślad aktywności na szansie, awans
statusu procesu, wyprowadzenie `CRM Deal` dla podpisującego). Endpointy umowy
zostają kluczowane po `deal` (bo to i tak ten sam string), endpointy kredytu
(`autenti_kredyt_status`, `autenti_send_kredyt`) -- po `kredyt` (nazwa rekordu).

Wspólny przepływ obu dokumentów żyje za modułowymi słownikami konfiguracji
(`KONFIG_UMOWA`, `KONFIG_KREDYT`, zebrane w `KONFIGURACJE`) -- jedyna różnica
między wysyłką umowy i wysyłką formularza kredytowego to WARTOŚCI w tych
słownikach (doctype, sposób pobrania rekordu, sposób odnalezienia PDF-u do
wysyłki, generatory tytułu/nazw plików, sposób wyprowadzenia podpisującego i czy
podpisanie przesuwa proces szansy), nigdy osobna kopia logiki.

Wysyłka do podpisu wysyła DOKŁADNIE te bajty PDF-u, które rep już wygenerował
i przejrzał przez `volteo_umowa_pdf`/`volteo_kredyt_pdf` -- NIGDY świeżo
wyrenderowane w tle. Klient musi podpisać to samo, co przedstawiciel widział.

Statusy zapisujemy przez `frappe.db.set_value`, nie przez `doc.save()` -- żeby
odpytywanie w tle (`poll_autenti_status`) i wysyłka nigdy nie ścigały się
z równoległym zapisem formularza przez przedstawiciela w przeglądarce.
"""

from typing import Any

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit

from crm.api.kredyt import DOCTYPE as KREDYT_DOCTYPE
from crm.api.kredyt import _kredyt_po_nazwie, _sprawdz_rodzaj_oze
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
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_kredyt import kontakt_z_wnioskodawcy, pasuje_plik_kredytu


def _autenti_ustawienia() -> dict[str, Any]:
	"""Odczyt Single `Volteo Autenti Settings` przez `get_singles_dict`.

	`get_single_value` kłamie o nieustawionym polu (zwraca 0/"" zamiast None dla
	Single, który nigdy nie był zapisany) - dlatego tu świadomie NIE jest używany.
	"""
	return frappe.db.get_singles_dict("Volteo Autenti Settings") or {}


def _wlaczone() -> bool:
	"""Czy integracja Autenti jest wlaczona - patrz `logika.czy_wlaczone` dla
	uzasadnienia, dlaczego to NIE jest goly `bool(...)`: `_autenti_ustawienia`
	czyta przez `get_singles_dict`, ktore zwraca wartosci Single jako stringi,
	wiec pole Check ustawione na 0 przychodzi tu jako string "0", a
	`bool("0")` jest `True` w Pythonie. Ten sam blad byl obecny (i naprawiony
	w tym samym miejscu, ops#169) w kazdym innym miejscu tego modulu, ktore
	czytalo `enabled` z tego samego slownika - patrz `autenti_is_enabled` i
	`_status_dokumentu` nizej, teraz routowane przez ta sama funkcje albo
	wprost przez `logika.czy_wlaczone`."""
	return logika.czy_wlaczone(_autenti_ustawienia().get("enabled"))


def _pdf_umowy_plik(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca rekord `File` NAJNOWSZEGO PDF-u umowy (niepodpisanej) tej szansy,
	albo `None`, gdy go brak.

	W odróżnieniu od pierwotnej wersji (dopasowanie po DOKŁADNEJ, stałej
	nazwie `logika.nazwa_pliku_umowy(deal)`), dopasowanie idzie po PREFIKSIE,
	tak jak `_pdf_kredytu_plik` niżej. Powód: Frappe nie nadpisuje pliku o
	istniejącej nazwie przy kolejnym `insert()` - przy kolizji ścieżki na
	dysku dokleja losowy sufiks do nazwy NOWEGO pliku (`Umowa-PRO-CP-26-1024.pdf`
	→ `Umowa-PRO-CP-26-1024e41034.pdf`). Taka kolizja może dziś powstać nawet
	bez żadnego błędu w tej szansie - wystarczy, że plik o dokładnie tej samej
	nazwie zostanie wgrany pod INNĄ szansą (zob. `crm.volteo_zalaczniki.czy_nazwa_systemowa`,
	rezerwacja nazw dla dowolnej szansy wprowadzona jako follow-up do ops#77) -
	dopasowanie po dokładnej nazwie wtedy trwale nie znajdowałoby prawdziwego
	PDF-u, a regeneracja by tego nie naprawiała.

	Wzorzec eskejpowania `%`/`_` w prefiksie MUSI zostać zsynchronizowany z
	`crm.api.umowa._usun_stare_pdfy_umowy` (analogicznie jak `_pdf_kredytu_plik`
	z `crm.api.kredyt._usun_stare_pliki_kredytu`) - obie funkcje dopasowują ten
	sam zestaw plików tym samym LIKE (jedna sprząta stare, druga szuka
	najnowszego źródła do wysyłki); rozjazd wzorca zepsułby jedną z nich po cichu.

	Podpisane PDF-y (`...-podpisana.pdf`, `logika.nazwa_pliku_podpisanego`)
	wpinają się pod `Volteo Umowa`, nie pod `CRM Deal` - ten LIKE (filtrowany po
	`attached_to_doctype == "CRM Deal"`) ich więc nie złapie, co jest zamierzone:
	ta funkcja szuka źródła do WYSŁANIA do podpisu, nie już podpisanego wyniku.
	"""
	prefiks = logika.nazwa_pliku_umowy(deal)[: -len(".pdf")]
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


def _pdf_umowy_plik_dla_wysylki(deal: str, nazwa: str) -> "frappe.model.document.Document | None":
	"""Adapter 2-argumentowy nad `_pdf_umowy_plik`, dopasowujący kształt wywołania do
	wspólnego przepływu (`konfig["znajdz_pdf"](deal, nazwa)`, gdzie `nazwa` to
	nazwa rekordu dokumentu, ops#160). Dla umowy `nazwa` jest zawsze tożsama z
	`deal` (`Volteo Umowa` pozostaje 1:1 z szansą, `autoname: field:deal`) i jest
	tu świadomie ignorowana - `_pdf_umowy_plik` operuje wyłącznie na `deal`."""
	return _pdf_umowy_plik(deal)


def _nazwa_pliku_umowy_wysylki(deal: str, nazwa: str) -> str:
	"""Adapter 2-argumentowy nad `logika.nazwa_pliku_umowy`, patrz
	`_pdf_umowy_plik_dla_wysylki` powyżej - `nazwa` jest tu świadomie ignorowana."""
	return logika.nazwa_pliku_umowy(deal)


def _nazwa_pliku_umowy_podpisanego(deal: str, nazwa: str) -> str:
	"""Adapter 2-argumentowy nad `logika.nazwa_pliku_podpisanego`, patrz
	`_pdf_umowy_plik_dla_wysylki` powyżej - `nazwa` jest tu świadomie ignorowana."""
	return logika.nazwa_pliku_podpisanego(deal)


def _pdf_kredytu_plik(deal: str, kredyt_name: str) -> "frappe.model.document.Document | None":
	"""Zwraca rekord `File` NAJNOWSZEGO wygenerowanego PDF-u formularza kredytowego
	KONKRETNEGO rekordu `Volteo Kredyt` (`kredyt_name`) tej szansy, albo `None`,
	gdy go brak (ops#160).

	Od ops#158/#159 jedna szansa może mieć wiele formularzy kredytowych, każdy z
	własnym prefiksem nazwy pliku (`logika.prefiks_pliku_kredytu`: legacy bez
	sufiksu vs hashowy z 8-znakowym sufiksem `kredyt_name`). Prefiks BAZOWY szansy
	(`prefiks_pliku_kredytu(deal, deal)`, wariant legacy) jest jednocześnie ścisłym
	prefiksem STRINGA nazwy pliku KAŻDEGO rodzeństwa hashowego tej samej szansy -
	samo dopasowanie LIKE po nim złapałoby więc pliki WSZYSTKICH formularzy naraz,
	dokładnie ta sama pułapka, co w `crm.api.kredyt._usun_stare_pliki_kredytu`
	(ta funkcja jest jej odpowiednikiem po stronie wysyłki: tamta sprząta stare,
	ta szuka najnowszego źródła). Stąd DWA kroki: LIKE po prefiksie bazowym
	(szeroki, tani odczyt kandydatów z bazy), potem `crm.volteo_kredyt.pasuje_plik_kredytu`
	w Pythonie (wąski, precyzyjny per `kredyt_name`) - patrz jej docstring dla
	pełnego opisu obu kształtów (legacy vs hash) i dlaczego rekord hashowy
	dopasowuje WYŁĄCZNIE pliki niosące jego WŁASNY 8-znakowy sufiks.

	Kandydaci są posortowani `creation desc`, więc pierwszy dopasowany przez
	`pasuje_plik_kredytu` jest już ten najnowszy.

	Wzorzec eskejpowania `%`/`_` w prefiksie MUSI zostać zsynchronizowany z
	`crm.api.kredyt._usun_stare_pliki_kredytu` - obie funkcje dopasowują ten sam
	zestaw plików tym samym LIKE (jedna sprząta stare, druga szuka najnowszego
	źródła do wysyłki); rozjazd wzorca zepsułby jedną z nich po cichu.
	"""
	prefiks_bazowy = logika.prefiks_pliku_kredytu(deal, deal)
	wzorzec = prefiks_bazowy.replace("%", r"\%").replace("_", r"\_") + "%.pdf"
	kandydaci = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": ["like", wzorzec],
		},
		fields=["name", "file_name"],
		order_by="creation desc",
	)
	for kandydat in kandydaci:
		if pasuje_plik_kredytu(kandydat.file_name, prefiks_bazowy, kredyt_name, deal):
			return frappe.get_doc("File", kandydat.name)
	return None


def _kredyt_po_nazwie_lub_none(nazwa: str) -> "frappe.model.document.Document | None":
	"""Zwraca dokument `Volteo Kredyt` po nazwie rekordu, albo `None`, gdy nie
	istnieje (ops#160).

	Adapter dla `KONFIG_KREDYT["pobierz"]`: w odróżnieniu od
	`crm.api.kredyt._kredyt_po_nazwie` (rzuca czytelny błąd, analog HTTP 404 -
	właściwe zachowanie dla endpointów formularza wywoływanych wprost z nazwą
	rekordu z przeglądarki), wspólny przepływ tego modułu (`_status_dokumentu`,
	`_wyslij_dokument`, `_autenti_send_job`, ...) jednolicie sprawdza `dokument is
	None` dla OBU dokumentów - dla umowy `_pobierz_umowe` też nigdy nie rzuca -
	i musi zachować się tak samo, gdy w `_autenti_send_job` rekord zniknie między
	`enqueue` a wykonaniem joba w tle: rzucony wyjątek uciekłby wtedy niezłapany
	z workera (ten fragment kodu jest poza `try/except` joba).

	Endpointy (`autenti_kredyt_status`/`autenti_send_kredyt`) walidują istnienie
	rekordu WCZEŚNIEJ, przez `crm.api.kredyt._kredyt_po_nazwie` (rzucającą), więc
	`dokument is None` z tej funkcji jest w praktyce osiągalne tylko w oknie
	wyścigu (rekord skasowany między bramką endpointu a tym odczytem).
	"""
	if not nazwa or not frappe.db.exists(KREDYT_DOCTYPE, nazwa):
		return None
	return frappe.get_doc(KREDYT_DOCTYPE, nazwa)


def _identyfikacja_podpisujacego(deal_doc: "frappe.model.document.Document") -> dict[str, Any] | None:
	"""Dane podstawowego kontaktu szansy do podpisu Autenti UMOWY: imię, nazwisko,
	pełne imię i nazwisko, e-mail. Używa dokładnie tych samych helperów co
	`volteo_umowa_pdf` (`_podstawowy_kontakt` + `_dane_kontaktu`), żeby podpisujący
	na dokumencie Autenti nigdy nie mógł się rozjechać z klientem widocznym na
	SAMEJ UMOWIE.

	Od ops#160 ten niezmiennik dotyczy WYŁĄCZNIE umowy - formularz kredytowy ma
	własny, analogiczny niezmiennik (podpisujący formularza kredytowego nigdy nie
	może się rozjechać z wnioskodawcą widocznym na SAMYM FORMULARZU), zrealizowany
	osobno w `_podpisujacy_kredyt` niżej (czyta blok `wnioskodawca_*` KONKRETNEGO
	rekordu, nie kontakt podstawowy szansy).

	Zwraca `None` TYLKO gdy szansa nie ma podstawowego kontaktu - brak e-maila jest
	dozwolonym stanem do wyświetlenia (podglądu w `_status_dokumentu`), blokuje
	dopiero samą wysyłkę (`_wyslij_dokument` sprawdza `email` osobno).
	"""
	kontakt = _podstawowy_kontakt(deal_doc)
	if not kontakt:
		return None

	# `_dane_kontaktu` zwraca "" (nigdy None) dla brakujących pól - to poprawne dla
	# `prefill` formularza, ale kontrakt tej funkcji to `str | None`, więc email jest
	# tu jawnie sprowadzany do None, gdy pusty.
	dane = _dane_kontaktu(kontakt)
	first_name = (dane.get("first_name") or "").strip()
	last_name = (dane.get("last_name") or "").strip()
	full_name = f"{first_name} {last_name}".strip()
	email = dane.get("email") or None

	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


def _drugi_podpisujacy_umowa(
	dokument: "frappe.model.document.Document | None",
) -> dict[str, Any] | None:
	"""Dane drugiego Zamawiającego umowy jako kandydat SIGNER (ops#169), albo `None`,
	gdy umowa nie istnieje albo nie ma ustawionego `drugi_zamawiajacy` (ops#168, pole
	Link do `Contact` na `Volteo Umowa`). Używa dokładnie tego samego helpera co
	`_identyfikacja_podpisujacego` dla kontaktu podstawowego (`_dane_kontaktu`), żeby
	drugi podpisujący na dokumencie Autenti nigdy nie mógł się rozjechać z drugim
	Zamawiającym widocznym na SAMEJ UMOWIE.

	Pusty/brakujący e-mail jest zwrócony jako `None` w wynikowym słowniku, nie jako
	pusty string: `zbuduj_odbiorcow` i `emaile_podpisujacych_rozlaczne` traktują taki
	kandydat jako pomijalny (kontakt istnieje, ale nie ma jeszcze e-maila), `_wyslij_dokument`
	blokuje na tym wysyłkę osobnym komunikatem, nazwanym po tej konkretnej osobie."""
	if dokument is None:
		return None
	drugi = dokument.get("drugi_zamawiajacy")
	if not drugi:
		return None

	dane = _dane_kontaktu(drugi)
	first_name = (dane.get("first_name") or "").strip()
	last_name = (dane.get("last_name") or "").strip()
	full_name = f"{first_name} {last_name}".strip()
	email = dane.get("email") or None
	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


def _podpisujacy_umowa(
	deal_doc: "frappe.model.document.Document", dokument: "frappe.model.document.Document | None"
) -> list[dict[str, Any] | None]:
	"""`konfig["podpisujacy"]` dla UMOWY (ops#160, listowany od ops#169) - zwraca
	uporządkowaną LISTĘ kandydatów SIGNER dla klienta: pierwszy element to zawsze
	kontakt podstawowy szansy (`_identyfikacja_podpisujacego`, cienki adapter jak
	poprzednio), drugi element (obecny WYŁĄCZNIE, gdy `dokument.drugi_zamawiajacy`
	jest ustawiony) to drugi Zamawiający wariantu umowy podwójnej
	(`_drugi_podpisujacy_umowa`). Lista ma więc jeden element dla umowy pojedynczej,
	dwa dla podwójnej - nigdy więcej.

	Pierwszy element może sam być `None` (brak kontaktu podstawowego na szansie) -
	lista wtedy ma jednoznacznie `[None]`, zgodność z zachowaniem sprzed listy, gdzie
	`_identyfikacja_podpisujacego` zwracało `None` wprost. Drugi element jest
	DOPISYWANY do listy tylko, gdy `_drugi_podpisujacy_umowa` zwróci słownik (czyli
	`drugi_zamawiajacy` jest ustawiony) - nigdy jako `None` na końcu listy, żeby
	długość listy sama w sobie mówiła, czy to wariant podwójny."""
	lista: list[dict[str, Any] | None] = [_identyfikacja_podpisujacego(deal_doc)]
	drugi = _drugi_podpisujacy_umowa(dokument)
	if drugi is not None:
		lista.append(drugi)
	return lista


def _podpisujacy_kredyt(
	deal_doc: "frappe.model.document.Document", dokument: "frappe.model.document.Document | None"
) -> list[dict[str, Any] | None]:
	"""`konfig["podpisujacy"]` dla FORMULARZA KREDYTOWEGO (ops#160, listowany od ops#169):
	podpisujący jest wnioskodawcą zapisanym NA TYM KONKRETNYM rekordzie `Volteo Kredyt`
	(blok `wnioskodawca_*`, `crm.volteo_kredyt.kontakt_z_wnioskodawcy`), NIGDY kontaktem
	podstawowym szansy - każdy formularz kredytowy tej samej szansy ma swojego
	WŁASNEGO wnioskodawcę, mogącego się różnić od klienta widocznego na umowie i
	od wnioskodawcy INNEGO formularza tej samej szansy. Ten niezmiennik lustrzanie
	odbija ten z `_identyfikacja_podpisujacego` (umowa): podpisujący formularza
	kredytowego nigdy nie może się rozjechać z wnioskodawcą widocznym na SAMYM
	FORMULARZU. Formularz kredytowy nie ma drugiego podpisującego (jeden wnioskodawca
	na rekord) - zachowanie tej funkcji jest więc BAJT W BAJT takie samo jak przed
	ops#169, opakowane w jednoelementową listę.

	`deal_doc` jest tu świadomie ignorowany (trzymany wyłącznie dla zgodności
	kształtu wywołania z `_podpisujacy_umowa`). Zwraca `[None]` tylko wtedy, gdy
	`dokument` sam jest `None` (okno wyścigu opisane w `_kredyt_po_nazwie_lub_none`)
	- w normalnym przepływie rekord zawsze tu istnieje, więc zwraca listę ze
	słownikiem nawet gdy wszystkie pola wnioskodawcy są puste (spójne z tym, że
	`prefill` formularza wypełnia ten blok od razu przy założeniu rekordu,
	`crm.api.kredyt.volteo_kredyt_create`)."""
	if dokument is None:
		return [None]
	surowy = kontakt_z_wnioskodawcy(dokument.as_dict())
	first_name = (surowy.get("first_name") or "").strip()
	last_name = (surowy.get("last_name") or "").strip()
	full_name = f"{first_name} {last_name}".strip()
	email = surowy.get("email") or None
	return [{"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}]


def _staly_podpisujacy(ustawienia: dict[str, Any]) -> dict[str, Any] | None:
	"""Stały podpisujący (prezes) z `Volteo Autenti Settings` - SIGNER na każdym
	dokumencie, obok klienta. Zwraca `None`, dopóki imię, nazwisko i e-mail nie są
	wszystkie skompletowane w ustawieniach - częściowo wypełniony rekord nie
	jest wystarczający, żeby dodać stronę do procesu dokumentu."""
	first_name = (ustawienia.get("staly_podpisujacy_imie") or "").strip()
	last_name = (ustawienia.get("staly_podpisujacy_nazwisko") or "").strip()
	email = (ustawienia.get("staly_podpisujacy_email") or "").strip()
	if not (first_name and last_name and email):
		return None
	full_name = f"{first_name} {last_name}".strip()
	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


def _archiwum(ustawienia: dict[str, Any]) -> dict[str, Any] | None:
	"""Stały adres archiwizacyjny z `Volteo Autenti Settings` - VIEWER na każdym
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
	"""Handlowiec - użytkownik CRM wysyłający dokument do podpisu - VIEWER na każdym
	dokumencie. Przyjmuje `user` JAWNIE zamiast czytać `frappe.session.user`
	bezpośrednio: w zadaniu w tle (`_autenti_send_job`) sesja workera nie
	jest sesją wysyłającego, więc tożsamość musi zostać przekazana z żądania
	HTTP (ten sam moment co stemplowanie `sent_by`), nie odczytana ponownie.

	Zwraca `None` dla `Administrator`/`Guest`, brakującego e-maila, albo adresu
	kończącego się na `@example.com` (brak realnej skrzynki) - takiego
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
	"znajdz_pdf": _pdf_umowy_plik_dla_wysylki,
	"nazwa_wysylki": _nazwa_pliku_umowy_wysylki,
	"nazwa_podpisanego": _nazwa_pliku_umowy_podpisanego,
	"podpisujacy": _podpisujacy_umowa,
	"tytul": logika.tytul_dokumentu,
	"awansuj_po_podpisie": True,
	# Pełne zdania, nie budowane z osobnej "etykiety" przez wspólny szablon: polska
	# odmiana (rodzaj gramatyczny rzeczownika, przypadki: "umowę"/"umowy" vs
	# "formularz kredytowy" bez odmiany w tych samych miejscach) sprawia, że
	# jeden dzielony szablon produkuje błędną gramatykę dla jednego z dwóch
	# dokumentów - stąd gotowe, przetestowane literały per dokument.
	"komunikat_brak_rekordu": "Najpierw wygeneruj umowę dla tej szansy sprzedaży.",
	"komunikat_brak_pdf": "Najpierw wygeneruj PDF umowy.",
	"komunikat_w_toku": "Umowa jest już w trakcie podpisywania lub podpisana.",
	"komunikat_brak_email": "Kontakt szansy nie ma adresu e-mail - uzupełnij go w CRM.",
}
"""Konfiguracja dokumentu UMOWA dla wspólnego przepływu wysyłki/statusu/odpytywania
poniżej. `awansuj_po_podpisie=True`: podpisanie umowy przesuwa proces szansy do
etapu „Umowa Podpisana” (`crm.volteo_pipeline`), analogicznie jak przed b47.
`znajdz_pdf`/`nazwa_wysylki`/`nazwa_podpisanego`/`podpisujacy` przyjmują kształt
`(deal, nazwa)`/`(deal_doc, dokument)` wspólny z `KONFIG_KREDYT` (ops#160) - dla
umowy `nazwa`/`dokument` są tu świadomie ignorowane w adapterach, bo umowa
pozostaje 1:1 z szansą."""

KONFIG_KREDYT: dict[str, Any] = {
	"rodzaj": "kredyt",
	"doctype": KREDYT_DOCTYPE,
	"pobierz": _kredyt_po_nazwie_lub_none,
	"znajdz_pdf": _pdf_kredytu_plik,
	"nazwa_wysylki": logika.nazwa_pliku_kredytu,
	"nazwa_podpisanego": logika.nazwa_pliku_kredytu_podpisanego,
	"podpisujacy": _podpisujacy_kredyt,
	"tytul": logika.tytul_dokumentu_kredytu,
	"awansuj_po_podpisie": False,
	# Pełne zdania - patrz komentarz przy `KONFIG_UMOWA` powyżej o tym, czemu nie ma
	# tu wspólnego szablonu. "Formularz kredytowy" jest rodzaju męskiego, stąd
	# "został podpisany" (nie "podpisana", jak dla "Umowa").
	"komunikat_brak_rekordu": "Najpierw wypełnij formularz kredytowy dla tej szansy sprzedaży.",
	"komunikat_brak_pdf": "Najpierw wygeneruj PDF formularza kredytowego.",
	"komunikat_w_toku": "Formularz kredytowy jest już w trakcie podpisywania lub został podpisany.",
	"komunikat_brak_email": "Wnioskodawca formularza kredytowego nie ma adresu e-mail - uzupełnij go w formularzu kredytowym.",
}
"""Konfiguracja dokumentu KREDYT (od b47, kluczowana po nazwie REKORDU od ops#158/#159/#160,
nie po `deal` - jedna szansa może mieć wiele rekordów `Volteo Kredyt`).
`awansuj_po_podpisie=False` jest CELOWE: formularz kredytowy nie ma własnego etapu
w `crm.volteo_pipeline` (żaden z OZE_RODZAJE ani CP nie zyskał etapu „Kredyt”) -
decyzja właściciela, 2026-08-17. Jego podpisanie aktualizuje wyłącznie
`Volteo Kredyt.autenti_status`/`signed_at` TEGO KONKRETNEGO rekordu i podpina
podpisany plik do niego; status szansy pozostaje nietknięty."""

KONFIGURACJE: dict[str, dict[str, Any]] = {"umowa": KONFIG_UMOWA, "kredyt": KONFIG_KREDYT}
"""Rejestr wszystkich dokumentów obsługiwanych przez tę integrację, kluczowany
`rodzaj` - `poll_autenti_status` iteruje po tym słowniku, `_autenti_send_job`
wybiera z niego konfigurację po nazwie przekazanej przez kolejkę."""


@frappe.whitelist()
def autenti_is_enabled() -> dict[str, Any]:
	"""Tani, bezstanowy check widoczności funkcji podpisu w UI. Bez gate'u dostępu do
	szansy - to globalny stan integracji, nie dane konkretnego dokumentu."""
	ustawienia = _autenti_ustawienia()
	return {
		"enabled": logika.czy_wlaczone(ustawienia.get("enabled")),
		"environment": ustawienia.get("environment"),
	}


def _status_dokumentu(nazwa: str, konfig: dict[str, Any]) -> dict[str, Any]:
	"""Zwraca pełny stan podpisu Autenti dokumentu `konfig["rodzaj"]` wskazanego przez
	NAZWĘ REKORDU `nazwa` (`Volteo Umowa`/`Volteo Kredyt`, ops#160) - nie zawsze
	nazwę szansy: dla umowy oba są tożsame (1:1, `autoname: field:deal`); dla
	formularza kredytowego (od ops#158/#159) to nazwa KONKRETNEGO formularza,
	`deal` jest wyprowadzany z załadowanego rekordu (`dokument.deal`). Wspólne
	ciało `autenti_umowa_status`/`autenti_kredyt_status` - obsługuje zarówno
	pierwsze wczytanie zakładki, jak i odpytywanie co 30 s przez frontend - to
	jeden, tani endpoint per dokument, żeby te dwa przypadki nigdy się nie rozjechały.
	"""
	ustawienia = _autenti_ustawienia()
	if not logika.czy_wlaczone(ustawienia.get("enabled")):
		return {"enabled": False}

	dokument = konfig["pobierz"](nazwa)
	# Dla umowy `nazwa == deal` zawsze, więc ten fallback nie zmienia zachowania -
	# dla kredytu chroni wyłącznie okno wyścigu opisane w `_kredyt_po_nazwie_lub_none`
	# (rekord skasowany między bramką endpointu i tym odczytem), gdzie i tak nie ma
	# skąd wziąć prawdziwego `deal`.
	deal = dokument.deal if dokument is not None else nazwa
	deal_doc = frappe.get_doc("CRM Deal", deal)
	# Lista kandydatów SIGNER dla klienta (ops#169): jeden element dla umowy
	# pojedynczej/kredytu, dwa dla umowy podwójnej z drugim Zamawiającym ustawionym
	# (`Volteo Umowa.drugi_zamawiajacy`, ops#168) - patrz `_podpisujacy_umowa`/
	# `_podpisujacy_kredyt`.
	podpisujacy_lista = konfig["podpisujacy"](deal_doc, dokument)
	pierwszy_podpisujacy = podpisujacy_lista[0] if podpisujacy_lista else None

	# Informacyjny podgląd pełnej listy odbiorców (klient(-ci)/wnioskodawca/prezes/
	# handlowiec/archiwum) - ten sam budulec co w `_autenti_send_job`, więc
	# podgląd nigdy nie rozjeżdża się z tym, co faktycznie trafi do procesu
	# dokumentu. Zwracany zawsze, gdy integracja jest włączona - także po
	# wysyłce, wyłącznie informacyjnie.
	proponowani_odbiorcy = logika.zbuduj_odbiorcow(
		podpisujacy_lista,
		_staly_podpisujacy(ustawienia),
		_handlowiec(frappe.session.user),
		_archiwum(ustawienia),
	)

	return {
		"enabled": True,
		"environment": ustawienia.get("environment"),
		"dokument_exists": dokument is not None,
		"pdf_exists": bool(konfig["znajdz_pdf"](deal, nazwa)),
		"autenti_status": dokument.get("autenti_status") if dokument else None,
		"signer_name": dokument.get("signer_name") if dokument else None,
		"signer_email": dokument.get("signer_email") if dokument else None,
		"sent_at": dokument.get("sent_at") if dokument else None,
		"signed_at": dokument.get("signed_at") if dokument else None,
		"error_message": dokument.get("error_message") if dokument else None,
		"signed_pdf_file": dokument.get("signed_pdf_file") if dokument else None,
		"proposed_signer": (
			{"full_name": pierwszy_podpisujacy["full_name"], "email": pierwszy_podpisujacy["email"]}
			if pierwszy_podpisujacy
			else None
		),
		# Lista wszystkich proponowanych podpisujących klientów (ops#169) - dla umowy
		# pojedynczej/kredytu jednoelementowa, tożsama treściowo z `proposed_signer`
		# (zachowany dla zgodności wstecznej z frontendem sprzed tej zmiany). `None`
		# na pierwszej pozycji (brak kontaktu podstawowego) jest pomijany, nie
		# przepuszczany jako `null` w liście.
		"proposed_signers": [
			{"full_name": p["full_name"], "email": p["email"]} for p in podpisujacy_lista if p
		],
		"proposed_recipients": proponowani_odbiorcy,
	}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def autenti_umowa_status(deal: str) -> dict[str, Any]:
	"""Zwraca pełny stan podpisu Autenti dla umowy tej szansy. Obsługuje zarówno
	pierwsze wczytanie zakładki, jak i odpytywanie co 30 s przez frontend - to
	jeden, tani endpoint, żeby te dwa przypadki nigdy się nie rozjechały.

	Umowa pozostaje 1:1 z szansą (ops#160 nie zmienia tego endpointu): `deal`
	jest jednocześnie nazwą rekordu `Volteo Umowa` przekazywaną do `_status_dokumentu`.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	wynik = _status_dokumentu(deal, KONFIG_UMOWA)
	if "dokument_exists" in wynik:
		# Zgodność wdrożeniowa: `dokument_exists` to nowy, ogólny klucz od b47
		# (dzielony z `autenti_kredyt_status`), ale ewentualny nieodświeżony
		# frontend z okna wdrożenia może jeszcze czytać wyłącznie starą nazwę
		# `umowa_exists` - dublujemy pod nią tę samą wartość, żeby taki frontend
		# nie stracił po cichu przycisku wysyłki.
		wynik["umowa_exists"] = wynik["dokument_exists"]
	return wynik


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def autenti_kredyt_status(kredyt: str | None = None) -> dict[str, Any]:
	"""Odpowiednik `autenti_umowa_status` dla JEDNEGO formularza kredytowego, po
	nazwie REKORDU (`kredyt`, ops#160) - od ops#158/#159 jedna szansa może mieć
	wiele formularzy `Volteo Kredyt`, więc `deal` sam w sobie już nie wskazuje
	jednoznacznie "ten jeden" formularz; ten endpoint operuje na dokładnie
	WSKAZANYM rekordzie, tak jak `crm.api.kredyt.volteo_kredyt_get`.

	Celowo BEZ bramki `_sprawdz_rodzaj_oze` - analogicznie do `volteo_kredyt_get`
	(`crm/api/kredyt.py`): zakładka Kredyt jest ukrywana dla linii Czyste Powietrze
	w UI, a sam odczyt statusu podpisu nie ujawnia niczego wrażliwego, więc nie ma
	powodu blokować go twardym błędem - np. przy odświeżeniu widoku tuż po
	przełączeniu „Rodzaju umowy” szansy na Czyste Powietrze.

	`kredyt` puste/`None` (ops#163 follow-up) NIE jest błędem, tylko stanem "rep
	nie ma jeszcze wybranego formularza" - `KredytTab.vue` woła ten endpoint (przez
	`useAutenti`'s `onMounted`) zanim `wybrany` zdąży się rozwiązać do konkretnego
	rekordu, a frontend już go wtedy w ogóle nie wysyła (patrz guard w
	`loadAutentiStatus`, `frontend/src/composables/useAutenti.js`) - JSON.stringify
	usuwa `undefined` z ciała żądania, więc bez wartości domyślnej tutaj Frappe
	widziałby brakujący wymagany parametr i rzucał gołym `TypeError` (417/500, bez
	wpisu w Error Log), zamiast czytelnej odpowiedzi. Krótkie zwarcie do kształtu
	"integracja wyłączona" (bez sprawdzania dostępu do szansy - nie ma jeszcze
	żadnej szansy do sprawdzenia) jest bezpieczne: `useAutenti`'s
	`autentiEnabled`/`showAutentiSendButton` i tak traktują `enabled !== true`
	jako "nie pokazuj UI podpisu", identycznie jak `autenti.value === null`.
	"""
	_sprawdz_role()
	if not kredyt:
		return {"enabled": False}
	kredyt_doc = _kredyt_po_nazwie(kredyt)
	_sprawdz_dostep_do_szansy(kredyt_doc.deal, "read")

	return _status_dokumentu(kredyt, KONFIG_KREDYT)


def _etykieta_dokumentu(konfig: dict[str, Any]) -> str:
	"""Rzeczownik dokumentu do treści śladu aktywności (`tekst_sladu`): "umowę" (biernik,
	rodzaj żeński) dla `KONFIG_UMOWA`, "formularz kredytowy" (rodzaj męski, bez odmiany w
	tych miejscach) dla `KONFIG_KREDYT`. Wyprowadzone z `konfig["doctype"]`, nie z
	`konfig["rodzaj"]`, żeby zawsze podążać za tą samą konfiguracją co reszta wspólnego
	przepływu - patrz komentarz o polskiej odmianie przy `KONFIG_UMOWA`/`KONFIG_KREDYT`."""
	if konfig["doctype"] == UMOWA_DOCTYPE:
		return "umowę"
	return "formularz kredytowy"


def _slad_z_atrybucja(deal: str, tekst: str, wysylajacy: str | None = None) -> None:
	"""Zapisuje ślad aktywności na szansie (`crm.volteo_aktywnosc.zapisz_slad`), NIGDY nie
	rzucając - sam ślad nie może zepsuć wysyłki ani odpytywania Autenti (ta sama zasada,
	co przy `advance_deal_status` w `poll_autenti_status`), więc każdy błąd trafia
	wyłącznie do Error Log.

	`deal` musi być nazwą SZANSY, nigdy nazwą rekordu dokumentu (ops#160: dla
	formularza kredytowego te dwie rzeczy od ops#158/#159 nie są już tym samym
	stringiem) - wołający jest odpowiedzialny za wyprowadzenie właściwego `deal`
	z załadowanego rekordu, patrz `_sprobuj_odzyskac_wyslany_proces`/`_attach_signed_pdf`.

	`wysylajacy`, gdy podane, przypisuje autorstwo komentarza do tego użytkownika przez
	tymczasowy `frappe.set_user` - potrzebne wyłącznie w `_autenti_send_job`, który
	działa w sesji workera (bez sesji wysyłającego, patrz jej docstring), więc bez tego
	komentarz zapisałby się jako Administrator. Poprzedni użytkownik jest zawsze
	przywracany w `finally`, żeby reszta wywołania (przed lub po tym miejscu) nie
	działała przypadkiem pod cudzą tożsamością. Gdy `wysylajacy` jest `None` (wywołania
	z żądania HTTP, gdzie `frappe.session.user` jest już wiarygodny, oraz ze schedulera,
	gdzie autor Administrator jest poprawny), `set_user` w ogóle nie jest wołane.
	"""
	poprzedni_user = frappe.session.user
	try:
		if wysylajacy:
			frappe.set_user(wysylajacy)
		zapisz_slad(deal, tekst)
	except Exception:
		frappe.log_error(
			title="Autenti: zapis śladu aktywności nie powiódł się",
			message=f"Szansa: {deal}\n{frappe.get_traceback()}",
		)
	finally:
		if wysylajacy:
			frappe.set_user(poprzedni_user)


def _wyslij_dokument(nazwa: str, konfig: dict[str, Any]) -> dict[str, Any]:
	"""Wysyła dokument `konfig["rodzaj"]` wskazany przez NAZWĘ REKORDU `nazwa`
	(ops#160) do podpisu przez Autenti (asynchronicznie - kolejkuje
	`_autenti_send_job` i wraca natychmiast). Wspólne ciało
	`autenti_send_umowa`/`autenti_send_kredyt` - bramki i ich kolejność są
	identyczne dla obu dokumentów. Dla umowy `nazwa` jest zawsze nazwą szansy
	(1:1); dla kredytu jest nazwą KONKRETNEGO rekordu `Volteo Kredyt`, `deal`
	jest wyprowadzany z załadowanego rekordu.
	"""
	if not _wlaczone():
		frappe.throw(_("Integracja Autenti jest wyłączona."))

	dokument = konfig["pobierz"](nazwa)
	if dokument is None:
		frappe.throw(_(konfig["komunikat_brak_rekordu"]))

	deal = dokument.deal

	if not konfig["znajdz_pdf"](deal, nazwa):
		frappe.throw(_(konfig["komunikat_brak_pdf"]))

	if not logika.mozna_wyslac(dokument.get("autenti_status")):
		frappe.throw(_(konfig["komunikat_w_toku"]))

	deal_doc = frappe.get_doc("CRM Deal", deal)
	# Lista kandydatów SIGNER dla klienta (ops#169): patrz `_podpisujacy_umowa`/
	# `_podpisujacy_kredyt` - jeden element dla umowy pojedynczej/kredytu, dwa dla
	# umowy podwójnej z drugim Zamawiającym ustawionym.
	podpisujacy_lista = konfig["podpisujacy"](deal_doc, dokument)

	# Bramka e-maila KAŻDEGO podpisującego klienta (ops#169): pierwszy brak
	# używa istniejącego, per-dokumentowego komunikatu (`komunikat_brak_email`,
	# zachowanie sprzed listy niezmienione); każdy kolejny brak (drugi
	# Zamawiający wariantu podwójnego) dostaje komunikat nazwany po TEJ
	# KONKRETNEJ osobie, żeby przedstawiciel wiedział, komu brakuje e-maila,
	# nie tylko że "komuś" brakuje.
	for indeks, dane in enumerate(podpisujacy_lista):
		if dane and dane.get("email"):
			continue
		if indeks == 0:
			frappe.throw(_(konfig["komunikat_brak_email"]))
		nazwa_osoby = (dane or {}).get("full_name") or "Drugi Zamawiający"
		frappe.throw(
			_(f"{nazwa_osoby} (drugi Zamawiający) nie ma adresu e-mail. Uzupełnij go w kontaktach.")
		)

	# Dwaj różni Zamawiający nie mogą dzielić jednego adresu e-mail (ops#169):
	# `zbuduj_odbiorcow` deduplikuje po e-mailu i po cichu zwinęłaby ich do
	# jednego odbiorcy, a drugi Zamawiający nigdy nie dostałby własnego
	# żądania podpisu mimo widniejącej na umowie roli.
	if not logika.emaile_podpisujacych_rozlaczne(podpisujacy_lista):
		frappe.throw(_("Obie osoby podpisujące muszą mieć różne adresy e-mail."))

	pierwszy_podpisujacy = podpisujacy_lista[0]
	drugi_podpisujacy = podpisujacy_lista[1] if len(podpisujacy_lista) > 1 else None

	ustawienia = _autenti_ustawienia()
	if not _staly_podpisujacy(ustawienia) or not _archiwum(ustawienia):
		# Prezes podpisuje KAŻDY dokument (patrz docstring modułu i specyfikacja) -
		# ciche wysłanie bez niego byłoby defektem, nie tylko brakiem funkcji.
		frappe.throw(_("Uzupełnij stałego podpisującego i adres archiwum w Ustawieniach Autenti."))

	# Wysyłający jest przechwytywany TERAZ (żądanie HTTP, `frappe.session.user`
	# wiarygodny) i przekazywany do joba jako jawny argument kolejki - job w
	# tle działa w sesji workera, gdzie `frappe.session.user` nie jest już
	# wysyłającym. To ten sam moment/źródło co stemplowanie `sent_by` niżej,
	# celowo bez ponownego odczytu, żeby uniknąć wyścigu.
	wysylajacy = frappe.session.user

	# `frappe.db.set_value` zamiast `doc.save()` - nie ryzykujemy ścigania się
	# z równoległym zapisem formularza przez przedstawiciela w przeglądarce.
	# Klucz zapisu to `nazwa` (nazwa REKORDU), nigdy `deal` - dla kredytu to
	# jedyny sposób trafić w WŁAŚCIWY formularz, gdy szansa ma ich wiele (ops#160).
	#
	# `sent_at` jest stemplowane już TU, nie dopiero przy sukcesie (ops#143, F2):
	# semantyka pola do tego momentu to "moment zakolejkowania wysyłki", nie
	# "moment faktycznego wysłania": jeśli `_autenti_send_job` zakończy się
	# sukcesem, `sent_at` zostanie NADPISANE prawdziwym momentem wysłania
	# (patrz `_autenti_send_job`). Bez tego wczesnego znacznika poller nie miałby
	# jak rozpoznać, że rekord utknął w „Wysyłanie” dłużej niż
	# `logika.WYSYLANIE_TIMEOUT_MIN` minut (worker mógł zginąć bez wejścia w
	# `except`, np. OOM albo restart kontenera).
	wartosci_zapisu: dict[str, Any] = {
		"autenti_status": "Wysyłanie",
		"signer_name": pierwszy_podpisujacy["full_name"],
		"signer_email": pierwszy_podpisujacy["email"],
		"sent_by": wysylajacy,
		"sent_at": frappe.utils.now(),
		"error_message": None,
	}

	# `signer2_name`/`signer2_email` (ops#169) tylko, gdy doctype JUŻ ma te pola -
	# `has_field` zamiast ślepego zapisu robi tę linię bezpieczną dla kolejności
	# wdrożenia (ops schema przed obrazem, patrz CLAUDE.md): stary schemat bez
	# tych dwóch pól nie dostaje ich w ogóle w słowniku zapisu, zamiast wysypać
	# `frappe.db.set_value` na nieistniejącej kolumnie. Gdy pola istnieją, ale nie
	# ma drugiego podpisującego (umowa pojedyncza, kredyt), oba są jawnie czyszczone
	# do `None` - ponowna wysyłka tego samego dokumentu bez drugiego Zamawiającego
	# (np. po jego usunięciu z umowy) nie może zostawić martwych danych po nim.
	if frappe.get_meta(konfig["doctype"]).has_field("signer2_name"):
		wartosci_zapisu["signer2_name"] = drugi_podpisujacy["full_name"] if drugi_podpisujacy else None
		wartosci_zapisu["signer2_email"] = drugi_podpisujacy["email"] if drugi_podpisujacy else None

	frappe.db.set_value(konfig["doctype"], nazwa, wartosci_zapisu, update_modified=False)
	frappe.db.commit()

	_slad_z_atrybucja(deal, tekst_sladu("autenti_wyslano", dokument=_etykieta_dokumentu(konfig)))

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_job",
		queue="default",
		timeout=300,
		nazwa=nazwa,
		wysylajacy=wysylajacy,
		rodzaj=konfig["rodzaj"],
	)

	return {"autenti_status": "Wysyłanie"}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def autenti_send_umowa(deal: str) -> dict[str, Any]:
	"""Wysyła PDF umowy tej szansy do podpisu przez Autenti (asynchronicznie -
	kolejkuje `_autenti_send_job` i wraca natychmiast).

	Bramka `write`, NIE `read` (ops#33): to akcja zmieniająca stan - wysyła do
	klienta prawnie wiążące żądanie podpisu i przestawia status umowy na
	„Wysyłanie” - więc samo prawo do PODGLĄDU szansy (np. lidera hierarchii
	czytającego szansę podwładnego) nie może wystarczyć do jej wywołania.
	Endpointy statusu (`autenti_umowa_status`/`autenti_kredyt_status`) zostają
	bramkowane `read` - tam odczyt nie zmienia niczego.

	Umowa pozostaje 1:1 z szansą (ops#160 nie zmienia tego endpointu): `deal`
	jest jednocześnie nazwą rekordu `Volteo Umowa` przekazywaną do `_wyslij_dokument`.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	return _wyslij_dokument(deal, KONFIG_UMOWA)


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def autenti_send_kredyt(kredyt: str | None = None) -> dict[str, Any]:
	"""Odpowiednik `autenti_send_umowa` dla JEDNEGO formularza kredytowego, po
	nazwie REKORDU (`kredyt`, ops#160) - patrz docstring `autenti_kredyt_status`
	dla uzasadnienia klucza. DODATKOWO sprawdza `_sprawdz_rodzaj_oze` przed
	delegacją - parytet z `volteo_kredyt_pdf` (`crm/api/kredyt.py`): formularz
	kredytowy dotyczy wyłącznie linii OZE, więc próba wysłania go do podpisu dla
	szansy Czyste Powietrze jest błędem danych szansy, nie stanem roboczym
	formularza.

	Bramka `write`, NIE `read` (ops#33) - patrz docstring `autenti_send_umowa`
	powyżej, ten sam powód: to wysyłka prawnie wiążącego żądania podpisu, nie
	odczyt. Od ops#160 `write` jest sprawdzane na szansie WYPROWADZONEJ z
	załadowanego rekordu (`kredyt_doc.deal`), nie z parametru wejściowego -
	parametr wejściowy to już nazwa rekordu, nie szansy.

	`kredyt: str | None = None` (ops#163 follow-up), tylko żeby brakujący klucz w
	ciele żądania nie rzucał gołym `TypeError` na poziomie dispatcha Frappe zamiast
	docierać tutaj - `_kredyt_po_nazwie` poniżej już wcześniej obsługiwała puste/
	`None` poprawnie (`if not kredyt or not frappe.db.exists(...)`), więc samo
	ciało tej funkcji nie zmienia się: pusty `kredyt` nadal kończy się czytelnym,
	polskim `frappe.throw(_("Formularz kredytowy nie istnieje."), frappe.DoesNotExistError)`.
	W praktyce ten endpoint jest dziś nieosiągalny z pustym `kredyt` z samego UI -
	`confirmSendAutenti` w `useAutenti.js` ma ten sam guard co `loadAutentiStatus` -
	ale to wysyłka prawnie wiążącego żądania podpisu, więc zostaje twardo
	zabezpieczona niezależnie od tego frontendowego gate'u.
	"""
	_sprawdz_role()
	kredyt_doc = _kredyt_po_nazwie(kredyt)
	_sprawdz_dostep_do_szansy(kredyt_doc.deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", kredyt_doc.deal)
	_sprawdz_rodzaj_oze(deal_doc)

	return _wyslij_dokument(kredyt, KONFIG_KREDYT)


def _zdalny_status_bezpiecznie(client: AutentiClient, doc_id: str) -> str | None:
	"""Odpytuje `AutentiClient.get_status(doc_id)` i zwraca sam status, traktując
	odpowiedź 404 (proces nie istnieje już po stronie Autenti) jako `None`, zamiast
	pozwalać jej propagować jako wyjątek. Każdy inny błąd HTTP jest przepuszczany
	dalej -- wołający nie ma jak bezpiecznie odróżnić "proces naprawdę nie
	istnieje" od "chwilowa awaria API", więc tylko 404 jest tu interpretowane
	jako sygnał, a nie usterka.
	"""
	try:
		return client.get_status(doc_id).get("status")
	except requests.HTTPError as exc:
		response = exc.response
		if response is not None and response.status_code == 404:
			return None
		raise


def _sprobuj_odzyskac_wyslany_proces(
	client: AutentiClient,
	deal: str,
	umowa_name: str,
	konfig: dict[str, Any],
	doc_id: str,
	wysylajacy: str | None = None,
) -> bool:
	"""Sprawdza zdalny status procesu dokumentu `doc_id` i stosuje regułę decyzyjną
	`logika.decyzja_ponownej_wysylki`: gdy zdalny proces idzie naprzód (PROCESSING)
	albo już się zakończył (COMPLETED), NIE tworzy nowego procesu -- ustawia lokalnie
	„Wysłana” (+ `sent_at`, `error_message=None`), zapisuje ślad i zwraca `True`,
	zostawiając dokończenie (w tym ewentualne przejście do „Podpisana” i pobranie
	podpisanego PDF-u) kolejnemu przebiegowi `poll_autenti_status`. W przeciwnym
	razie (DRAFT, terminalny status nie-sukces, albo 404) zwraca `False` i NIE
	dotyka żadnego stanu -- decyzję, co zrobić dalej (utworzyć nowy proces, albo
	oznaczyć „Błąd”), podejmuje wołający.

	Współdzielona między F1 (`_autenti_send_job`, ponowna wysyłka rekordu w stanie
	„Błąd” z zachowanym `autenti_document_id`) i F2 (`poll_autenti_status`, rekord
	utknięty w „Wysyłanie” dłużej niż `logika.WYSYLANIE_TIMEOUT_MIN`) -- ten sam
	kontrakt API Autenti, ta sama reguła decyzyjna, jeden punkt prawdy (ops#143).

	`deal` i `umowa_name` (ops#160): dla UMOWY zawsze ten sam string (1:1 z `CRM
	Deal`, `autoname: field:deal`). Dla FORMULARZA KREDYTOWEGO to już DWIE różne
	wartości -- `umowa_name` jest nazwą KONKRETNEGO rekordu `Volteo Kredyt` (klucz
	zapisu DB poniżej, `frappe.db.set_value(konfig["doctype"], umowa_name, ...)`),
	`deal` jest szansą, do której ten rekord należy (klucz śladu aktywności,
	`_slad_z_atrybucja(deal, ...)`) -- nigdy nie mylić tych dwóch ról.

	Może rzucić (błąd sieciowy inny niż 404 z `_zdalny_status_bezpiecznie`) --
	wołający decyduje, jak zareagować na awarię samego sprawdzenia.
	"""
	zdalny_status = _zdalny_status_bezpiecznie(client, doc_id)
	if logika.decyzja_ponownej_wysylki(zdalny_status) != logika.DECYZJA_ODZYSKAJ:
		return False

	frappe.db.set_value(
		konfig["doctype"],
		umowa_name,
		{"autenti_status": "Wysłana", "sent_at": frappe.utils.now(), "error_message": None},
		update_modified=False,
	)
	frappe.db.commit()
	_slad_z_atrybucja(
		deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Wysłana"), wysylajacy
	)
	return True


def _autenti_send_job(nazwa: str, wysylajacy: str | None = None, rodzaj: str = "umowa") -> None:
	"""Zadanie w tle: pobiera zapisany PDF dokumentu `rodzaj` wskazanego przez
	NAZWĘ REKORDU `nazwa` (ops#160; NIGDY świeży render - patrz docstring
	modułu) i wywołuje Autenti, żeby utworzyć proces dokumentu, dodać odbiorców
	(jeden lub dwaj klienci/wnioskodawca + prezes jako SIGNER-zy, handlowiec +
	archiwum jako VIEWER-zy - patrz `logika.zbuduj_odbiorcow`; od ops#169 lista
	klientów ma dwa elementy dla wariantu umowy podwójnej, `Volteo Umowa.drugi_zamawiajacy`
	ustawiony), wgrać plik i wysłać (podpis równoległy: wszyscy odbiorcy są dodani
	przed jednym wywołaniem `send()`). Status w CRM osiąga „Podpisana” dopiero,
	gdy zdalny proces jest COMPLETED, czyli po podpisaniu przez WSZYSTKICH
	sygnatariuszy - to zachowanie samego pollera (`_odpytaj_wyslane` niżej,
	czekające na `SIGNED_CONTENT_FILE`) i NIE ZMIENIA SIĘ w ops#169: COMPLETED
	po stronie Autenti już dziś oznacza podpisanie przez KAŻDEGO SIGNER-a
	dodanego do procesu, niezależnie od tego, ilu ich jest.

	`rodzaj` wybiera konfigurację z `KONFIGURACJE` (`"umowa"`/`"kredyt"`); domyślne
	`"umowa"` jest tu wyłącznie dla zgodności ze starą sygnaturą wywoływaną przez
	`_autenti_send_umowa_job` (patrz jej docstring niżej).

	`nazwa` to nazwa REKORDU (dla umowy tożsama z `deal`, dla kredytu nazwa
	KONKRETNEGO formularza) - `deal`, potrzebny do śladu aktywności i do
	wyprowadzenia `CRM Deal` dla podpisującego, jest wyprowadzany z załadowanego
	rekordu (`dokument.deal`), nigdy z `nazwa` wprost.

	`wysylajacy` to id użytkownika CRM, który wykonał wysyłkę - przekazywane
	jawnie z `_wyslij_dokument` (patrz jej docstring), bo sesja workera nie
	jest sesją wysyłającego. Nie jest whitelisted - wywoływane wyłącznie przez
	`frappe.enqueue`.
	"""
	konfig = KONFIGURACJE[rodzaj]
	dokument = konfig["pobierz"](nazwa)
	if dokument is None:
		# Rekord zniknął między enqueue a wykonaniem joba - nie powinno się zdarzyć
		# (formularz się nie usuwa), ale nie ma gdzie zapisać stanu błędu.
		frappe.log_error(
			title=f"Autenti: brak {konfig['doctype']} w jobie wysyłki",
			message=f"Rekord: {nazwa}",
		)
		return

	deal = dokument.deal

	try:
		client = AutentiClient()

		# F1 (ops#143): ponowna wysyłka rekordu z zachowanym `autenti_document_id`
		# NIE tworzy ślepo drugi proces dokumentu: najpierw sprawdza, czy poprzedni
		# proces da się odzyskać (patrz docstring `_sprobuj_odzyskac_wyslany_proces`).
		# Umyślnie PRZED każdym innym przygotowaniem (PDF, kontakt, ustawienia):
		# odzyskanie nie potrzebuje żadnego z nich, więc sprawdzamy to najpierw i
		# najtaniej.
		#
		# Bramka jest WYŁĄCZNIE na `istniejacy_doc_id`, celowo BEZ sprawdzania
		# `dokument.get("autenti_status") == "Błąd"`: `_wyslij_dokument` ustawia
		# status na „Wysyłanie” i commituje SYNCHRONICZNIE, PRZED `frappe.enqueue`
		# (patrz jej docstring) -- ten job zawsze widzi w bazie „Wysyłanie”, nigdy
		# „Błąd”, więc warunek na status byłby tu zawsze fałszywy i cała gałąź
		# odzyskania byłaby martwa (znaleziono w QA ops#143, druga runda).
		# `autenti_document_id` sam w sobie jest wystarczającym sygnałem: pojawia
		# się w rekordzie dopiero po poprzedniej próbie (pierwsza wysyłka go nie
		# ma), a `logika.mozna_wyslac` w `_wyslij_dokument` już przepuściło tylko
		# stany, dla których ponowna wysyłka jest w ogóle legalna (Błąd, Odrzucona,
		# Wygasła, Wycofana, brak wysyłki) -- dla terminalnych nie-sukcesów
		# `get_status` zwróci REJECTED/EXPIRED/WITHDRAWN i `decyzja_ponownej_wysylki`
		# i tak da nowy proces, dla PROCESSING/COMPLETED odzyska istniejący.
		istniejacy_doc_id = dokument.get("autenti_document_id")
		if istniejacy_doc_id:
			try:
				odzyskano = _sprobuj_odzyskac_wyslany_proces(
					client, deal, nazwa, konfig, istniejacy_doc_id, wysylajacy
				)
			except Exception:
				frappe.log_error(
					title=f"Autenti: sprawdzenie poprzedniego procesu {konfig['doctype']} nie powiodło się",
					message=f"Szansa: {deal}\nRekord: {nazwa}\nProces dokumentu: {istniejacy_doc_id}\n{frappe.get_traceback()}",
				)
				frappe.db.set_value(
					konfig["doctype"],
					nazwa,
					{
						"autenti_status": "Błąd",
						"error_message": "Nie udało się sprawdzić stanu poprzedniej wysyłki w Autenti. Spróbuj ponownie.",
					},
					update_modified=False,
				)
				frappe.db.commit()
				_slad_z_atrybucja(
					deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd"), wysylajacy
				)
				return
			if odzyskano:
				return
			# decyzja == nowy_proces: stary proces zostaje w Autenti nieszkodliwy
			# (DRAFT albo terminalny nie-sukces), tworzymy nowy od zera poniżej.

		plik = konfig["znajdz_pdf"](deal, nazwa)
		if plik is None:
			frappe.db.set_value(
				konfig["doctype"],
				nazwa,
				{"autenti_status": "Błąd", "error_message": "PDF zniknął przed wysyłką."},
				update_modified=False,
			)
			frappe.db.commit()
			_slad_z_atrybucja(
				deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd"), wysylajacy
			)
			return
		pdf_bytes = plik.get_content()

		deal_doc = frappe.get_doc("CRM Deal", deal)
		# Lista kandydatów SIGNER dla klienta (ops#169) - patrz `_podpisujacy_umowa`/
		# `_podpisujacy_kredyt`. Defensywne powtórzenie tylko na PIERWSZYM podpisującym,
		# tak jak przed tą zmianą: `_wyslij_dokument` już zweryfikowało e-maile
		# WSZYSTKICH kandydatów (włącznie z rozłącznością) przed zakolejkowaniem tego
		# joba, więc ten check jest wyłącznie na wypadek, gdyby stan zmienił się w
		# oknie między akceptacją żądania a wykonaniem joba.
		podpisujacy_lista = konfig["podpisujacy"](deal_doc, dokument)
		pierwszy_podpisujacy = podpisujacy_lista[0] if podpisujacy_lista else None
		if not pierwszy_podpisujacy or not pierwszy_podpisujacy["email"]:
			frappe.db.set_value(
				konfig["doctype"],
				nazwa,
				{"autenti_status": "Błąd", "error_message": konfig["komunikat_brak_email"]},
				update_modified=False,
			)
			frappe.db.commit()
			_slad_z_atrybucja(
				deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd"), wysylajacy
			)
			return

		ustawienia = _autenti_ustawienia()

		# Defensywne powtórzenie bramki z `_wyslij_dokument`: ustawienia mogły się
		# zmienić w oknie między akceptacją żądania a wykonaniem joba w tle. Job nie
		# może rzucić do przeglądarki - jedyna droga to zapisany stan błędu.
		prezes = _staly_podpisujacy(ustawienia)
		archiwum = _archiwum(ustawienia)
		if not prezes or not archiwum:
			frappe.db.set_value(
				konfig["doctype"],
				nazwa,
				{
					"autenti_status": "Błąd",
					"error_message": "Brak stałego podpisującego lub adresu archiwum w Ustawieniach Autenti.",
				},
				update_modified=False,
			)
			frappe.db.commit()
			_slad_z_atrybucja(
				deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd"), wysylajacy
			)
			return

		handlowiec = _handlowiec(wysylajacy)
		odbiorcy = logika.zbuduj_odbiorcow(podpisujacy_lista, prezes, handlowiec, archiwum)

		signature_type = ustawienia.get("default_signature_type") or "BASIC"
		tytul = konfig["tytul"](pierwszy_podpisujacy["full_name"])

		doc_id = client.create_document_process(title=tytul)

		# F1 pkt 1 (ops#143): `autenti_document_id` jest zapisany OSOBNYM zapisem
		# zaraz po utworzeniu procesu, PRZED add_party/upload_file/send. Read
		# timeout (`client.py` READ_TIMEOUT=30 s) na którymkolwiek z tych trzech
		# wywołań, mimo że po stronie Autenti proces już powstał, ląduje w
		# `except` poniżej -- a ten NIE nadpisuje `autenti_document_id` (dict w
		# excepcie go nie zawiera), więc zostaje zachowany dla przyszłej
		# ponownej wysyłki (patrz `_sprobuj_odzyskac_wyslany_proces` powyżej).
		# Bez tego wczesnego zapisu poprzednia wersja tego kodu traciła doc_id
		# przy każdym takim timeoucie, więc poller nigdy nie widział procesu, a
		# „Wyślij ponownie” tworzyło DRUGI proces podpisu tej samej umowy.
		frappe.db.set_value(konfig["doctype"], nazwa, "autenti_document_id", doc_id, update_modified=False)
		frappe.db.commit()

		for odbiorca in odbiorcy:
			# first_name/last_name pochodzą osobno z helpera kontaktu/wnioskodawcy/
			# ustawień/User, nigdy z rozbicia pełnego imienia i nazwiska po spacji
			# (zawodzi dla nazwisk wieloczłonowych).
			party_kwargs: dict[str, Any] = {
				"first_name": odbiorca["first_name"] or odbiorca["full_name"],
				"last_name": odbiorca["last_name"],
				"email": odbiorca["email"],
				"role": odbiorca["role"],
			}
			if odbiorca["role"] == "SIGNER":
				party_kwargs["signature_type"] = signature_type
			client.add_party(doc_id, **party_kwargs)
		client.upload_file(doc_id, filename=konfig["nazwa_wysylki"](deal, nazwa), pdf_bytes=pdf_bytes)
		client.send(doc_id)

		frappe.db.set_value(
			konfig["doctype"],
			nazwa,
			{
				"autenti_status": "Wysłana",
				"sent_at": frappe.utils.now(),
				"error_message": None,
			},
			update_modified=False,
		)
		frappe.db.commit()
		_slad_z_atrybucja(
			deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Wysłana"), wysylajacy
		)
	except Exception as exc:
		frappe.log_error(
			title=f"Autenti: wysyłka {konfig['doctype']} nie powiodła się",
			message=f"Szansa: {deal}\nRekord: {nazwa}\n{frappe.get_traceback()}",
		)
		# F1 pkt 2 (ops#143): `autenti_document_id` NIE jest w tym słowniku --
		# celowo pozostaje nienaruszony, gdyby już był zapisany powyżej.
		# F15 (ops#143): polski, czysty komunikat dla handlowca (`komunikat_bledu_wysylki`)
		# zamiast surowego, angielskiego `str(exc)` -- pełny traceback zostaje w
		# Error Log przez `frappe.log_error` powyżej.
		frappe.db.set_value(
			konfig["doctype"],
			nazwa,
			{"autenti_status": "Błąd", "error_message": logika.komunikat_bledu_wysylki(exc)},
			update_modified=False,
		)
		frappe.db.commit()
		_slad_z_atrybucja(
			deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd"), wysylajacy
		)


def _autenti_send_umowa_job(deal: str, wysylajacy: str | None = None) -> None:
	"""Cienki shim delegujący do `_autenti_send_job(deal, wysylajacy, rodzaj="umowa")`.

	Zachowany pod STARĄ, kropkowaną ścieżką
	(`crm.integrations.autenti.api._autenti_send_umowa_job`) - `frappe.enqueue`
	serializuje dotted path, nie referencję funkcji w pamięci, więc jakikolwiek job
	zakolejkowany pod tą nazwą TUŻ PRZED wdrożeniem tej zmiany (a wykonany PO
	restarcie workerów kolejki) musi nadal trafić do działającej funkcji, zamiast
	dead-letterować na nieistniejącej już nazwie. Wywołanie pozycyjne poniżej działa
	bez zmian po ops#160 (parametr `_autenti_send_job` nazywa się teraz `nazwa`, nie
	`deal`, ale dla umowy to zawsze ten sam string).
	"""
	_autenti_send_job(deal, wysylajacy, rodzaj="umowa")


def _attach_signed_pdf(deal: str, umowa_name: str, doc_id: str, konfig: dict[str, Any]) -> None:
	"""Pobiera podpisany PDF z Autenti i podpina go jako prywatny `File` do rekordu
	dokumentu `konfig["doctype"]` (`umowa_name`), zapisując jego url w
	`signed_pdf_file`.

	`deal` i `umowa_name` (ops#160): dla UMOWY zawsze ten sam string (1:1 z `CRM
	Deal`, `autoname: field:deal`) - trzymane osobno dla czytelności, na wzór
	odpowiednika dla oferty. Dla FORMULARZA KREDYTOWEGO `umowa_name` jest nazwą
	KONKRETNEGO rekordu `Volteo Kredyt`, `deal` jest szansą, do której ten rekord
	należy - patrz `_sprobuj_odzyskac_wyslany_proces` dla tego samego rozróżnienia.

	Cały błąd jest łapany i logowany, nigdy nie propaguje - utrata samego załącznika
	nie może cofnąć już zapisanego przejścia statusu na „Podpisana”.

	WZNAWIALNA i IDEMPOTENTNA (ops#143, F3 pkt 1): `poll_autenti_status` woła tę
	funkcję ponownie dla każdego rekordu „Podpisana” z pustym `signed_pdf_file`,
	dopóki się nie powiedzie. Zanim pobierze cokolwiek z Autenti, sprawdza,
	czy `File` o docelowej nazwie już wisi na tym dokumencie (poprzednia próba
	zdążyła go wgrać, ale awarowała PRZED zapisem `signed_pdf_file`, np. na
	samym `frappe.db.commit()`), wtedy tylko uzupełnia pole, nie pobiera i nie
	wgrywa pliku po raz drugi.
	"""
	try:
		istniejacy_url = frappe.db.get_value(
			"File",
			{
				"attached_to_doctype": konfig["doctype"],
				"attached_to_name": umowa_name,
				"file_name": konfig["nazwa_podpisanego"](deal, umowa_name),
			},
			"file_url",
		)
		if istniejacy_url:
			frappe.db.set_value(konfig["doctype"], umowa_name, "signed_pdf_file", istniejacy_url, update_modified=False)
			frappe.db.commit()
			return

		client = AutentiClient()
		file_id = client.get_signed_file_id(doc_id)
		if not file_id:
			# F3 pkt 3 (ops#143): logujemy dopiero, gdy zaległość faktycznie trwa
			# (`ZALEGLY_PODPISANY_PLIK_LOG_MIN`), nie przy KAŻDYM przebiegu pollera
			# (co 10 minut), inaczej zalałoby to Error Log ~144 wpisami/dobę na
			# jeden dokument, zanim Autenti w ogóle wystawi plik.
			signed_at_raw = frappe.db.get_value(konfig["doctype"], umowa_name, "signed_at")
			signed_at = frappe.utils.get_datetime(signed_at_raw) if signed_at_raw else None
			if logika.czy_logowac_brak_podpisanego_pliku(signed_at, frappe.utils.now_datetime()):
				frappe.log_error(
					title="Autenti: brak podpisanego pliku",
					message=f"{konfig['doctype']}: {umowa_name}\nProces dokumentu: {doc_id}\nBrak jeszcze pliku podpisanego.",
				)
			return

		content = client.download_file_content(doc_id, file_id)

		plik = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": konfig["nazwa_podpisanego"](deal, umowa_name),
				"attached_to_doctype": konfig["doctype"],
				"attached_to_name": umowa_name,
				"is_private": 1,
				"content": content,
			}
		)
		plik.insert(ignore_permissions=True)

		frappe.db.set_value(konfig["doctype"], umowa_name, "signed_pdf_file", plik.file_url, update_modified=False)
		frappe.db.commit()
		_slad_z_atrybucja(deal, tekst_sladu("autenti_pdf", dokument=_etykieta_dokumentu(konfig)))
	except Exception:
		frappe.log_error(
			title="Autenti: pobranie podpisanego pliku nie powiodło się",
			message=f"{konfig['doctype']}: {umowa_name}\nProces dokumentu: {doc_id}\n{frappe.get_traceback()}",
		)
		frappe.db.commit()


def _odpytaj_wyslane(client: AutentiClient, konfig: dict[str, Any]) -> None:
	"""Skanuje wszystkie dokumenty `konfig["doctype"]` w lokalnym stanie „Wysłana”,
	sprawdza ich zdalny status przez API Autenti i aktualizuje rekord. Wydzielone z
	`poll_autenti_status`, żeby ten skan (istniejący od b45) i dwa nowe skany
	dodane w ops#143 (`_odzyskaj_utkniete_wysylanie`, `_ponow_pobranie_podpisanych_plikow`)
	miały niezależne bloki try/except pod wspólną pętlą po `KONFIGURACJE`, patrz
	docstring `poll_autenti_status`.

	Ops#160: każdy wiersz jest zawsze identyfikowany po `wiersz.name` (nazwa
	REKORDU - jedyny klucz bezpieczny dla `frappe.db.set_value`/`frappe.get_all`,
	skoro jedna szansa może mieć wiele rekordów `Volteo Kredyt`), NIGDY po
	`wiersz.deal`. `wiersz.deal` jest pobierany osobno WYŁĄCZNIE tam, gdzie
	rzeczywiście chodzi o szansę (ślad aktywności, awans statusu procesu).
	"""
	wiersze = frappe.get_all(
		konfig["doctype"],
		filters={"autenti_status": "Wysłana", "autenti_document_id": ["is", "set"]},
		fields=["name", "deal", "autenti_document_id", "autenti_status", "error_message"],
	)
	if not wiersze:
		return

	for wiersz in wiersze:
		try:
			zdalny_status = _zdalny_status_bezpiecznie(client, wiersz.autenti_document_id)
			nowy_status = logika.STATUS_MAP.get(zdalny_status) if zdalny_status else None
			if not nowy_status:
				if zdalny_status in logika.PENDING_REMOTE_STATUSES:
					# Nieterminalny stan zdalny: dokument zasadnie czeka na podpis
					# dni, więc NIGDY nie logujemy tego jako błąd (zalałoby Error Log).
					continue
				# F9 (ops#143): nierozpoznany zdalny status (np. 404 -> None, albo
				# literał spoza STATUS_MAP/PENDING_REMOTE_STATUSES) jest logowany
				# RAZ na dokument, nie przy każdym przebiegu co 10 minut:
				# deduplikacja przez treść `error_message` (patrz
				# `logika.czy_logowac_nierozpoznany_status`). Status lokalny
				# pozostaje bez zmiany: NIE dodajemy zgadywanych statusów do
				# STATUS_MAP tylko dlatego, że jeden przebieg je zobaczył.
				if logika.czy_logowac_nierozpoznany_status(wiersz.error_message, str(zdalny_status)):
					frappe.log_error(
						title="Autenti: nierozpoznany status",
						message=f"{konfig['doctype']}: {wiersz.name}\nProces dokumentu: {wiersz.autenti_document_id}\n"
						f"Nierozpoznany zdalny status: {zdalny_status}",
					)
					frappe.db.set_value(
						konfig["doctype"],
						wiersz.name,
						"error_message",
						logika.komunikat_nierozpoznanego_statusu(str(zdalny_status)),
						update_modified=False,
					)
					frappe.db.commit()
				continue

			stary_status = wiersz.autenti_status
			aktualizacja: dict[str, Any] = {"autenti_status": nowy_status}
			if nowy_status == "Podpisana":
				aktualizacja["signed_at"] = frappe.utils.now()
			frappe.db.set_value(konfig["doctype"], wiersz.name, aktualizacja, update_modified=False)
			frappe.db.commit()

			if nowy_status != stary_status:
				# Ślad tylko przy FAKTYCZNEJ zmianie stanu: `stary_status` jest tu
				# zawsze "Wysłana" (patrz filtr `frappe.get_all` powyżej) i
				# `logika.STATUS_MAP` nigdy nie mapuje na "Wysłana", więc ten
				# warunek jest dziś zawsze prawdziwy; trzymany jawnie jako
				# bezpiecznik na wypadek przyszłej zmiany mapowania.
				_slad_z_atrybucja(
					wiersz.deal,
					tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status=nowy_status),
				)

			if nowy_status == "Podpisana":
				if konfig["awansuj_po_podpisie"]:
					# F4 (ops#143): własny try/except wokół awansu procesu szansy i
					# jego commita, ODDZIELNY od pobrania pliku poniżej. Wcześniej
					# oba żyły w tym samym `try` tej pętli, a wyjątek na
					# `advance_deal_status`/`frappe.db.commit()` przeskakiwał całe
					# `_attach_signed_pdf` mimo komentarza obiecującego, że awaria
					# automatyzacji nie zablokuje pobrania pliku. Automatyzacja jest
					# opcjonalna w panelu admina i przejście musi iść do przodu w
					# JEJ procesie; nigdy nie może cofnąć już zapisanego statusu
					# podpisu ani zablokować pobrania podpisanego pliku. Ten worker
					# nie ma sesji wołającego (scheduler), więc `doc.save()`
					# wewnątrz `advance_deal_status` zapisuje jako wołający zadania
					# w tle. Formularz kredytowy (`konfig["awansuj_po_podpisie"] is
					# False`) celowo NIGDY tu nie trafia: nie ma własnego etapu w
					# `crm.volteo_pipeline` (decyzja właściciela, 2026-08-17).
					try:
						advance_deal_status(wiersz.deal, "Umowa Podpisana", "umowa_podpisana")
						frappe.db.commit()
					except Exception:
						frappe.log_error(
							title="Autenti: awans statusu szansy po podpisaniu nie powiódł się",
							message=f"Szansa: {wiersz.deal}\n{frappe.get_traceback()}",
						)
						frappe.db.commit()
				_attach_signed_pdf(wiersz.deal, wiersz.name, wiersz.autenti_document_id, konfig)
		except Exception:
			frappe.log_error(
				title="Autenti: odpytanie statusu nie powiodło się",
				message=f"{konfig['doctype']}: {wiersz.name}\n{frappe.get_traceback()}",
			)
			frappe.db.commit()


def _odzyskaj_utkniete_wysylanie(client: AutentiClient, konfig: dict[str, Any]) -> None:
	"""F2 (ops#143): skanuje dokumenty `konfig["doctype"]` utknięte w lokalnym
	statusie „Wysyłanie” dłużej niż `logika.WYSYLANIE_TIMEOUT_MIN` minut: worker
	mógł zginąć (OOM, restart kontenera) bez wejścia w `except`, więc taki rekord
	inaczej blokowałby ponowną wysyłkę i regenerację PDF-u na zawsze
	(`logika.SEND_BLOCKED_STATUSES`).

	Bez `autenti_document_id`: żaden proces nie zdążył powstać po stronie Autenti,
	od razu „Błąd”. Z `autenti_document_id`: ta sama reguła odzyskiwania co F1
	(`_sprobuj_odzyskac_wyslany_proces`): PROCESSING/COMPLETED odzyskuje rekord
	do „Wysłana” i zostawia dokończenie kolejnemu przebiegowi pollera; w
	przeciwnym razie „Błąd” (poller sam nie tworzy nowych procesów, brakuje mu
	PDF-u/odbiorców/ustawień, które ma tylko `_autenti_send_job`, więc rep musi
	kliknąć „Wyślij ponownie”, co wtedy trafi na ten sam stary `doc_id` i, widząc
	DRAFT/terminalny status, utworzy nowy proces).

	Ops#160: identyfikacja rekordu (filtry, `frappe.db.set_value`) idzie zawsze po
	`wiersz.name`, nigdy po `wiersz.deal` - patrz docstring `_odpytaj_wyslane`.
	"""
	wiersze = frappe.get_all(
		konfig["doctype"],
		filters={"autenti_status": "Wysyłanie"},
		fields=["name", "deal", "autenti_document_id", "sent_at"],
	)
	if not wiersze:
		return

	teraz = frappe.utils.now_datetime()
	for wiersz in wiersze:
		sent_at = frappe.utils.get_datetime(wiersz.sent_at) if wiersz.sent_at else None
		if not logika.czy_wysylanie_przekroczylo_timeout(sent_at, teraz):
			continue

		try:
			if not wiersz.autenti_document_id:
				frappe.db.set_value(
					konfig["doctype"],
					wiersz.name,
					{"autenti_status": "Błąd", "error_message": logika.KOMUNIKAT_TIMEOUT_WYSYLANIA_BEZ_PROCESU},
					update_modified=False,
				)
				frappe.db.commit()
				_slad_z_atrybucja(
					wiersz.deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd")
				)
				continue

			if _sprobuj_odzyskac_wyslany_proces(client, wiersz.deal, wiersz.name, konfig, wiersz.autenti_document_id):
				continue

			frappe.db.set_value(
				konfig["doctype"],
				wiersz.name,
				{"autenti_status": "Błąd", "error_message": logika.KOMUNIKAT_TIMEOUT_WYSYLANIA_Z_PROCESEM},
				update_modified=False,
			)
			frappe.db.commit()
			_slad_z_atrybucja(
				wiersz.deal, tekst_sladu("autenti_status", dokument=_etykieta_dokumentu(konfig), status="Błąd")
			)
		except Exception:
			frappe.log_error(
				title="Autenti: odzyskanie utkniętej wysyłki nie powiodło się",
				message=f"{konfig['doctype']}: {wiersz.name}\n{frappe.get_traceback()}",
			)
			frappe.db.commit()


def _ponow_pobranie_podpisanych_plikow(konfig: dict[str, Any]) -> None:
	"""F3 pkt 1 (ops#143): ponawia `_attach_signed_pdf` dla dokumentów `konfig["doctype"]`
	już w statusie „Podpisana”, którym mimo to brakuje `signed_pdf_file`:
	pierwsza próba w `_odpytaj_wyslane` mogła się nie udać (np. plik jeszcze nie
	istnieje po stronie Autenti tuż po COMPLETED, albo przejściowy błąd sieci).
	`_attach_signed_pdf` jest wznawialna i idempotentna (patrz jej docstring) i
	sama łapie każdy wyjątek, więc ta funkcja nie potrzebuje własnego try/except
	wokół samego wywołania, tylko wokół zapytania `frappe.get_all`.

	Ops#160: `wiersz.name` (nazwa rekordu) i `wiersz.deal` (szansa) są przekazywane
	do `_attach_signed_pdf` osobno, w tej kolejności - patrz jej docstring.
	"""
	wiersze = frappe.get_all(
		konfig["doctype"],
		filters={
			"autenti_status": "Podpisana",
			"autenti_document_id": ["is", "set"],
			"signed_pdf_file": ["is", "not set"],
		},
		fields=["name", "deal", "autenti_document_id"],
	)
	for wiersz in wiersze:
		_attach_signed_pdf(wiersz.deal, wiersz.name, wiersz.autenti_document_id, konfig)


def poll_autenti_status() -> None:
	"""Zadanie harmonogramu (co 10 min, patrz `hooks.py`): dla KAŻDEGO skonfigurowanego
	typu dokumentu w `KONFIGURACJE` -- sprawdza status wszystkich dokumentów w stanie
	„Wysłana” przez API Autenti (`_odpytaj_wyslane`), odzyskuje albo oznacza jako
	błąd rekordy utknięte w „Wysyłanie” (`_odzyskaj_utkniete_wysylanie`, ops#143 F2),
	i ponawia pobranie podpisanego pliku dla „Podpisana” bez `signed_pdf_file`
	(`_ponow_pobranie_podpisanych_plikow`, ops#143 F3).

	Ops#160: dla `Volteo Kredyt` każdy z tych trzech skanów operuje na REKORDACH,
	nie na szansach -- jedna szansa z dwoma wysłanymi formularzami generuje DWA
	niezależne przebiegi (dwa wiersze `frappe.get_all`), z własnym statusem i
	własnym pobraniem podpisanego pliku dla każdego; identyfikacja rekordu w
	każdym skanie idzie zawsze po `row.name`, nigdy po `row.deal` (patrz docstring
	`_odpytaj_wyslane`).

	Konstrukcja `AutentiClient()` jest owinięta WŁASNYM try/except (ops#143, F19):
	wyjątek w jej `__init__` (np. brak sekretu po migracji ustawień) nie może
	wywalić całego joba bez wpisu w Error Log.

	Każdy z trzech skanów, dla KAŻDEGO doctype'u, jest owinięty WŁASNYM
	try/except: schemat `Volteo Kredyt` (kolumny `autenti_status`/`autenti_document_id`)
	może na danej instalacji nie być jeszcze wdrożony (np. okno między deployem
	obrazu z tym kodem a odpaleniem skryptu ops dodającego pola), brakująca
	kolumna przy jednym skanie/doctype nie może zablokować pozostałych, już
	działających.
	"""
	if not _wlaczone():
		return

	try:
		client = AutentiClient()
	except Exception:
		frappe.log_error(title="Autenti: konfiguracja klienta", message=frappe.get_traceback())
		return

	for konfig in KONFIGURACJE.values():
		try:
			_odpytaj_wyslane(client, konfig)
		except Exception:
			frappe.log_error(
				title=f"Autenti: odpytanie statusu {konfig['doctype']} nie powiodło się",
				message=frappe.get_traceback(),
			)

		try:
			_odzyskaj_utkniete_wysylanie(client, konfig)
		except Exception:
			frappe.log_error(
				title=f"Autenti: odzyskanie utkniętej wysyłki {konfig['doctype']} nie powiodło się",
				message=frappe.get_traceback(),
			)

		try:
			_ponow_pobranie_podpisanych_plikow(konfig)
		except Exception:
			frappe.log_error(
				title=f"Autenti: ponowienie pobrania podpisanego pliku {konfig['doctype']} nie powiodło się",
				message=frappe.get_traceback(),
			)
