"""Whitelisted API formularza „Informacje do umowy” (doctype `Volteo Umowa`).

`Volteo Umowa` jest 1:1 z `CRM Deal` (`autoname: "field:deal"` — nazwa dokumentu
to nazwa szansy). Przeglądarka nigdy nie ustala kwoty kredytu ani wymogu zgody
przeciwpożarowej (PPOŻ) — obie wartości liczy wyłącznie serwer, przez wspólny,
bezstanowy rdzeń `crm.volteo_umowa`, i nadpisuje przy każdym zapisie niezależnie
od tego, co przyszło od klienta. Formularz jest wypełniany stopniowo przez
przedstawiciela, więc niekompletny zapis to poprawny stan roboczy (draft-save),
a nie błąd — brakujące pola są zwracane w wyniku, nigdy nie rzucamy wyjątku
z powodu samej niekompletności.
"""

from decimal import Decimal
from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate

from crm.api.czyste_powietrze import KALKULATOR_ROLE
from crm.api.pipeline import advance_deal_status
from crm.integrations.autenti import logika as autenti_logika
from crm.permissions.file_nazwy_systemowe import plik_systemowy
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_naming import code_for
from crm.volteo_umowa import (
	brakujace_dane_klienta,
	brakujace_pola,
	czy_propagowac_zgody,
	czy_umowa_podwojna,
	kod_szablonu,
	kontakty_do_zgod,
	kwota_kredytu,
	miejsce_i_pokrycie,
	ppoz_wymagane,
)
from crm.volteo_umowa_pdf import POLA_KOMPONENTU, zbuduj_kontekst
from crm.volteo_umowa_render import SZABLONY, sciezka_wbudowanego_szablonu, zloz_umowe

DOCTYPE = "Volteo Umowa"

_DEAL_POLA_PREFILL = [
	"name",
	"deal_value",
	"custom_netto",
	"custom_pv_power_kwp",
	"custom_panele",
	"custom_panel",
	"custom_falownik",
	"custom_bateria",
	"custom_pojemnosc_kwh",
	"custom_konstrukcja",
	"custom_kabel_m",
	"custom_wplata_wlasna",
	"custom_install_address",
	"custom_install_city",
	"custom_install_postal_code",
	"custom_voivodeship",
	"custom_rodzaj_umowy",
	"custom_istniejaca_pv",
	"custom_istniejaca_pv_moc_kwp",
	"custom_ppoz",
]
"""Pola `CRM Deal` kopiowane bez zmian do bloku `prefill`."""

_KONTAKT_POLA = [
	"first_name",
	"last_name",
	"custom_pesel",
	"custom_ulica",
	"custom_nr_domu",
	"custom_nr_mieszkania",
	"custom_kod_pocztowy",
	"custom_miasto",
	"custom_wojewodztwo",
]
"""Pola podstawowego `Contact` szansy kopiowane do `prefill`; adres domowy kontaktu."""

_PREFILL_MAPOWANIE: dict[str, str] = {
	"custom_ulica": "adres_zam_ulica",
	"custom_nr_domu": "adres_zam_nr_domu",
	"custom_nr_mieszkania": "adres_zam_nr_mieszkania",
	"custom_kod_pocztowy": "adres_zam_kod",
	"custom_miasto": "adres_zam_miasto",
	"custom_install_address": "adres_montaz_ulica",
	"custom_install_postal_code": "adres_montaz_kod",
	"custom_install_city": "adres_montaz_miasto",
	"custom_kabel_m": "dodatkowy_kabel_m",
	"custom_wplata_wlasna": "wklad_wlasny_pln",
	"custom_istniejaca_pv": "istniejaca_pv",
	"custom_istniejaca_pv_moc_kwp": "istniejaca_pv_moc_kwp",
}
"""Mapowanie pole źródłowe (Deal/Contact) → pole `Volteo Umowa`, dopisywane do `prefill`.

Frontend hydratuje formularz kluczami `Volteo Umowa` (`form[fn] = valueOr(record[fn],
prefill[fn])`), nie surowymi nazwami pól CRM Deal/Contact — bez tego mapowania prefill
jest cichym no-opem: każdy lookup zwraca `undefined`, nic nie się wywala, pole po prostu
zostaje puste. Surowe klucze źródłowe (`_DEAL_POLA_PREFILL`, `_KONTAKT_POLA`) zostają
w `prefill` OBOK wpisów zmapowanych — przydatne do wyświetlania i późniejszego kroku PDF.

Celowo BEZ mapowania: `adres_montaz_nr_domu` i `adres_montaz_nr_mieszkania`. Deal
przechowuje adres montażu jako jedno pole tekstowe (`custom_install_address`) bez
wydzielonego numeru domu/mieszkania — NIE wyciągać ich regexem z tego stringa. Te dwa
pola formularza zostają puste, do ręcznego wypełnienia przez przedstawiciela.

`custom_istniejaca_pv` i `custom_istniejaca_pv_moc_kwp` (ops#194) prefillują
odpowiedź kalkulatora OZE o istniejącej instalacji klienta: przedstawiciel może
je na formularzu umowy dowolnie poprawić, prefill jest tylko punktem startowym.
`custom_ppoz` jest CELOWO bez wpisu w tym słowniku: to nie jest pole formularza
umowy, tylko sygnał wejściowy dla `ppoz_wymagane()` po stronie serwera (patrz
`_wyliczenia`/`volteo_umowa_save` niżej) i dla `ppozWymagane()` po stronie
frontendu, który czyta je wprost z `prefill.custom_ppoz` (surowy klucz Deal,
zostaje w `prefill` bez mapowania, jak każdy wpis `_DEAL_POLA_PREFILL`).
"""

_DANE_POLA_DOZWOLONE = [
	"adres_zam_jak_montaz",
	"typ_budynku",
	"powierzchnia_prog",
	"powierzchnia_m2",
	"finansowanie",
	"wklad_wlasny_pln",
	"internet",
	"instalacja_odgromowa",
	"moc_przylaczeniowa_kw",
	"liczba_faz",
	"osd",
	"przekop_gruntowy",
	"przekop_mb",
	"istniejaca_pv",
	"istniejaca_pv_moc_inwertera_kw",
	"istniejaca_pv_moc_kwp",
	"istniejaca_pv_producent_inwertera",
	"adres_zam_ulica",
	"adres_zam_nr_domu",
	"adres_zam_nr_mieszkania",
	"adres_zam_kod",
	"adres_zam_miasto",
	"adres_montaz_ulica",
	"adres_montaz_nr_domu",
	"adres_montaz_nr_mieszkania",
	"adres_montaz_kod",
	"adres_montaz_miasto",
	"dodatkowy_kabel",
	"dodatkowy_kabel_m",
	"zgoda_kontakt_telefoniczny",
	"zgoda_dzialania_promocyjne",
	"zgoda_realizacja_przed_odstapieniem",
	"drugi_zamawiajacy",
]
"""Jedyne pola `Volteo Umowa`, jakie `volteo_umowa_save` przyjmuje od klienta.

Nigdy nie robimy ślepego ``doc.update(dane)`` z danych przesłanych przez przeglądarkę —
wszystko spoza tej listy jest po cichu odrzucane. `kwota_kredytu_pln` i `ppoz_wymagane`
celowo NIE są tu wymienione: są liczone wyłącznie na serwerze (patrz `_wyliczenia`).
`adres_montaz_nr_mieszkania` jest tu celowo, mimo że instalacja zwykle dotyczy domu
jednorodzinnego: `typ_budynku` dopuszcza „Wielorodzinny” (§1.2 umowy — „Mieszkaniu w
budynku wielorodzinnym”), więc adres montażu czasem wymaga numeru mieszkania.
`zgoda_kontakt_telefoniczny` i `zgoda_dzialania_promocyjne` to zgody RODO/marketingowe
z Załącznika 2 — mają wagę prawną, patrz `_POLA_CHECKBOX` dla ich koercji.
`zgoda_realizacja_przed_odstapieniem` to oświadczenie klienta z Załącznika nr 3
(realizacja Umowy przed upływem ustawowego terminu na odstąpienie) — to warunek
umowy, nie zgoda marketingowa, więc celowo NIE jest kopiowane na `Contact` przez
`_propaguj_zgody` poniżej.
`drugi_zamawiajacy` (ops#168) to Link do `Contact` drugiego Zamawiającego dla
wariantu umowy podwójnej: samo przyjęcie wartości z klienta idzie tą samą
allowlistą jak reszta pól, ale zapis w `volteo_umowa_save` dokłada osobną
walidację (kontakt musi istnieć i różnić się od kontaktu podstawowego szansy)
i efekt uboczny (dopięcie kontaktu do `deal_doc.contacts`), patrz komentarz
przy tej walidacji niżej.
"""

_POLA_KWOTOWE = frozenset({"wklad_wlasny_pln"})
"""Pola kwotowe wymagające konwersji przez `Decimal` zamiast surowego przypisania."""

_POLA_CHECKBOX = frozenset(
	{"zgoda_kontakt_telefoniczny", "zgoda_dzialania_promocyjne", "zgoda_realizacja_przed_odstapieniem"}
)
"""Pola Check (0/1 Int) wymagające jawnej koercji przez `cint`, nigdy `bool()`.

Pułapka: `bool("0")` daje `True` w Pythonie, więc string ``"0"`` przepuszczony bez
koercji zapisałby się jako zgoda udzielona, mimo że przedstawiciel jej nie zaznaczył.
`cint` poprawnie sprowadza do 0/1 zarówno booleany JSON (`True`/`False`), jak i stringi
liczbowe (``"0"``/``"1"``); nieparsowalne wejście pada na bezpieczne domyślne 0.
"""

_UMOWA_POLA_WYJSCIOWE = [*_DANE_POLA_DOZWOLONE, "kwota_kredytu_pln", "ppoz_wymagane"]
"""Pola `Volteo Umowa` zwracane w bloku `umowa` odpowiedzi — dane formularza plus
serwerowo przeliczone `kwota_kredytu_pln`/`ppoz_wymagane`, których wartości są
zawsze te ostatnio zapisane (świeże przeliczenie na żądanie jest w `wyliczenia`)."""


def _sprawdz_role() -> None:
	"""Sprawdza rolę uprawnioną do korzystania z formularza — ten sam gate co kalkulator."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)


def _sprawdz_dostep_do_szansy(deal: str, tryb: str) -> None:
	"""Sprawdza istnienie szansy i uprawnienie `read`/`write` wywołującego do niej."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Szansa sprzedaży nie istnieje."), frappe.DoesNotExistError)
	if not frappe.has_permission("CRM Deal", tryb, deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd formularza")
	frappe.throw(_("Wystąpił błąd podczas zapisu formularza umowy."))


def _blad_generowania_pdf() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd generowania PDF")
	frappe.throw(_("Wystąpił błąd podczas generowania PDF-u umowy. Spróbuj ponownie."))


def _blad_rodzaju_umowy_bez_szablonu(rodzaj: str | None) -> NoReturn:
	"""Rodzaj umowy szansy (`custom_rodzaj_umowy`) nie ma wbudowanego szablonu PDF-u
	(`kod not in SZABLONY`) — to błąd DANYCH szansy (albo jej brak), nie awaria
	wdrożenia, więc NIE loguje przez `frappe.log_error` i wymaga rozróżnienia w
	komunikacie dwóch odrębnych sytuacji:

	1. rodzaj pusty/nierozpoznany — przedstawiciel ma ustawić „Rodzaj umowy” na
	   szansie na jedną z trzech obsługiwanych wartości;
	2. rodzaj to „Czyste Powietrze” — ten PDF świadomie obsługuje wyłącznie
	   umowy PV/magazyn (zob. `crm.volteo_umowa_render` — `CP` celowo nie ma
	   wpisu w `SZABLONY`), więc komunikat mówi wprost, że to inny produkt,
	   zamiast sugerować literówkę czy usterkę.
	"""
	if rodzaj == "Czyste Powietrze":
		frappe.throw(
			_(
				"PDF umowy w tym miejscu obejmuje wyłącznie umowy Fotowoltaika / "
				"Fotowoltaika + Magazyn / Magazyn energii — nie dotyczy Czyste Powietrze."
			)
		)
	frappe.throw(
		_(
			"Ustaw „Rodzaj umowy” na szansie sprzedaży na jedną z wartości: "
			"Fotowoltaika, Fotowoltaika + Magazyn, Magazyn energii — dopiero wtedy "
			"można wygenerować PDF umowy."
		)
	)


def _blad_brakujacego_szablonu() -> NoReturn:
	"""Wbudowany szablon PDF-u (jeden z trzech: `crm/szablony/umowa_pv.pdf`,
	`umowa_pv_me.pdf`, `umowa_me.pdf` — wg rodzaju umowy szansy) nie wczytał się z dysku.

	To awaria WDROŻENIA (plik nie trafił do obrazu albo jest uszkodzony), nie
	błąd użytkownika ani danych szansy — komunikat celowo nie sugeruje "spróbuj
	ponownie" (to nie pomoże) i nie wygląda jak zwykły błąd generowania.
	"""
	frappe.log_error(frappe.get_traceback(), "Volteo Umowa: brak wbudowanego szablonu PDF")
	frappe.throw(
		_("Szablon PDF-u umowy nie jest dostępny w tej instalacji. Skontaktuj się z administratorem systemu.")
	)


def _blad_zapisu_pliku() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd zapisu pliku PDF")
	frappe.throw(_("PDF wygenerowano, ale nie udało się go zapisać. Spróbuj ponownie."))


def _pobierz_umowe(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca dokument `Volteo Umowa` dla szansy, jeśli istnieje — inaczej `None`.

	Nazwa dokumentu jest tożsama z nazwą szansy (`autoname: field:deal`), więc
	sprawdzenie istnienia i pobranie odbywa się po tym samym kluczu.
	"""
	if frappe.db.exists(DOCTYPE, deal):
		return frappe.get_doc(DOCTYPE, deal)
	return None


def _podstawowy_kontakt(deal_doc: "frappe.model.document.Document") -> str | None:
	"""Zwraca nazwę podstawowego kontaktu (`is_primary`) szansy albo `None`, gdy go brak."""
	for wiersz in deal_doc.contacts:
		if wiersz.is_primary:
			return wiersz.contact
	return None


def _dane_kontaktu(kontakt: str | None) -> dict[str, Any]:
	"""Dane podstawowego kontaktu do `prefill`; puste stringi, gdy kontakt nie istnieje.

	Świadomie nigdy nie rzuca — brak podstawowego kontaktu na szansie jest normalnym,
	niekompletnym stanem, a nie błędem formularza.
	"""
	puste = {pole: "" for pole in _KONTAKT_POLA} | {"email": "", "mobile_no": ""}
	if not kontakt:
		return puste

	dane = frappe.db.get_value("Contact", kontakt, _KONTAKT_POLA, as_dict=True)
	if not dane:
		return puste

	wynik = {pole: dane.get(pole) or "" for pole in _KONTAKT_POLA}
	wynik["email"] = (
		frappe.db.get_value("Contact Email", {"parent": kontakt, "is_primary": 1}, "email_id") or ""
	)
	wynik["mobile_no"] = (
		frappe.db.get_value("Contact Phone", {"parent": kontakt, "is_primary_mobile_no": 1}, "phone") or ""
	)
	return wynik


def _prefill_drugi(umowa_doc: "frappe.model.document.Document | None") -> dict[str, Any]:
	"""Dane drugiego Zamawiającego (ops#168) do osobnego bloku `prefill_drugi`,
	tym samym kształtem kluczy co `_dane_kontaktu` dla kontaktu podstawowego
	(``first_name``/``last_name``/``custom_pesel``/adres/``email``/``mobile_no``).
	Pusty dokument umowy albo brak `drugi_zamawiajacy` daje same puste stringi,
	`_dane_kontaktu(None)` już to robi, świadomie nigdy nie rzuca.
	"""
	kontakt = umowa_doc.get("drugi_zamawiajacy") if umowa_doc else None
	return _dane_kontaktu(kontakt)


def _prefill(deal_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Składa blok `prefill`: surowe pola szansy/kontaktu PLUS wpisy zmapowane na
	fieldnames `Volteo Umowa` (`_PREFILL_MAPOWANIE`), których frontend faktycznie
	szuka podczas hydratacji formularza. Brakujące/`None` źródło daje pusty string,
	nigdy `None` — żeby `None` nie wyciekło do pola tekstowego w formularzu.
	"""
	dane = {pole: deal_doc.get(pole) for pole in _DEAL_POLA_PREFILL}
	kontakt = _podstawowy_kontakt(deal_doc)
	dane.update(_dane_kontaktu(kontakt))
	for zrodlo, cel in _PREFILL_MAPOWANIE.items():
		# Jawne None-check, NIE `or ""`: `wklad_wlasny_pln` to kwota, gdzie 0 jest
		# poprawną wartością (brak wkładu własnego) i `0 or ""` zgubiłoby to zero.
		wartosc = dane.get(zrodlo)
		dane[cel] = wartosc if wartosc is not None else ""
	return dane


def _wyliczenia(
	deal_doc: "frappe.model.document.Document",
	umowa_doc: "frappe.model.document.Document | None",
) -> dict[str, Any]:
	"""Wartości liczone na żądanie: miejsce montażu, pokrycie dachowe, wymóg PPOŻ,
	kwota kredytu, lista brakujących pól formularza umowy, lista brakujących
	danych osobowych klienta z karty kontaktu (ops#146) i, gdy umowa ma drugiego
	Zamawiającego (ops#168), ta sama lista dla niego (`brakujace_dane_drugiego`).
	Zawsze przeliczane od nowa z bieżącego stanu szansy, umowy i kontaktu(ów),
	nigdy nie ufamy wcześniej zapisanym wartościom.
	"""
	miejsce, pokrycie = miejsce_i_pokrycie(deal_doc.get("custom_konstrukcja"))
	moc_istniejaca = umowa_doc.get("istniejaca_pv_moc_kwp") if umowa_doc else None
	istniejaca_pv = umowa_doc.get("istniejaca_pv") if umowa_doc else None
	wklad = umowa_doc.get("wklad_wlasny_pln") if umowa_doc else None
	finansowanie = umowa_doc.get("finansowanie") if umowa_doc else None
	dane_do_walidacji = {pole: umowa_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE} if umowa_doc else {}
	kontakt_dane = _dane_kontaktu(_podstawowy_kontakt(deal_doc))
	drugi_kontakt = umowa_doc.get("drugi_zamawiajacy") if umowa_doc else None

	return {
		"miejsce_montazu": miejsce,
		"pokrycie_dachowe": pokrycie,
		# `deal_doc.get("custom_ppoz")` zwraca None, gdy pole nie istnieje jeszcze
		# w schemacie (ops skrypt jeszcze nie uruchomiony), bezpieczne, bo `None`
		# zostawia regułę progową bez zmian, patrz docstring `ppoz_wymagane` (ops#194).
		"ppoz_wymagane": ppoz_wymagane(
			deal_doc.get("custom_pv_power_kwp"), moc_istniejaca, istniejaca_pv, deal_doc.get("custom_ppoz")
		),
		"kwota_kredytu_pln": kwota_kredytu(deal_doc.get("deal_value"), wklad, finansowanie),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
		"brakujace_dane_klienta": brakujace_dane_klienta(kontakt_dane),
		# Brak drugiego Zamawiającego to normalny stan (umowa pojedyncza), pusta
		# lista, NIE lista czterech braków wyliczona z pustego kontaktu; stąd jawny
		# warunek zamiast `brakujace_dane_klienta(_dane_kontaktu(drugi_kontakt))`.
		"brakujace_dane_drugiego": brakujace_dane_klienta(_dane_kontaktu(drugi_kontakt)) if drugi_kontakt else [],
	}


def _umowa_do_dict(umowa_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Spłaszcza dokument `Volteo Umowa` do bloku `umowa` odpowiedzi."""
	wynik = {pole: umowa_doc.get(pole) for pole in _UMOWA_POLA_WYJSCIOWE}
	wynik["name"] = umowa_doc.name
	wynik["deal"] = umowa_doc.deal
	wynik["status"] = umowa_doc.status
	return wynik


def _decimal_lub_none(wartosc: Any) -> Decimal | None:
	"""Konwertuje kwotę na `Decimal` przez `str()` (nigdy `Decimal(float)`); puste wejście → `None`."""
	if wartosc is None or wartosc == "":
		return None
	try:
		return Decimal(str(wartosc))
	except (ArithmeticError, ValueError, TypeError):
		frappe.throw(_("Nieprawidłowa wartość kwoty."))


def _propaguj_zgody(
	deal_doc: "frappe.model.document.Document",
	umowa_doc: "frappe.model.document.Document",
) -> None:
	"""Kopiuje zgody `zgoda_kontakt_telefoniczny`/`zgoda_dzialania_promocyjne` z `Volteo
	Umowa` na karty `Contact` OBU Zamawiających: podstawowego kontaktu szansy oraz,
	gdy umowa ma ustawiony `drugi_zamawiajacy` (ops#168, drugi Zamawiający na umowie
	dwuosobowej), także jego (decyzja właściciela 2026-09-23, ops#170). Na papierze
	(Załącznik 2) jest jedna wspólna para pól wyboru i jedna linia podpisu
	Zamawiającego, ale obie osoby stają się stroną dokumentu, więc obie dostają
	zapis zgody na swojej karcie kontaktu, żeby dało się filtrować/budować listę
	kontaktów po zgodach.

	Najnowsza deklaracja nadpisuje poprzednią: nawet gdy przedstawiciel odznaczy
	obie zgody, nadpisujemy nimi `Contact`, historyczny fakt, że zgoda kiedyś była
	udzielona, zostaje zachowany na tym konkretnym rekordzie `Volteo Umowa` i nie
	jest tu retroaktywnie zmieniany. Data i źródło zgody są stemplowane WYŁĄCZNIE
	gdy przynajmniej jedna zgoda jest udzielona.

	Propagacja NIE odpala się, gdy dokument już poszedł do podpisu albo został
	podpisany (`czy_propagowac_zgody`, REVISIT.md A-3, ops#170), żeby późniejszy
	zapis roboczego formularza nie zmieniał retroaktywnie zgody na kartach
	kontaktów. Konsentem wiążącym jest ten widoczny na podpisanym PDF-ie, nie ten
	ostatnio zaznaczony w formularzu.
	"""
	if not czy_propagowac_zgody(umowa_doc.get("autenti_status")):
		frappe.logger().info(
			"Volteo Umowa %s: pomijam propagacje zgod do Contact, autenti_status=%r"
			% (umowa_doc.name, umowa_doc.get("autenti_status"))
		)
		return

	kontakty = kontakty_do_zgod(_podstawowy_kontakt(deal_doc), umowa_doc.get("drugi_zamawiajacy"))
	if not kontakty:
		return

	telefon = umowa_doc.get("zgoda_kontakt_telefoniczny")
	marketing = umowa_doc.get("zgoda_dzialania_promocyjne")

	aktualizacja: dict[str, Any] = {
		"custom_zgoda_telefon": telefon,
		"custom_zgoda_marketing": marketing,
	}
	if telefon or marketing:
		aktualizacja["custom_zgoda_data"] = frappe.utils.nowdate()
		aktualizacja["custom_zgoda_zrodlo"] = umowa_doc.name

	for kontakt in kontakty:
		try:
			# `Contact.custom_pesel` jest polem wymaganym (reqd=1), a wiele istniejących
			# kontaktów powstało przed jego dodaniem i ma je puste, `.save()` na takim
			# kontakcie wywaliłoby walidację pola wymaganego i zepsuło zapis CAŁEGO
			# formularza umowy z powodu zupełnie niepowiązanego efektu ubocznego.
			# `db.set_value` omija walidację dokumentu, więc jest tu bezpieczne.
			frappe.db.set_value("Contact", kontakt, aktualizacja, update_modified=False)
		except Exception:
			# Utrata wypełnionego formularza umowy przez błąd w efekcie ubocznym (kopii
			# zgód na Contact) byłaby gorszym skutkiem niż samo zalogowanie i pominięcie
			# propagacji dla TEGO kontaktu, jeden nieudany zapis nie może pominąć zapisu
			# dla drugiego kontaktu ani przerwać zapisu umowy.
			frappe.log_error(frappe.get_traceback(), "Volteo Umowa: propagacja zgód do Contact")


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_umowa_get(deal: str) -> dict[str, Any]:
	"""Zwraca istniejący rekord `Volteo Umowa` (jeśli jest), dane `prefill`,
	`prefill_drugi` (dane drugiego Zamawiającego, ops#168, puste gdy nieustawiony)
	i `wyliczenia`.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)

	return {
		"umowa": _umowa_do_dict(umowa_doc) if umowa_doc else None,
		"prefill": _prefill(deal_doc),
		"prefill_drugi": _prefill_drugi(umowa_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_umowa_create(deal: str) -> dict[str, Any]:
	"""Tworzy `Volteo Umowa` dla szansy. Idempotentne: jeśli rekord już istnieje
	(np. podwójne kliknięcie „Wygeneruj umowę”), zwraca istniejący zamiast rzucać
	`DuplicateEntryError` — nazwa dokumentu jest nazwą szansy, więc naiwny `insert()`
	wybuchłby przy powtórnym wywołaniu.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)

	if umowa_doc is None:
		try:
			umowa_doc = frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"deal": deal,
					"status": "Roboczy",
					"dodatkowy_kabel_m": deal_doc.get("custom_kabel_m"),
					"wklad_wlasny_pln": deal_doc.get("custom_wplata_wlasna"),
					# ops#194: świeżo utworzony rekord od razu niesie odpowiedź kalkulatora
					# o istniejącej instalacji PLUS przeliczony wymóg PPOŻ, żeby PDF
					# (`crm/volteo_umowa_pdf.py`, `_stan_bool(umowa.get("ppoz_wymagane"))`)
					# nie musiał czekać na pierwsze „Zapisz": bez tego dokument utworzony
					# i od razu wydrukowany (bez edycji) miałby `ppoz_wymagane=None`.
					"istniejaca_pv": deal_doc.get("custom_istniejaca_pv"),
					"istniejaca_pv_moc_kwp": deal_doc.get("custom_istniejaca_pv_moc_kwp"),
					"ppoz_wymagane": ppoz_wymagane(
						deal_doc.get("custom_pv_power_kwp"),
						deal_doc.get("custom_istniejaca_pv_moc_kwp"),
						deal_doc.get("custom_istniejaca_pv"),
						deal_doc.get("custom_ppoz"),
					),
				}
			)
			umowa_doc.insert()
			try:
				zapisz_slad(deal, tekst_sladu("umowa_utworzono"))
			except Exception:
				# Ślad w Aktywności to wygoda, nie warunek sukcesu — awaria zapisu
				# śladu nie może cofnąć ani zablokować już utworzonego rekordu umowy.
				frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd zapisu śladu utworzenia")
		except frappe.DuplicateEntryError:
			# Wyścig: inna sesja/kliknięcie zdążyło wstawić rekord między sprawdzeniem a insertem.
			umowa_doc = frappe.get_doc(DOCTYPE, deal)
		except Exception:
			_blad_ogolny()

	return {
		"umowa": _umowa_do_dict(umowa_doc),
		"prefill": _prefill(deal_doc),
		"prefill_drugi": _prefill_drugi(umowa_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}


def _zwaliduj_i_dopnij_drugiego_zamawiajacego(
	deal_doc: "frappe.model.document.Document",
	umowa_doc: "frappe.model.document.Document",
) -> None:
	"""Waliduje `drugi_zamawiajacy` (ops#168) i, gdy trzeba, dopina go do szansy.

	Panel boczny szansy świadomie pokazuje jednego klienta (decyzja właściciela
	2026-09-03, patrz `CRM Deal`/`is_primary` w reszcie forka), drugi uczestnik
	umowy jest dopinany WYŁĄCZNIE tutaj, z poziomu formularza umowy, nigdy przez
	panel szansy. Kontakt musi już istnieć w bazie i różnić się od podstawowego
	kontaktu szansy (`_podstawowy_kontakt`), inaczej to nie jest "drugi" nikt.
	Jeśli kontakt nie jest jeszcze podpięty do `deal_doc.contacts`, dopisujemy
	go jako wiersz NIE-podstawowy (`is_primary=0`), nigdy nie zamieniamy ani nie
	dotykamy istniejącego podstawowego wiersza. Pusty `drugi_zamawiajacy` (umowa
	pojedyncza, częstszy przypadek) jest no-opem.
	"""
	drugi = umowa_doc.get("drugi_zamawiajacy")
	if not drugi:
		return

	if not frappe.db.exists("Contact", drugi):
		frappe.throw(_("Wskazany drugi Zamawiający nie istnieje."))

	podstawowy = _podstawowy_kontakt(deal_doc)
	if drugi == podstawowy:
		frappe.throw(_("Drugi Zamawiający musi być innym kontaktem niż podstawowy kontakt szansy."))

	juz_podpiety = any(wiersz.contact == drugi for wiersz in deal_doc.contacts)
	if juz_podpiety:
		return

	try:
		deal_doc.append("contacts", {"contact": drugi, "is_primary": 0})
		deal_doc.save(ignore_permissions=False)
	except Exception:
		_blad_ogolny()


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_umowa_save(deal: str, dane: dict[str, Any]) -> dict[str, Any]:
	"""Zapisuje formularz umowy z allowlistą pól i serwerowym przeliczeniem.

	Niekompletny zapis jest poprawnym stanem roboczym (przedstawiciel wypełnia
	formularz stopniowo) — brakujące wymagane pola NIE blokują zapisu, tylko
	ustawiają `status="Roboczy"` i trafiają do `wyliczenia.brakujace_pola`, żeby
	UI mógł je podświetlić. Dopiero komplet danych daje `status="Kompletny"`.
	`kwota_kredytu_pln` i `ppoz_wymagane` przesłane przez klienta są ignorowane —
	liczy je wyłącznie serwer.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	if not isinstance(dane, dict):
		frappe.throw(_("Nieprawidłowy format danych formularza."))

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)
	if umowa_doc is None:
		frappe.throw(_("Najpierw wygeneruj umowę dla tej szansy sprzedaży."))

	for pole in _DANE_POLA_DOZWOLONE:
		if pole not in dane:
			continue
		wartosc = dane[pole]
		if pole in _POLA_KWOTOWE:
			wartosc = _decimal_lub_none(wartosc)
		elif pole in _POLA_CHECKBOX:
			# Jawna koercja przez cint — NIGDY bool(), bo bool("0") == True w Pythonie.
			wartosc = cint(wartosc)
		umowa_doc.set(pole, wartosc)

	# ops#168: musi biec PO pętli powyżej (żeby widzieć świeżo ustawiony
	# `drugi_zamawiajacy`) i PRZED `umowa_doc.save()` niżej, rzuca od razu na
	# nieprawidłowym wyborze, zanim cokolwiek trafi do bazy.
	_zwaliduj_i_dopnij_drugiego_zamawiajacego(deal_doc, umowa_doc)

	braki = brakujace_pola({pole: umowa_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE})
	# Status "Kompletny" wymaga TAKŻE kompletu danych osobowych klienta z karty
	# kontaktu (ops#146 Z4). Bez tej bramki dokument prawny mógł wyjść ze
	# statusem "Kompletny" mimo pustego PESEL-u/telefonu/e-maila w komparycji.
	braki_klienta = brakujace_dane_klienta(_dane_kontaktu(_podstawowy_kontakt(deal_doc)))
	umowa_doc.status = "Roboczy" if (braki or braki_klienta) else "Kompletny"

	# Kwota kredytu i wymóg PPOŻ liczone są WYŁĄCZNIE na serwerze i nadpisują cokolwiek
	# przesłał klient — klient nie może ustawić kwoty kredytu ani ominąć wymogu PPOŻ.
	# Obie funkcje dostają też pole sterujące (`finansowanie`/`istniejaca_pv`)
	# świeżo zapisane wyżej w pętli `umowa_doc.set(...)`: jawny wybór w Selekcie
	# gasi resztkę wartości zostawioną w polu warunkowym (ops#145 Z1/Z2).
	umowa_doc.kwota_kredytu_pln = kwota_kredytu(
		deal_doc.get("deal_value"), umowa_doc.get("wklad_wlasny_pln"), umowa_doc.get("finansowanie")
	)
	# `deal_doc.get("custom_ppoz")` zwraca None, gdy pole nie istnieje jeszcze
	# w schemacie (ops skrypt jeszcze nie uruchomiony), bezpieczne, bo `None`
	# zostawia regułę progową bez zmian, patrz docstring `ppoz_wymagane` (ops#194).
	umowa_doc.ppoz_wymagane = ppoz_wymagane(
		deal_doc.get("custom_pv_power_kwp"),
		umowa_doc.get("istniejaca_pv_moc_kwp"),
		umowa_doc.get("istniejaca_pv"),
		deal_doc.get("custom_ppoz"),
	)

	try:
		umowa_doc.save()
	except Exception:
		_blad_ogolny()

	_propaguj_zgody(deal_doc, umowa_doc)

	return {
		"umowa": _umowa_do_dict(umowa_doc),
		"prefill": _prefill(deal_doc),
		"prefill_drugi": _prefill_drugi(umowa_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}


_KOMPONENT_POLA = list(POLA_KOMPONENTU)
"""Pola `Volteo Komponent` czytane dla PDF-u umowy. WYPROWADZONE z
`crm.volteo_umowa_pdf.POLA_KOMPONENTU` — JEDYNEGO źródła prawdy o tym, czego
`zbuduj_kontekst()` faktycznie potrzebuje — żeby ta lista i logika dopasowania
komponentu (`_znajdz_komponent`, filtrująca po `kategoria`) nie mogły się już
rozjechać tak jak 2026-08-06, gdy literał tu pomijał `kategoria` i żaden
komponent nigdy się nie dopasowywał.

Celowo BEZ `cena_jednostkowa_netto` (permlevel 1, wewnętrzna cena) — model
tajemnicy kosztów: żadne pole kosztowe/marżowe/prowizyjne nie może trafić do
kontekstu szablonu, niezależnie od tego, czy wywołujący użytkownik miałby
techniczne uprawnienia je odczytać gdzie indziej."""
assert "cena_jednostkowa_netto" not in _KOMPONENT_POLA, (
	"Volteo Komponent.cena_jednostkowa_netto (permlevel 1, cena wewnętrzna) nie może "
	"trafić do kontekstu PDF-u umowy — patrz model tajemnicy kosztów w docstringu wyżej."
)


def _komponenty_katalogu() -> list[dict[str, Any]]:
	"""Zwraca wszystkie wiersze katalogu `Volteo Komponent`, tylko pola kliencie/techniczne.

	Dezaktywacja karty jest rutynową rotacją dostępności, a nie usunięciem danych.
	Zgodnie z konwencją wiersze katalogu nigdy nie są usuwane, więc historyczne deale
	muszą nadal rozwiązywać swoje komponenty także po ich dezaktywacji.

	`zbuduj_kontekst` sam dopasowuje wiersz do `deal.custom_falownik`/`custom_bateria`
	/`custom_panel` po złożeniu `f"{nazwa} {model}"` (struktura doctype'u jest odwrotna
	do intuicji — `nazwa` to producent, `model` to model) — tu tylko pobieramy pełną
	listę katalogu.
	"""
	return frappe.get_all("Volteo Komponent", fields=_KOMPONENT_POLA)


def _wiersze_zestawu(deal_doc: "frappe.model.document.Document") -> list[dict[str, Any]]:
	"""Spłaszcza wiersze `custom_zestaw` (typ/nazwa/ilość) do zwykłych dictów."""
	return [
		{"typ": wiersz.get("typ"), "nazwa": wiersz.get("nazwa"), "ilosc": wiersz.get("ilosc")}
		for wiersz in deal_doc.get("custom_zestaw") or []
	]


def _usun_stare_pdfy_umowy(deal: str, nazwa_pliku: str) -> None:
	"""Usuwa wszystkie wcześniejsze rekordy `File` z PDF-em umowy TEJ szansy.

	Frappe nie nadpisuje pliku o istniejącej nazwie przy kolejnym `insert()` —
	dokleja losowy sufiks tuż przed rozszerzeniem (`Umowa-PRO-PVME-26-1000.pdf`
	→ `Umowa-PRO-PVME-26-1000e41034.pdf`). Dopasowanie po dokładnej nazwie
	niczego by więc nie znalazło po drugim wywołaniu; zamiast tego dopasowujemy
	PREFIKS `nazwa_pliku` bez rozszerzenia + dowolny sufiks + `.pdf`.

	Bezpieczeństwo zakresu — filtr łączy TRZY warunki jednocześnie:
	1. `attached_to_doctype == "CRM Deal"`,
	2. `attached_to_name == deal` — żaden załącznik INNEJ szansy nie może zostać
	   złapany, niezależnie od tego, jak nazywa się jego plik;
	3. `file_name LIKE "<prefiks tej szansy>%.pdf"` — inne załączniki TEJ SAMEJ
	   szansy (np. PDF faktury) mają inny prefiks nazwy (nie zaczynają się od
	   `Umowa-<ta szansa>`) i nie pasują do wzorca, więc przeżywają.
	Oba warunki (2) i (3) muszą być spełnione naraz, więc nawet plik o nazwie
	pasującej do wzorca, ale podpięty pod inną szansę, nie zostanie ruszony.
	Znaki `%`/`_` w nazwie szansy (nietypowe w naszym schemacie nazewnictwa, ale
	teoretycznie możliwe) są eskejpowane, żeby nie działały jako wildcardy LIKE.

	Usuwanie jest rekordem (`frappe.delete_doc`), nie tylko plikiem z dysku, żeby
	nie zostawiać osieroconych wpisów `File`. Nieudane sprzątnięcie NIE MOŻE
	zablokować wygenerowania nowego PDF-u — błąd trafia do `frappe.log_error`
	i przetwarzanie idzie dalej.
	"""
	prefiks = nazwa_pliku[: -len(".pdf")]  # "Umowa-<szansa z myślnikami zamiast ukośników>"
	wzorzec = prefiks.replace("%", r"\%").replace("_", r"\_") + "%.pdf"
	stare_pliki = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": ["like", wzorzec],
		},
		pluck="name",
	)
	for nazwa in stare_pliki:
		try:
			frappe.delete_doc("File", nazwa, ignore_permissions=True, delete_permanently=True)
		except Exception:
			frappe.log_error(title="volteo_umowa_pdf: nie udało się usunąć starego pliku PDF umowy")


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def volteo_umowa_pdf(deal: str) -> dict[str, Any]:
	"""Generuje PDF umowy dla szansy sprzedaży i zapisuje go jako prywatny plik
	podpięty do `CRM Deal`. Zwraca `{"file_url": ..., "file_name": ...}`.

	Dokument PDF nie jest już odtwarzany w HTML — kontekst danych jest nakładany
	jako warstwa na ORYGINALNY plik PDF od prawnika (jeden z sześciu wbudowanych
	szablonów w `crm/szablony/`: trzy jednoosobowe plus, od ops#167, trzy
	PODWÓJNE dla umowy z drugim Zamawiającym, wybrany wg `custom_rodzaj_umowy`
	szansy i obecności `Volteo Umowa.drugi_zamawiajacy` przez
	`crm.volteo_umowa.kod_szablonu` i rejestr `crm.volteo_umowa_render.SZABLONY`),
	przez `crm.volteo_umowa_render.zloz_umowe`, według współrzędnych z mapy
	właściwej temu szablonowi. Dzięki temu treść prawna, układ i podział stron
	są dokładnie takie jak w oryginale.

	Umowa PODWÓJNA (ops#167, drugi Zamawiający ustawiony na `Volteo Umowa`):
	wybiera automatycznie szablon `<KOD>_2` zamiast `<KOD>` i dokłada dane
	drugiego Zamawiającego (`kontakt2=`) do `zbuduj_kontekst`; braki w jego
	danych osobowych (imię/nazwisko, PESEL, telefon, e-mail) blokują
	generowanie tym samym mechanizmem co dla osoby pierwszej. Umowa
	POJEDYNCZA (bez `drugi_zamawiajacy`) przechodzi przez DOKŁADNIE tę samą
	ścieżkę co przed tym zadaniem: `kod`/`kontakt2` niedotknięte, żadna
	gałąź niżej się nie wykonuje.

	Uprawnienia: rola kalkulatora + `write` na szansie (SEC#35 — było `read`:
	generowanie PDF-u faktycznie zapisuje nowy plik `File` podpięty do szansy i,
	niżej, przesuwa status szansy przez `advance_deal_status`, więc `read` był
	niewystarczającą bramką dla mutującego endpointu). Model tajemnicy kosztów/prowizji:
	do kontekstu trafiają
	wyłącznie kwoty netto/brutto DLA KLIENTA (`deal_value`, `custom_netto`,
	`wklad_wlasny_pln`, `kwota_kredytu_pln`) i dane techniczne — nigdy
	`cena_jednostkowa_netto`, marże ani prowizje (patrz `_KOMPONENT_POLA`, które
	jawnie pomija cenę wewnętrzną komponentu; `Volteo Kalkulator Stale` przekazujemy
	w całości do `zbuduj_kontekst`, ale nakładanie na PDF czyta z kontekstu
	wyłącznie pola `panel_*` — kosztowe/marżowe pola tej Single nigdy nie trafiają
	na wydrukowaną stronę).

	Rodzaj umowy bez wbudowanego szablonu (pusty/nierozpoznany `custom_rodzaj_umowy`,
	albo „Czyste Powietrze” — ten PDF obejmuje wyłącznie umowy PV/magazyn) odmawia
	generowania OD RAZU, przed odczytem pliku szablonu (patrz
	`_blad_rodzaju_umowy_bez_szablonu`) — celowo rozróżnione od braku rekordu
	`Volteo Umowa` (formularz jeszcze niewypełniony, poniżej) i od braku/uszkodzenia
	samego pliku szablonu na dysku (awaria wdrożenia, `_blad_brakujacego_szablonu`) —
	trzy różne przyczyny, trzy różne, jednoznaczne komunikaty dla użytkownika.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	rodzaj_umowy = deal_doc.get("custom_rodzaj_umowy")
	kod = code_for(rodzaj_umowy)
	if kod not in SZABLONY:
		_blad_rodzaju_umowy_bez_szablonu(rodzaj_umowy)

	umowa_doc = _pobierz_umowe(deal)
	if umowa_doc is None:
		frappe.throw(_("Najpierw wypełnij formularz informacji do umowy dla tej szansy sprzedaży."))

	# Umowa wysłana do podpisu (albo już podpisana) nie może zostać po cichu
	# podmieniona nowym PDF-em — klient musiałby podpisać inne bajty niż te,
	# które faktycznie widzi w Autenti. Po stanach terminalnych NIE-sukcesu
	# (Odrzucona/Wygasła/Wycofana/Błąd) regenerowanie jest świadomie znów
	# dozwolone: Autenti i tak trzyma własną kopię SOURCE_FILE tego, co już
	# raz zostało wysłane, więc nadpisanie lokalnego PDF-u niczego tam nie zmienia.
	if umowa_doc.get("autenti_status") in autenti_logika.SEND_BLOCKED_STATUSES:
		frappe.throw(_("Umowa została wysłana do podpisu — nie można wygenerować nowego PDF-u."))

	# Umowa PODWÓJNA (ops#167): przełącza `kod` na wariant `<KOD>_2` i wymaga
	# kompletnych danych drugiego Zamawiającego przed generowaniem. TA CAŁA
	# GAŁĄŹ jest no-op dla umowy pojedynczej (`czy_umowa_podwojna` fałsz), więc
	# `kod`/`kontakt2` niżej zostają dokładnie takie, jak przed tym zadaniem:
	# ŚCIEŻKA JEDNOOSOBOWA JEST NIEZMIENIONA.
	kontakt2: dict[str, Any] | None = None
	if czy_umowa_podwojna(umowa_doc.as_dict()):
		kod = kod_szablonu(rodzaj_umowy, True)
		kontakt2 = _dane_kontaktu(umowa_doc.get("drugi_zamawiajacy"))
		braki_drugiego = brakujace_dane_klienta(kontakt2)
		if braki_drugiego:
			frappe.throw(
				_(
					"Uzupełnij dane drugiego Zamawiającego przed wygenerowaniem PDF-u "
					"umowy: {0}."
				).format(", ".join(braki_drugiego))
			)

	kontakt = _podstawowy_kontakt(deal_doc)

	try:
		szablon_pdf = sciezka_wbudowanego_szablonu(kod).read_bytes()
	except OSError:
		_blad_brakujacego_szablonu()

	try:
		kontekst = zbuduj_kontekst(
			umowa=umowa_doc.as_dict(),
			deal={pole: deal_doc.get(pole) for pole in _DEAL_POLA_PREFILL},
			kontakt=_dane_kontaktu(kontakt),
			zestaw=_wiersze_zestawu(deal_doc),
			komponenty=_komponenty_katalogu(),
			stale=dict(frappe.db.get_singles_dict("Volteo Kalkulator Stale") or {}),
			dzis=getdate(),
			kontakt2=kontakt2,
		)
		pdf_bytes = zloz_umowe(kontekst, szablon_pdf, kod)
	except Exception:
		_blad_generowania_pdf()

	nazwa_pliku = autenti_logika.nazwa_pliku_umowy(deal)
	_usun_stare_pdfy_umowy(deal, nazwa_pliku)
	try:
		plik = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": nazwa_pliku,
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": deal,
				"is_private": 1,
				"content": pdf_bytes,
			}
		)
		with plik_systemowy():
			plik.insert(ignore_permissions=True)
	except Exception:
		_blad_zapisu_pliku()

	try:
		zapisz_slad(deal, tekst_sladu("umowa_pdf"))
	except Exception:
		# Ślad w Aktywności to wygoda, nie warunek sukcesu — awaria zapisu śladu
		# nie może cofnąć ani zablokować już zapisanego pliku PDF.
		frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd zapisu śladu PDF")

	# Automatyzacja: przesuwa status szansy do przodu, o ile włączona w panelu
	# admina i przejście jest do przodu w JEJ procesie; nigdy nie rzuca — awaria
	# automatyzacji nie może cofnąć już wygenerowanego i zapisanego PDF-u.
	advance_deal_status(deal, "Umowa Wygenerowana", "umowa_wygenerowana")

	return {"file_url": plik.file_url, "file_name": plik.file_name}
