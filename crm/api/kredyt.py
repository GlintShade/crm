"""Whitelisted API formularza „Kredyt” (doctype `Volteo Kredyt`).

Od ops#158 (po zdjęciu ograniczenia 1:1 w #157/#159) `Volteo Kredyt` NIE jest
już 1:1 z `CRM Deal`: jedna szansa może mieć wiele formularzy kredytowych,
każdy jako osobny rekord. Endpointy poniżej są kluczowane po NAZWIE REKORDU
(`kredyt`), nie po `deal`, z dwoma wyjątkami: `volteo_kredyt_lista` (lista
formularzy danej szansy) i `volteo_kredyt_create` (zakłada nowy formularz dla
szansy, patrz strażnik w jego docstringu). Szansa, do której gate'y ról/dostępu
się odnoszą, jest zawsze odczytywana Z REKORDU (`kredyt_doc.deal`), nigdy z
argumentu wywołania: jedynym źródłem prawdy o tym, do której szansy dany
formularz należy, jest sam rekord.

Analogicznie do `Volteo Umowa` (`crm/api/umowa.py`, wzorzec skopiowany
strukturalnie, choć `Volteo Umowa` sama zostaje 1:1). Frontend woła te
endpointy WYŁĄCZNIE pełną kropkowaną ścieżką (`crm.api.kredyt.volteo_kredyt_*`)
— gołe nazwy metod działają tylko dla Server Scriptów, nie dla wywołań
`call()` frontendu na whitelisted API forka (patrz pułapka HTTP 417
udokumentowana przy `Volteo Umowa`/`AudytTab.vue`).

Formularz kredytowy jest wypełniany stopniowo przez przedstawiciela — tak
jak formularz umowy, niekompletny zapis jest poprawnym stanem roboczym
(`status="Roboczy"`), nie błędem; brakujące pola wracają w odpowiedzi, nigdy
nie blokują `volteo_kredyt_save`. Generowanie PDF-u jest tu jednak świadomie
SUROWSZE niż w `Volteo Umowa`: `volteo_kredyt_pdf` odmawia złożenia dokumentu,
dopóki formularz (54 pola podstawowe) i blok wnioskodawcy zapisany NA TYM
REKORDZIE (`wnioskodawca_*`, ops#157/#158, migawka z chwili założenia
formularza, nie aktualna karta `Contact`) nie są komplet: decyzja
właściciela, bo formularz kredytowy trafia do banku/pośrednika i częściowy
wydruk nie ma tam żadnej wartości roboczej.

Kwoty dochodu/zobowiązań (`_POLA_KWOTOWE_DATA`) są celowo polami Data
(string), nie Currency/Float — ten sam powód co gdzie indziej w tym
repozytorium (`None vs 0` w polach liczbowych): na zwykłym doctypie
nieustawiony Float/Currency czyta się jako `0`, nie do odróżnienia od
zadeklarowanego zera (np. „dochód współmałżonka: 0 zł”, co bank musi widzieć
inaczej niż „pole niewypełnione”). Trzymanie ich jako Data eliminuje tę
niejednoznaczność u źródła, kosztem walidacji po stronie serwera przy każdym
zapisie (`kwota_poprawna`/cyfry-only dla `liczba_osob_na_utrzymaniu`) zamiast
polegania na typie kolumny.

Od b47 (decyzja właściciela, 2026-08-17) formularz kredytowy JEST wysyłany do
e-podpisu przez Autenti — endpointy wysyłki/statusu/pobrania żyją w
`crm/integrations/autenti/api.py`, analogicznie do `Volteo Umowa` (od b45).
Co pozostaje celowo nieobsłużone: żadna automatyzacja procesu
(`advance_deal_status`) nie reaguje na podpisanie formularza kredytowego —
w odróżnieniu od umowy, kredyt nie ma własnego etapu w `crm.volteo_pipeline`
i jego podpisanie niczego w statusie szansy nie przesuwa (patrz też komentarz
w `volteo_kredyt_pdf` poniżej).
"""

from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate

from crm.api.umowa import _dane_kontaktu, _podstawowy_kontakt, _sprawdz_dostep_do_szansy, _sprawdz_role
from crm.integrations.autenti import logika as autenti_logika
from crm.permissions.file_nazwy_systemowe import plik_systemowy
from crm.volteo_aktywnosc import etykieta_wnioskodawcy, tekst_sladu, zapisz_slad
from crm.volteo_kredyt import ETYKIETY_POL as _ETYKIETY_POL
from crm.volteo_kredyt import ETYKIETY_WNIOSKODAWCY as _ETYKIETY_WNIOSKODAWCY
from crm.volteo_kredyt import (
	GRUPY_DOCHODU,
	POLA_WNIOSKODAWCY,
	brakujace_dane_wnioskodawcy,
	brakujace_pola,
	kontakt_z_wnioskodawcy,
	kwota_poprawna,
	pasuje_plik_kredytu,
	prefill_z_wnioskodawcy,
)
from crm.volteo_kredyt_pdf import zbuduj_kontekst_kredytu
from crm.volteo_kredyt_render import sciezka_szablonu_kredytu, zloz_kredyt
from crm.volteo_pipeline import OZE_RODZAJE

DOCTYPE = "Volteo Kredyt"

_DANE_POLA_PODSTAWOWE = [
	"miejsce_urodzenia",
	"rodzaj_dokumentu",
	"seria_numer_dokumentu",
	"data_wydania_dokumentu",
	"data_waznosci_dokumentu",
	"adres_zameldowania_taki_sam",
	"adres_zameldowania",
	"adres_korespondencji_taki_sam",
	"adres_korespondencji",
	"wyksztalcenie",
	"stan_cywilny",
	"liczba_osob_na_utrzymaniu",
	"kwota_800_plus",
	"dochod_wspolmalzonka",
	"zrodlo_dochodu_malzonka",
	"oplaty_miesieczne",
	"suma_zobowiazan",
	"numer_rachunku",
	"praca_wlaczone",
	"praca_forma",
	"praca_data_zatrudnienia",
	"praca_okres",
	"praca_okres_od",
	"praca_okres_do",
	"praca_nip",
	"praca_nazwa_zakladu",
	"praca_adres_telefon",
	"praca_kwota_dochodu",
	"emerytura_wlaczone",
	"emerytura_numer_swiadczenia",
	"emerytura_od_kiedy",
	"emerytura_kwota_dochodu",
	"renta_wlaczone",
	"renta_numer_swiadczenia",
	"renta_od_kiedy",
	"renta_kwota_dochodu",
	"dzialalnosc_wlaczone",
	"dzialalnosc_forma_opodatkowania",
	"dzialalnosc_forma_inna",
	"dzialalnosc_nip",
	"dzialalnosc_nazwa",
	"dzialalnosc_adres",
	"dzialalnosc_telefon",
	"dzialalnosc_od_kiedy",
	"dzialalnosc_kwota_dochodu",
	"gospodarstwo_wlaczone",
	"gospodarstwo_nip",
	"gospodarstwo_od_kiedy",
	"gospodarstwo_kwota_dochodu",
	"inne_wlaczone",
	"inne_1_typ",
	"inne_1_kwota",
	"inne_2_typ",
	"inne_2_kwota",
]
"""54 pola danych `Volteo Kredyt` sprzed ops#157/#158, bez bloku wnioskodawcy.

Osobno od pełnej allowlisty (`_DANE_POLA_DOZWOLONE` niżej), bo strażnik
"formularz nietknięty" w `volteo_kredyt_create` (patrz `_formularz_nietkniety`)
i liczenie `brakujace_pola`/`status` MUSZĄ patrzeć wyłącznie na te 54 pola:
blok `wnioskodawca_*` jest wypełniany przez prefill od razu przy założeniu
formularza, więc strażnik zbudowany na jego pustości nigdy by nie zadziałał
(ops#158), a kompletność formularza (status Roboczy/Kompletny) była i zostaje
liczona wyłącznie z tych 54 pól. Kompletność danych wnioskodawcy ma osobny,
odrębny sygnał (`brakujace_dane_wnioskodawcy`, blokuje tylko PDF)."""

_DANE_POLA_DOZWOLONE = [*_DANE_POLA_PODSTAWOWE, *POLA_WNIOSKODAWCY]
"""Jedyne pola `Volteo Kredyt`, jakie `volteo_kredyt_save` przyjmuje od klienta:
54 pola podstawowe (`_DANE_POLA_PODSTAWOWE`) plus 10 pól wnioskodawcy
(`crm.volteo_kredyt.POLA_WNIOSKODAWCY`, ops#157/#158). Kanon kolejności i
nazw pól wnioskodawcy żyje WYŁĄCZNIE w `crm.volteo_kredyt`, tu tylko domieszany.

Nigdy nie robimy ślepego `doc.update(dane)` z danych przesłanych przez
przeglądarkę — wszystko spoza tej listy jest po cichu odrzucane. `deal` i
`status` są tu celowo NIEOBECNE: `deal` ustala wyłącznie `volteo_kredyt_create`
(przez `frappe.get_doc({"doctype": ..., "deal": deal, ...})`, nazwa dokumentu
jest teraz hashem generowanym przez Frappe, NIE nazwą szansy, ops#159),
`status` liczy wyłącznie serwer z `brakujace_pola` po każdym zapisie, klient
nie może żadnego z nich nadpisać.
"""

_POLA_CHECKBOX = frozenset(
	{
		"praca_wlaczone",
		"emerytura_wlaczone",
		"renta_wlaczone",
		"dzialalnosc_wlaczone",
		"gospodarstwo_wlaczone",
		"inne_wlaczone",
	}
)
"""Sześć przełączników źródeł dochodu (pola Check, 0/1 Int) — koercja WYŁĄCZNIE
przez `cint`, nigdy `bool()`. Pułapka: `bool("0")` daje `True` w Pythonie, więc
string `"0"` przepuszczony bez koercji zapisałby się jako źródło włączone,
mimo że przedstawiciel go nie zaznaczył (ten sam błąd, którego unika
`Volteo Umowa` dla swoich pól zgody — patrz `crm/api/umowa.py`).
"""

_POLA_DATY = frozenset(
	{
		"data_wydania_dokumentu",
		"data_waznosci_dokumentu",
		"praca_data_zatrudnienia",
		"praca_okres_od",
		"praca_okres_do",
		"emerytura_od_kiedy",
		"renta_od_kiedy",
		"dzialalnosc_od_kiedy",
		"gospodarstwo_od_kiedy",
	}
)
"""Pola Date formularza — puste wejście (`None`/`""`) zapisuje się jako `None`,
niepuste jest walidowane przez `getdate` (rzuca czytelny komunikat po polsku
przy niepoprawnej dacie zamiast pozwolić Frappe wywalić się gołym wyjątkiem
frameworka przy `.save()`). `praca_okres_od`/`praca_okres_do` SĄ tu: to
kalendarzowe daty początku/końca umowy o pracę na czas określony — `praca_okres`
(Select) tylko wybiera, które z nich mają zastosowanie, nie zmienia ich typu.
"""

_POLA_KWOTOWE_DATA = frozenset(
	{
		"liczba_osob_na_utrzymaniu",
		"kwota_800_plus",
		"dochod_wspolmalzonka",
		"oplaty_miesieczne",
		"suma_zobowiazan",
		"praca_kwota_dochodu",
		"emerytura_kwota_dochodu",
		"renta_kwota_dochodu",
		"dzialalnosc_kwota_dochodu",
		"gospodarstwo_kwota_dochodu",
		"inne_1_kwota",
		"inne_2_kwota",
	}
)
"""Pola Data (string) niosące kwoty/liczby — patrz akapit o `None vs 0` w
docstringu modułu. Niepuste wartości muszą przejść `kwota_poprawna` (Decimal
parsowalny), poza `liczba_osob_na_utrzymaniu`, gdzie liczba osób wymaga
sprawdzenia cyfry-only (`_pole_kwotowe_poprawne` niżej) — dziesiętne „2.5
osoby” nie ma sensu, mimo że jako kwota parsowałoby się poprawnie.
"""

# `_ETYKIETY_POL` (import u góry pliku, `crm.volteo_kredyt.ETYKIETY_POL`) to
# JEDYNY kanon etykiet PL dla WSZYSTKICH pól `_DANE_POLA_DOZWOLONE`: nadzbiór
# tego, co `crm.volteo_kredyt.brakujace_pola` może kiedykolwiek zwrócić, żeby
# komunikat blokujący PDF (`volteo_kredyt_pdf`) zawsze miał czytelną nazwę
# pola, nawet gdy zbiór pól wymaganych przez rdzeń się zmieni. Ten moduł go
# nie definiuje: przepisywanie etykiet lokalnie tutaj (osobno od Desku i
# frontendu) było źródłem ops#148 (K5/K6/K17). Etykiety różniły się między
# frontem, tym plikiem, doctype'em i papierowym szablonem PDF-u. Zmiana
# etykiety idzie WYŁĄCZNIE do `crm/volteo_kredyt.py::ETYKIETY_POL` (i do jego
# odpowiednika po stronie JS, `frontend/src/utils/kredytForm.js`), nigdy tu.

# Od ops#158 nie ma tu już osobnego `_PREFILL_ETYKIETY`: kompletność bloku
# wnioskodawcy przy generowaniu PDF-u (`volteo_kredyt_pdf`) jest sprawdzana
# przez `crm.volteo_kredyt.brakujace_dane_wnioskodawcy`, a etykiety do
# komunikatu błędu czyta z `_ETYKIETY_WNIOSKODAWCY` (import u góry pliku,
# `crm.volteo_kredyt.ETYKIETY_WNIOSKODAWCY`), ten sam kanon, który jest już
# domieszany do `_ETYKIETY_POL`. Dawniej to pole sprawdzało dane KONTAKTU
# PODSTAWOWEGO szansy (`_kontakt_surowy_i_prefill`); teraz formularz jest
# migawką zapisaną NA REKORDZIE (`wnioskodawca_*`), nie podąża już za kartą
# kontaktu, więc sprawdzenie kompletności patrzy na rekord, nie na `Contact`.


def _sprawdz_rodzaj_oze(deal_doc: "frappe.model.document.Document") -> None:
	"""Formularz kredytowy dotyczy wyłącznie linii OZE — `custom_rodzaj_umowy` szansy
	musi być jedną z wartości `crm.volteo_pipeline.OZE_RODZAJE`. Czyste Powietrze ma
	własny, odrębny proces (`PIPELINE_CP`) bez etapu kredytowego, więc dostęp do
	tego formularza dla takiej szansy jest błędem danych szansy, nie stanem
	roboczym formularza — stąd osobna, jawna bramka zamiast cichego pustego wyniku.
	"""
	if deal_doc.get("custom_rodzaj_umowy") not in OZE_RODZAJE:
		frappe.throw(
			_(
				"Formularz kredytowy dotyczy wyłącznie linii OZE (Fotowoltaika, "
				"Fotowoltaika + Magazyn, Magazyn energii) — ustaw „Rodzaj umowy” na "
				"szansie sprzedaży na jedną z tych wartości."
			)
		)


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd formularza")
	frappe.throw(_("Wystąpił błąd podczas zapisu formularza kredytowego."))


def _blad_generowania_pdf() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd generowania PDF")
	frappe.throw(_("Wystąpił błąd podczas generowania PDF-u formularza kredytowego. Spróbuj ponownie."))


def _blad_brakujacego_szablonu() -> NoReturn:
	"""Wbudowany szablon PDF-u (`crm/szablony/formularz_kredytowy.pdf`) nie wczytał
	się z dysku. To awaria WDROŻENIA (plik nie trafił do obrazu albo jest
	uszkodzony), nie błąd użytkownika ani danych szansy — patrz analogiczny
	komunikat w `crm.api.umowa._blad_brakujacego_szablonu`.
	"""
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: brak wbudowanego szablonu PDF")
	frappe.throw(
		_("Szablon PDF-u formularza kredytowego nie jest dostępny w tej instalacji. Skontaktuj się z administratorem systemu.")
	)


def _blad_zapisu_pliku() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd zapisu pliku PDF")
	frappe.throw(_("PDF wygenerowano, ale nie udało się go zapisać. Spróbuj ponownie."))


def _pobierz_kredyt(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca dokument `Volteo Kredyt` dla szansy, jeśli istnieje pod nazwą TOŻSAMĄ
	z `deal`, inaczej `None`.

	LEGACY, deal-keyed: poprawne tylko dla rekordów sprzed ops#159 (`autoname:
	field:deal`, `kredyt_name == deal`, dokładnie jeden formularz na szansę).
	Od ops#158/#159 to już nie jest ogólny sposób odczytu formularza: szansa
	może mieć wiele rekordów, żaden hashowy nie nazywa się jak szansa. Wszystkie
	endpointy w TYM pliku czytają teraz po nazwie rekordu, przez
	`_kredyt_po_nazwie` niżej. Ta funkcja zostaje WYŁĄCZNIE dlatego, że
	`crm.integrations.autenti.api` (poza zakresem ops#158, patrz #160) wciąż ją
	importuje po nazwie (`_pobierz_kredyt`, kluczowana po `deal`); usunięcie
	jej tutaj wywaliłoby ten moduł błędem importu. Ten rozjazd jest znany
	orkiestratorowi i sekwencjonowany osobno.
	"""
	if frappe.db.exists(DOCTYPE, deal):
		return frappe.get_doc(DOCTYPE, deal)
	return None


def _kredyt_po_nazwie(kredyt: str) -> "frappe.model.document.Document":
	"""Zwraca dokument `Volteo Kredyt` po NAZWIE REKORDU, albo rzuca czytelny błąd
	(analog HTTP 404), gdy nie istnieje. Jedyny sposób odczytu formularza od
	ops#158, odkąd jedna szansa może mieć wiele rekordów i `deal` przestał
	jednoznacznie wskazywać "ten jeden" formularz.
	"""
	if not kredyt or not frappe.db.exists(DOCTYPE, kredyt):
		frappe.throw(_("Formularz kredytowy nie istnieje."), frappe.DoesNotExistError)
	return frappe.get_doc(DOCTYPE, kredyt)


def _kontakt_surowy_i_prefill(
	deal_doc: "frappe.model.document.Document",
) -> tuple[dict[str, Any], dict[str, Any]]:
	"""Jedno wywołanie `_dane_kontaktu` kontaktu podstawowego szansy, zwracające PARĘ
	(surowy słownik, re-keyed `prefill`) z TEGO SAMEGO odczytu — reużywa
	`crm.api.umowa._podstawowy_kontakt`/`_dane_kontaktu` (spacer po kontaktach szansy
	+ odczyt `Contact Email`/`Contact Phone`) zamiast duplikować tę logikę.

	Dwa niezależne wywołania `_dane_kontaktu` (jedno dla `prefill`, drugie dla
	kontekstu PDF-u) mogłyby się rozjechać — stąd jeden odczyt, dwa kształty z
	niego wyprowadzone. Surowy słownik ma klucze `_dane_kontaktu`
	(`custom_pesel`, `first_name`, `last_name`, `mobile_no`, `email`,
	`custom_kod_pocztowy`, `custom_miasto`, `custom_ulica`, `custom_nr_domu`,
	`custom_nr_mieszkania`) — to kształt, jakiego oczekuje
	`crm.volteo_kredyt_pdf.zbuduj_kontekst_kredytu`. `prefill` jest re-keyed na
	nazwy pól formularza kredytowego (`pesel`, `imiona`, `nazwisko`, ...) — to
	kształt, jakiego oczekuje przeglądarka i bramka kompletności kontaktu.
	Mylenie tych dwóch kształtów to klasa błędu prefill-keying z 2026-08-05,
	zaobserwowana ponownie na tym szwie sondą e2e 2026-08-15: przekazanie
	re-keyed `prefill` zamiast surowego słownika do `zbuduj_kontekst_kredytu`
	dawało pusty kontekst kontaktu w PDF-ie poza `email` — jedynym kluczem
	wspólnym obu kształtów.
	"""
	kontakt = _podstawowy_kontakt(deal_doc)
	surowe = _dane_kontaktu(kontakt)
	prefill = {
		"pesel": surowe.get("custom_pesel") or "",
		"imiona": surowe.get("first_name") or "",
		"nazwisko": surowe.get("last_name") or "",
		"telefon": surowe.get("mobile_no") or "",
		"email": surowe.get("email") or "",
		"kod_pocztowy": surowe.get("custom_kod_pocztowy") or "",
		"miejscowosc": surowe.get("custom_miasto") or "",
		"ulica": surowe.get("custom_ulica") or "",
		"nr_domu": surowe.get("custom_nr_domu") or "",
		"nr_lokalu": surowe.get("custom_nr_mieszkania") or "",
	}
	return surowe, prefill


def _prefill(deal_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Składa blok `prefill`: dane kontaktu podstawowego szansy, wyłącznie do
	odczytu przez zakładkę (formularz kredytowy nigdy nie zapisuje z powrotem
	do `Contact`). Cienki wrapper nad `_kontakt_surowy_i_prefill` — wywołujący,
	którym nie zależy na surowym kształcie (np. `volteo_kredyt_get/create/save`),
	dostaje tylko `prefill`.
	"""
	_, prefill = _kontakt_surowy_i_prefill(deal_doc)
	return prefill


def _kredyt_do_dict(kredyt_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Spłaszcza dokument `Volteo Kredyt` do bloku `kredyt` odpowiedzi."""
	wynik = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE}
	wynik["name"] = kredyt_doc.name
	wynik["deal"] = kredyt_doc.deal
	wynik["status"] = kredyt_doc.status
	return wynik


def _data_lub_none(pole: str, wartosc: Any) -> Any:
	"""Konwertuje wejście Date na coś, co `Document.set` przyjmie — puste wejście
	(`None`/`""`) daje `None` (pole czyszczone), niepuste jest walidowane przez
	`getdate`, rzucając czytelny komunikat po polsku zamiast surowego wyjątku
	frameworka przy `.save()`.
	"""
	if wartosc is None or wartosc == "":
		return None
	try:
		return getdate(wartosc)
	except Exception:
		frappe.throw(_("Nieprawidłowa data w polu „{0}”.").format(_ETYKIETY_POL.get(pole, pole)))


def _pole_kwotowe_poprawne(pole: str, tekst: str) -> bool:
	"""`liczba_osob_na_utrzymaniu` to LICZBA osób (cyfry-only), nie kwota — reszta
	pól `_POLA_KWOTOWE_DATA` idzie przez `kwota_poprawna` (Decimal parsowalny).
	"""
	if pole == "liczba_osob_na_utrzymaniu":
		return tekst.isdigit()
	return kwota_poprawna(tekst)


def _wyczysc_nieaktywne_grupy_dochodu(kredyt_doc: "frappe.model.document.Document") -> None:
	"""Obrona w głąb: dla każdego przełącznika `GRUPY_DOCHODU`, który jest
	WYŁĄCZONY po zastosowaniu allowlisty, czyści (`None`) wszystkie pola jego
	grupy na dokumencie. Bez tego nieaktualny payload przeglądarki (np. stara
	karta z otwartym formularzem, w której rep odznaczył „Emerytura” już PO
	stronie klienta, ale request zawierał tylko zmienione pole przełącznika)
	mógłby zostawić martwe dane dochodowe źródła, które użytkownik jawnie wyłączył.
	"""
	for przelacznik, pola_grupy in GRUPY_DOCHODU.items():
		if not cint(kredyt_doc.get(przelacznik)):
			for pole_grupy in pola_grupy:
				kredyt_doc.set(pole_grupy, None)


def _pole_puste(wartosc: Any) -> bool:
	"""Reguła pustości identyczna do `crm.volteo_kredyt._jest_puste` (funkcja
	prywatna tamtego modułu, celowo zduplikowana lokalnie zamiast importowana
	po nazwie z podkreślnikiem przez granicę modułów): `None`/`""`/sam biały
	znak są puste, wszystko inne (włącznie z `"0"`) jest wypełnione. Nigdy nie
	rzuca."""
	if wartosc is None:
		return True
	if isinstance(wartosc, str):
		return wartosc.strip() == ""
	return False


def _formularz_nietkniety(kredyt_doc: "frappe.model.document.Document") -> bool:
	"""Czy formularz jest NIETKNIĘTY: wszystkie 54 pola `_DANE_POLA_PODSTAWOWE` są
	puste (blok `wnioskodawca_*` SIĘ NIE LICZY: prefill wypełnia go od razu
	przy założeniu formularza, więc strażnik zbudowany na jego pustości nigdy
	by nie zadziałał, ops#158).

	Sześć pól-przełączników (`_POLA_CHECKBOX`) są typu Check (Int 0/1). Na
	zwykłym doctypie nieustawiony Int czyta się jako `0`, NIE `None` (patrz
	"None vs 0" w CLAUDE.md), więc `_pole_puste(0)` dałoby fałszywe "wypełnione"
	dla każdego świeżo założonego rekordu i strażnik nigdy nie zwracałby prawdy.
	Dla tych sześciu pól "puste" znaczy więc "fałszywe po `cint`", nie
	"`None`/pusty string".
	"""
	for pole in _DANE_POLA_PODSTAWOWE:
		wartosc = kredyt_doc.get(pole)
		if pole in _POLA_CHECKBOX:
			if cint(wartosc):
				return False
		elif not _pole_puste(wartosc):
			return False
	return True


def _odpowiedz_kredytu(
	kredyt_doc: "frappe.model.document.Document", deal_doc: "frappe.model.document.Document"
) -> dict[str, Any]:
	"""Kształt odpowiedzi wspólny dla `volteo_kredyt_create`: `kredyt` + `prefill`
	kontaktu podstawowego szansy (do podglądu przed ewentualnym „Przywróć dane
	klienta”) + `brakujace_pola` (54 pola podstawowe, bez bloku wnioskodawcy)."""
	dane_do_walidacji = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_PODSTAWOWE}
	return {
		"kredyt": _kredyt_do_dict(kredyt_doc),
		"prefill": _prefill(deal_doc),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
	}


def _usun_stare_pliki_kredytu(deal: str, kredyt_name: str) -> None:
	"""Analogiczne do `crm.api.umowa._usun_stare_pdfy_umowy`: usuwa wcześniejsze
	rekordy `File` z PDF-em formularza kredytowego TEGO KONKRETNEGO rekordu
	`Volteo Kredyt` (`kredyt_name`), nigdy plików INNEGO formularza tej samej
	szansy (ops#158/#159: jedna szansa może mieć wiele rekordów).

	Frappe nie nadpisuje pliku o istniejącej nazwie przy kolejnym `insert()` —
	dokleja losowy sufiks tuż przed rozszerzeniem, więc dopasowanie po
	dokładnej nazwie niczego by nie znalazło po drugim wywołaniu; zamiast tego
	dopasowujemy przez LIKE po prefiksie BAZOWYM szansy (obejmuje pliki
	KAŻDEGO formularza tej szansy, żeby jeden LIKE starczył do pobrania
	kandydatów z bazy), a potem filtrujemy w Pythonie precyzyjnie po kształcie
	nazwy WŁAŚCIWYM dla `kredyt_name` (`crm.volteo_kredyt.pasuje_plik_kredytu`).

	PUŁAPKA (ops#158): prefiks BAZOWY szansy (`Formularz-kredytowy-<deal>`,
	bez sufiksu rekordu) jest jednocześnie ścisłym prefiksem STRINGA nazwy
	pliku KAŻDEGO rodzeństwa hashowego tej samej szansy. Samo dopasowanie
	LIKE złapałoby więc pliki WSZYSTKICH formularzy szansy naraz i dla rekordu
	legacy skasowałoby też pliki formularzy hashowych. Stąd DWA kroki: LIKE
	(szeroki, po samej bazie) plus `pasuje_plik_kredytu` (wąski, po kształcie
	konkretnego rekordu), zob. docstring `pasuje_plik_kredytu` dla pełnego
	opisu obu kształtów (legacy vs hash) i dlaczego rekord hashowy dopasowuje
	WYŁĄCZNIE pliki niosące jego WŁASNY 8-znakowy sufiks, nigdy sufiks innego
	rekordu. Pliki podpisane (`-podpisany.pdf`) wpinają się pod `Volteo Kredyt`,
	nie pod `CRM Deal` (patrz `crm.integrations.autenti.api`), więc filtr
	`attached_to_doctype == "CRM Deal"` niżej ich w ogóle nie widzi: nigdy nie
	są kandydatem do skasowania tutaj.

	Bezpieczeństwo zakresu: filtr LIKE łączy TRZY warunki jednocześnie,
	`attached_to_doctype == "CRM Deal"`, `attached_to_name == deal` (żaden
	załącznik INNEJ szansy nie może zostać złapany) i `file_name LIKE
	"<prefiks bazowy tej szansy>%.pdf"` (inne załączniki TEJ SAMEJ szansy, np.
	PDF umowy, mają inny prefiks nazwy i nie pasują). Znaki `%`/`_` w nazwie
	szansy są eskejpowane, żeby nie działały jako wildcardy LIKE. Wołający
	uruchamia to PRZED insertem nowego pliku, więc świeżo wstawiony plik (jego
	nazwa też pasuje do wzorca) nie istnieje jeszcze w bazie w momencie
	dopasowania i nie może zostać przez pomyłkę skasowany. Nieudane
	sprzątnięcie NIE MOŻE zablokować wygenerowania nowego PDF-u — błąd trafia
	do `frappe.log_error` i przetwarzanie idzie dalej.
	"""
	prefiks_bazowy = autenti_logika.prefiks_pliku_kredytu(deal, deal)
	wzorzec = prefiks_bazowy.replace("%", r"\%").replace("_", r"\_") + "%.pdf"
	kandydaci = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": ["like", wzorzec],
		},
		fields=["name", "file_name"],
	)
	for wiersz in kandydaci:
		if not pasuje_plik_kredytu(wiersz.file_name, prefiks_bazowy, kredyt_name, deal):
			continue
		try:
			frappe.delete_doc("File", wiersz.name, ignore_permissions=True, delete_permanently=True)
		except Exception:
			frappe.log_error(title="volteo_kredyt_pdf: nie udało się usunąć starego pliku PDF formularza kredytowego")


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_kredyt_lista(deal: str) -> dict[str, Any]:
	"""Zwraca listę skrótów formularzy kredytowych DANEJ szansy (ops#158), po
	zdjęciu ograniczenia 1:1 (#157/#159 zdjęły je): jedna szansa może mieć
	wiele rekordów `Volteo Kredyt`.

	Bramki jak `get`: rola kalkulatora + `read` na szansie. Celowo
	`frappe.get_list`, NIGDY `frappe.get_all`: tylko `get_list` przepuszcza
	wynik przez `permission_query_conditions`, więc ewentualny hook widoczności
	rekordów `Volteo Kredyt` (ops#161) działa też tutaj, na liście, nie tylko
	na pojedynczym rekordzie (`get_all` ignoruje uprawnienia, klasyczna
	pułapka safe_exec/Frappe tego projektu, patrz CLAUDE.md).

	Kolejność `creation asc`: formularze w kolejności założenia, najstarszy
	pierwszy, stabilna, przewidywalna kolejność zakładek/listy w UI.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	formularze = frappe.get_list(
		DOCTYPE,
		filters={"deal": deal},
		fields=[
			"name",
			"wnioskodawca_nazwisko",
			"wnioskodawca_imiona",
			"status",
			"autenti_status",
			"creation",
			"modified",
		],
		order_by="creation asc",
		limit_page_length=0,
	)
	return {"formularze": formularze}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_kredyt_get(kredyt: str) -> dict[str, Any]:
	"""Zwraca formularz `Volteo Kredyt` po nazwie rekordu, `prefill` (dane
	wnioskodawcy ZAPISANE NA TYM REKORDZIE, migawka z chwili założenia),
	`prefill_kontakt` (AKTUALNE dane kontaktu podstawowego szansy, osobno, do
	obsługi przycisku „Przywróć dane klienta” bez kolejnego endpointu),
	`brakujace_pola` (54 pola podstawowe) i `brakujace_dane_wnioskodawcy`
	(kompletność bloku wnioskodawcy, patrz `volteo_kredyt_pdf`).

	Celowo BEZ bramki OZE (`_sprawdz_rodzaj_oze`), inaczej niż
	`create`/`save`/`pdf`: jeśli rep przełączy „Rodzaj umowy” szansy na Czyste
	Powietrze podczas gdy zakładka Kredyt jest już otwarta, `get` nadal ma
	zwrócić dane, żeby UI mogło się spokojnie ukryć (stan zakładki), zamiast
	wywalić się błędem na zwykłym odświeżeniu widoku.
	"""
	_sprawdz_role()
	kredyt_doc = _kredyt_po_nazwie(kredyt)
	_sprawdz_dostep_do_szansy(kredyt_doc.deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", kredyt_doc.deal)
	kredyt_dict = _kredyt_do_dict(kredyt_doc)
	dane_do_walidacji = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_PODSTAWOWE}

	return {
		"kredyt": kredyt_dict,
		"prefill": prefill_z_wnioskodawcy(kredyt_dict),
		"prefill_kontakt": _prefill(deal_doc),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
		"brakujace_dane_wnioskodawcy": brakujace_dane_wnioskodawcy(kredyt_dict),
	}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_kredyt_create(deal: str) -> dict[str, Any]:
	"""Tworzy NOWY formularz `Volteo Kredyt` dla szansy, z migawką danych
	wnioskodawcy prefillowaną z kontaktu podstawowego szansy w chwili założenia
	(ops#158, po zdjęciu ograniczenia 1:1 w #157/#159).

	Strażnik przed podwójnym kliknięciem: jeśli na szansie istnieje formularz
	w statusie `Roboczy`, który jest NIETKNIĘTY (wszystkie 54 pola
	`_DANE_POLA_PODSTAWOWE` puste, blok `wnioskodawca_*` SIĘ NIE LICZY, bo
	prefill wypełnia go od razu przy założeniu i strażnik zbudowany na jego
	pustości nigdy by nie zadziałał, patrz `_formularz_nietkniety`), zwraca
	TEN formularz zamiast zakładać kolejny. Handlowiec, który chce naprawdę
	drugi formularz, musi najpierw cokolwiek wpisać w pierwszym.

	Od chwili założenia formularz jest MIGAWKĄ danych wnioskodawcy i nie
	podąża już za kartą kontaktu: naprawia przy okazji cichą wadę sprzed
	ops#158, dawniej edycja karty kontaktu zmieniała treść ponownie
	generowanego PDF-u, także dla formularza już wysłanego do banku.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	istniejace_robocze = frappe.get_list(
		DOCTYPE,
		filters={"deal": deal, "status": "Roboczy"},
		fields=["name"],
		order_by="creation asc",
		limit_page_length=0,
	)
	for wiersz in istniejace_robocze:
		kandydat = frappe.get_doc(DOCTYPE, wiersz.name)
		if _formularz_nietkniety(kandydat):
			return _odpowiedz_kredytu(kandydat, deal_doc)

	_, prefill = _kontakt_surowy_i_prefill(deal_doc)
	kredyt_doc = frappe.get_doc({"doctype": DOCTYPE, "deal": deal, "status": "Roboczy"})
	for klucz, wartosc in prefill.items():
		kredyt_doc.set(f"wnioskodawca_{klucz}", wartosc)

	try:
		# Nie ma tu już łapania `frappe.DuplicateEntryError` po wyścigu insertów:
		# to zabezpieczenie miało sens wyłącznie przy dawnym `autoname:
		# field:deal` (nazwa dokumentu = nazwa szansy, więc dwa równoległe
		# wstawienia dla TEJ SAMEJ szansy naprawdę mogły kolidować na nazwie).
		# Od ops#159 nazwa rekordu jest generowana przez Frappe jako hash:
		# kolizja nazwy między dwoma NOWYMI rekordami jest praktycznie
		# niemożliwa, więc łapanie tego wyjątku tutaj byłoby martwym kodem.
		kredyt_doc.insert()
	except Exception:
		_blad_ogolny()

	try:
		# ops#162: etykieta wnioskodawcy w tekście śladu odróżnia formularze,
		# gdy na jednej szansy powstaje ich więcej niż jeden (ops#157/#159
		# zdjęło ograniczenie 1:1); dane biorą się z MIGAWKI zapisanej na
		# `kredyt_doc` chwilę wcześniej (prefill), nie z aktualnej karty kontaktu.
		etykieta = etykieta_wnioskodawcy(
			kredyt_doc.get("wnioskodawca_nazwisko"), kredyt_doc.get("wnioskodawca_imiona")
		)
		zapisz_slad(deal, tekst_sladu("kredyt_utworzono", wnioskodawca=etykieta))
	except Exception:
		# Ślad w Aktywności to wygoda, nie warunek sukcesu: awaria zapisu
		# śladu nie może cofnąć ani zablokować już utworzonego rekordu kredytu.
		frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd zapisu śladu utworzenia")

	return _odpowiedz_kredytu(kredyt_doc, deal_doc)


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_kredyt_save(kredyt: str, dane: dict[str, Any]) -> dict[str, Any]:
	"""Zapisuje formularz kredytowy (po nazwie rekordu) z allowlistą pól i koercją
	typów.

	Niekompletny zapis jest poprawnym stanem roboczym (przedstawiciel wypełnia
	formularz stopniowo) — brakujące pola NIE blokują zapisu, tylko ustawiają
	`status="Roboczy"` i trafiają do odpowiedzi, żeby UI mógł je podświetlić.
	Dopiero komplet DANYCH PODSTAWOWYCH (54 pól, bez bloku wnioskodawcy) daje
	`status="Kompletny"`. Kompletność wnioskodawcy ma osobny sygnał
	(`brakujace_dane_wnioskodawcy`, sprawdzany dopiero przy `volteo_kredyt_pdf`).
	Blokada PDF-u dotyczy wyłącznie generowania, nie zapisu.
	"""
	_sprawdz_role()
	kredyt_doc = _kredyt_po_nazwie(kredyt)
	deal = kredyt_doc.deal
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	if not isinstance(dane, dict):
		frappe.throw(_("Nieprawidłowy format danych formularza."))

	for pole in _DANE_POLA_DOZWOLONE:
		if pole not in dane:
			continue
		wartosc = dane[pole]
		if pole in _POLA_CHECKBOX:
			# Jawna koercja przez cint — NIGDY bool(), bo bool("0") == True w Pythonie.
			wartosc = cint(wartosc)
		elif pole in _POLA_DATY:
			wartosc = _data_lub_none(pole, wartosc)
		elif pole in _POLA_KWOTOWE_DATA:
			tekst = "" if wartosc is None else str(wartosc).strip()
			if tekst and not _pole_kwotowe_poprawne(pole, tekst):
				frappe.throw(_("Nieprawidłowa wartość w polu „{0}”.").format(_ETYKIETY_POL.get(pole, pole)))
			wartosc = tekst
		elif pole in POLA_WNIOSKODAWCY:
			# Pola wnioskodawcy (ops#157/#158), czysty Data, bez koercji poza
			# strip: żadna z pozostałych trzech gałęzi (checkbox/data/kwota) tu
			# nie pasuje.
			wartosc = "" if wartosc is None else str(wartosc).strip()
		kredyt_doc.set(pole, wartosc)

	_wyczysc_nieaktywne_grupy_dochodu(kredyt_doc)

	braki = brakujace_pola({pole: kredyt_doc.get(pole) for pole in _DANE_POLA_PODSTAWOWE})
	kredyt_doc.status = "Roboczy" if braki else "Kompletny"

	try:
		kredyt_doc.save()
	except Exception:
		_blad_ogolny()

	kredyt_dict = _kredyt_do_dict(kredyt_doc)
	return {
		"kredyt": kredyt_dict,
		"prefill": prefill_z_wnioskodawcy(kredyt_dict),
		"prefill_kontakt": _prefill(deal_doc),
		"brakujace_pola": braki,
		"brakujace_dane_wnioskodawcy": brakujace_dane_wnioskodawcy(kredyt_dict),
	}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def volteo_kredyt_pdf(kredyt: str) -> dict[str, Any]:
	"""Generuje PDF formularza kredytowego (po nazwie rekordu) i zapisuje go jako
	prywatny plik podpięty do `CRM Deal`. Zwraca `{"file_url": ..., "file_name": ...}`.

	W odróżnieniu od `volteo_umowa_pdf` (który generuje niekompletny PDF bez
	blokady — dokument jest roboczy, wracany do edycji), generowanie tutaj jest
	CELOWO zablokowane, dopóki: (1) formularz `Volteo Kredyt` nie ma żadnych
	brakujących pól wg `crm.volteo_kredyt.brakujace_pola` (54 pola podstawowe),
	i (2) blok wnioskodawcy zapisany NA TYM REKORDZIE (`wnioskodawca_*`) nie ma
	braków wg `crm.volteo_kredyt.brakujace_dane_wnioskodawcy`. Decyzja
	właściciela: ten PDF trafia do banku/pośrednika kredytowego, więc
	częściowy wydruk nie ma tam żadnej wartości roboczej. Od ops#158 to
	sprawdzenie patrzy na dane ZAPISANE NA FORMULARZU (migawka z chwili
	założenia), nie na aktualną kartę `Contact`: formularz już wysłany do
	banku nie może po cichu zmienić treści wraz z edycją karty kontaktu.

	Proces OZE (`crm.volteo_pipeline.PIPELINE_OZE`) nie ma etapu „Kredyt” —
	w odróżnieniu od `volteo_umowa_pdf` ten endpoint celowo NIE wywołuje
	`crm.api.pipeline.advance_deal_status`: wygenerowanie formularza kredytowego
	nie przesuwa szansy w procesie.

	Uprawnienia: rola kalkulatora + `write` na szansie (SEC#35 — było `read`:
	generowanie mimo braku zaawansowania statusu i tak wstawia i kasuje pliki
	`File` podpięte do szansy z `ignore_permissions=True`, więc `read` był
	niewystarczającą bramką dla mutującego endpointu).
	"""
	_sprawdz_role()
	kredyt_doc = _kredyt_po_nazwie(kredyt)
	deal = kredyt_doc.deal
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	# Formularz wysłany do podpisu (albo już podpisany) nie może zostać po cichu
	# podmieniony nowym PDF-em, analogicznie do `volteo_umowa_pdf`: (a) bajty
	# pokazane klientowi w podglądzie muszą zostać identyczne z bajtami wysłanymi
	# do podpisu, i (b) to jednocześnie chroni sam wysłany plik przed
	# `_usun_stare_pliki_kredytu` niżej, która sprząta tylko przy generowaniu
	# PDF-u — skasowanie lokalnego pliku źródłowego NIE zepsułoby samego procesu
	# podpisu (Autenti dostaje bajty PDF-u przy wysyłce i już do naszego URL-a
	# pliku nie wraca, a podpisany dokument pobieramy z Autenti, nie z naszego
	# pliku), ale zniszczyłoby nasze lokalne archiwum dokładnie tego, co zostało
	# wysłane do podpisu — bramka utrzymuje ten zapis bajt w bajt.
	# `kredyt_doc.get("autenti_status")` zwraca `None`, gdy Custom Field jeszcze
	# nie istnieje (przed wdrożeniem schematu) — `None` nie jest w
	# `SEND_BLOCKED_STATUSES`, więc to bezpieczne względem kolejności wdrożenia
	# bez dodatkowej bramki.
	if kredyt_doc.get("autenti_status") in autenti_logika.SEND_BLOCKED_STATUSES:
		frappe.throw(
			_(
				"Formularz kredytowy jest w trakcie podpisywania lub został podpisany — "
				"nie można wygenerować nowego PDF-u."
			)
		)

	kredyt_dict = _kredyt_do_dict(kredyt_doc)

	braki = brakujace_pola({pole: kredyt_doc.get(pole) for pole in _DANE_POLA_PODSTAWOWE})
	if braki:
		etykiety = ", ".join(_ETYKIETY_POL.get(pole, pole) for pole in braki)
		frappe.throw(_("Formularz kredytowy jest niekompletny — uzupełnij pola: {0}.").format(etykiety))

	brakujace_wnioskodawcy = brakujace_dane_wnioskodawcy(kredyt_dict)
	if brakujace_wnioskodawcy:
		etykiety = ", ".join(_ETYKIETY_WNIOSKODAWCY.get(pole, pole) for pole in brakujace_wnioskodawcy)
		frappe.throw(
			_("Dane wnioskodawcy są niekompletne, uzupełnij pola: {0}.").format(etykiety)
		)

	try:
		szablon_pdf = sciezka_szablonu_kredytu().read_bytes()
	except OSError:
		_blad_brakujacego_szablonu()

	try:
		# `kontakt` MUSI być surowym słownikiem (klucze custom_pesel/first_name/
		# last_name/mobile_no/email/custom_kod_pocztowy/custom_miasto/custom_ulica/
		# custom_nr_domu/custom_nr_mieszkania), NIE re-keyed `prefill`
		# (pesel/imiona/nazwisko/...), klasa błędu prefill-keying z 2026-08-05/
		# 2026-08-15: re-keyed prefill daje pusty kontakt w PDF-ie poza `email`
		# (jedyny wspólny klucz). Od ops#158 ten surowy kształt pochodzi z
		# `kontakt_z_wnioskodawcy(kredyt_dict)`, z REKORDU formularza (migawka
		# wnioskodawcy), nie z aktualnej karty `Contact`, patrz docstring funkcji.
		kontekst = zbuduj_kontekst_kredytu(
			kredyt=kredyt_dict,
			kontakt=kontakt_z_wnioskodawcy(kredyt_dict),
			dzis=getdate(),
		)
		pdf_bytes = zloz_kredyt(kontekst, szablon_pdf)
	except Exception:
		_blad_generowania_pdf()

	# Nazwa MUSI zawierać znacznik czasu generacji — w odróżnieniu od
	# `autenti_logika.nazwa_pliku_kredytu`, która celowo ma STAŁĄ nazwę (bez
	# znacznika czasu), bo to właśnie ta stała nazwa jest dzielona z Autenti
	# (wysyłka do e-podpisu odwołuje się do tego samego URL-a). Ten lokalnie
	# generowany plik (poniżej) nie ma tego ograniczenia, a stała nazwa okazała
	# się realnym defektem zanim Autenti wszedł do gry: zmierzony nagłówek
	# odpowiedzi pliku to `Cache-Control: private,max-age=3600,stale-while-
	# revalidate=86400`, więc pod STAŁYM URL-em przeglądarka przez godzinę
	# serwowała pierwszy wygenerowany render mimo poprawnie przeliczonego,
	# świeżego pliku po stronie backendu — właściciel zgłosił to jako "ponowne
	# Generuj PDF pokazuje stary dokument" (sonda 2026-08-15). Prefiks sam w
	# sobie (bez znacznika czasu) pochodzi z `autenti_logika.prefiks_pliku_kredytu`,
	# WOŁANY TU DLA TEGO KONKRETNEGO REKORDU (`deal`, `kredyt_doc.name`).
	# JEDYNE źródło prawdy dzielone też ze sprzątaniem starych plików niżej
	# i z wyszukiwaniem pliku źródłowego przy wysyłce do Autenti.
	prefiks_nazwy = autenti_logika.prefiks_pliku_kredytu(deal, kredyt_doc.name)
	nazwa_pliku = f"{prefiks_nazwy}-{frappe.utils.now_datetime().strftime('%Y%m%d-%H%M%S')}.pdf"
	# Sprzątanie idzie PRZED insertem nowego pliku (niżej) i usuwa WYŁĄCZNIE
	# pliki TEGO REKORDU (`kredyt_doc.name`), nigdy plików INNEGO formularza tej
	# samej szansy: patrz docstring `_usun_stare_pliki_kredytu` (ops#158) dla
	# pełnego opisu pułapki prefiksu współdzielonego przez rodzeństwo. Jeszcze
	# nieistniejący `nazwa_pliku` (wstawiany dopiero niżej) pasowałby do wzorca
	# tego samego rekordu, ale kolejność, sprzątanie przed insertem,
	# gwarantuje, że go nie skasuje.
	_usun_stare_pliki_kredytu(deal, kredyt_doc.name)
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
		# ops#162: patrz analogiczny komentarz przy "kredyt_utworzono" powyżej;
		# `kredyt_doc` tutaj jest tym samym rekordem, dla którego wygenerowano PDF.
		etykieta = etykieta_wnioskodawcy(
			kredyt_doc.get("wnioskodawca_nazwisko"), kredyt_doc.get("wnioskodawca_imiona")
		)
		zapisz_slad(deal, tekst_sladu("kredyt_pdf", wnioskodawca=etykieta))
	except Exception:
		# Ślad w Aktywności to wygoda, nie warunek sukcesu — awaria zapisu śladu
		# nie może cofnąć ani zablokować już zapisanego pliku PDF.
		frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd zapisu śladu PDF")

	return {"file_url": plik.file_url, "file_name": plik.file_name}
