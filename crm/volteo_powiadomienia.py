# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Powiadomienia mailowe/dzwonkowe o przydziale leada i o zmianie terminu spotkania (ops#182).

Moduł celowo nie importuje ``frappe`` na poziomie modułu, wzorem
``crm/volteo_aktywnosc.py`` i ``crm/volteo_naming.py``: to jedyny sposób, żeby dało się
go przetestować lokalnie (``frappe`` nie jest instalowalne na tej maszynie). Jedyne
dwa miejsca w pliku, które dotykają Frappe, to ``wzbogac_notification_log`` i
``powiadom_o_zmianie_terminu``, oba z lokalnym ``import frappe`` w ciele funkcji.

Stan sprzed tego modułu (patrz opis w issue ops#182): mail o przydziale leada szedł
w całości z rdzenia Frappe (``frappe.desk.form.assign_to`` -> ``Notification Log`` ->
``send_notification_email``) - bez terminu spotkania, z linkiem do Desku zamiast do
``/crm/leads/<name>`` i z wyciekiem nazwiska CC do handlowca w temacie maila. Ten
moduł dopisuje własną treść na haku ``Notification Log.before_insert``. Kolejność jest
istotna: ``Document.run_method`` woła NAJPIERW własny kontroler doctype'u (tu:
``NotificationLog.before_insert``, który kopiuje ``subject`` -> ``title`` i
``email_content`` -> ``description``), a DOPIERO POTEM haki ``doc_events`` tego
samego eventu (zweryfikowane na lokalnym kontenerze, Frappe 15.118) - czyli
kopiowanie już się wydarzyło, zanim nasz hak w ogóle zacznie działać. Dlatego
``wzbogac_notification_log`` nadpisuje wszystkie cztery pola naraz (``subject``,
``title``, ``email_header``, ``email_content``, ``description``), zamiast liczyć na
to, że zdąży przed kopiowaniem. Moduł dokłada też osobne powiadomienie o zmianie
terminu, którego rdzeń w ogóle nie generuje.

Wszystkie funkcje budujące treść są immutable: zwracają nowe struktury (dict/str),
nigdy nie mutują argumentów wejściowych (`lead` w szczególności).
"""

import datetime
import html
from urllib.parse import quote_plus

from crm.volteo_aktywnosc import AUTOR_ZASTEPCZY_CC

DNI_TYGODNIA: tuple[str, ...] = (
	"poniedziałek",
	"wtorek",
	"środa",
	"czwartek",
	"piątek",
	"sobota",
	"niedziela",
)
"""Pełne nazwy dni tygodnia, indeks 0 = poniedziałek (zgodnie z `datetime.date.weekday()`)."""

DNI_KROTKO: tuple[str, ...] = ("pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz.")
"""Skrócone nazwy dni tygodnia używane w temacie maila (`formatuj_termin`'s trzeci element)."""

MIESIACE_DOPELNIACZ: tuple[str, ...] = (
	"stycznia",
	"lutego",
	"marca",
	"kwietnia",
	"maja",
	"czerwca",
	"lipca",
	"sierpnia",
	"września",
	"października",
	"listopada",
	"grudnia",
)
"""Nazwy miesięcy w dopełniaczu ("25 września"), indeks 0 = styczeń."""

ETYKIETY_PRODUKTOW: dict[str, str] = {
	"PV": "Fotowoltaika",
	"ME": "Magazyn energii",
	"PC": "Pompa ciepła",
	"PP": "Piec",
	"AUDYT": "Audyt",
	"TERMO": "Termomodernizacja",
	"REKU": "Rekuperacja",
	"OKNA": "Okna",
	"GRUNT": "Grunt pod farmę",
}
"""Kanoniczny słownik tokenów produktowych (`custom_posiadane_produkty` na `CRM Lead`,
tokeny sklejone "+") -> etykieta po polsku. Nieznany token zostaje bez zmian,
patrz `nazwy_produktow`."""

KOLOR_MARKI = "#f97316"
"""Kolor akcentu maila (lewa krawędź bloku spotkania, przycisk) - pomarańcz marki
ProEnergy, inline w HTML, bo mail nie dostaje `<style>` (poza allowlistą bleach)."""

ZNACZNIK_TRESCI = 'data-volteo="powiadomienie"'
"""Atrybut na korzeniu `email_content` kazdego z trzech budowniczych ponizej
(`zbuduj_powiadomienie_przydzialu`, `zbuduj_powiadomienie_odebrania`,
`zbuduj_powiadomienie_zmiany_terminu`) - bleach zachowuje kazdy atrybut `data-*`
(`frappe/utils/html_utils.py::sanitize_html`), wiec przezywa sanitizacje az do
szablonu. `crm/templates/emails/new_notification.html` szuka go w poczatku
`description`, zeby odroznic nasza tresc od zwyklego powiadomienia rdzenia
(wzmianka, przydzial szansy/zadania, udostepnienie) i wyrenderowac ja BEZ
duplikujacego opakowania rdzenia (powtorzony temat jako akapit, szare
`<blockquote>`, drugi link "Otworz dokument")."""

POLA_LEADA: tuple[str, ...] = (
	"lead_name",
	"mobile_no",
	"custom_install_address",
	"custom_nr_domu",
	"custom_install_postal_code",
	"custom_install_city",
	"custom_termin_spotkania",
	"custom_kolejny_kontakt",
	"custom_posiadane_produkty",
	"custom_uwagi_import",
)
"""Pola `CRM Lead` czytane do treści maila - wyłącznie permlevel 0. Celowo BEZ
`custom_cc` (permlevel 2): tożsamość CC nigdy nie ma trafić do treści maila
handlowca, niezależnie od maskowania w warstwie wyżej - patrz `nazwa_przydzielajacego`."""

_UWAGI_LIMIT_ZNAKOW = 600


def _parsuj_moment(wartosc: object) -> datetime.datetime | None:
	"""Normalizuje `datetime.datetime`, `datetime.date` albo string
	("YYYY-MM-DD HH:MM:SS" / "YYYY-MM-DD HH:MM" / "YYYY-MM-DD") do jednego
	`datetime.datetime` (data-only wchodzi jako północ), żeby `formatuj_termin`,
	`formatuj_date` i `czy_zmienil_sie_termin` porównywały/formatowały jednym kodem.
	`None`, pusty string i nierozpoznany format dają `None`."""
	if not wartosc:
		return None
	if isinstance(wartosc, datetime.datetime):
		return wartosc
	if isinstance(wartosc, datetime.date):
		return datetime.datetime(wartosc.year, wartosc.month, wartosc.day)
	if isinstance(wartosc, str):
		tekst = wartosc.strip()
		if not tekst:
			return None
		for wzor in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
			try:
				return datetime.datetime.strptime(tekst, wzor)
			except ValueError:
				continue
		return None
	return None


def formatuj_termin(wartosc: object) -> tuple[str, str, str]:
	"""`(pełna data słownie, godzina HH:MM, skrót "czw. 25.09")` dla `wartosc`
	(`datetime.datetime` albo string, patrz `_parsuj_moment`). `("", "", "")` gdy
	`wartosc` jest pusta/nierozpoznana - to jest sygnał "termin nieustalony" dla
	wołających (`zbuduj_powiadomienie_przydzialu` itd.)."""
	moment = _parsuj_moment(wartosc)
	if moment is None:
		return "", "", ""
	pelna = f"{DNI_TYGODNIA[moment.weekday()]}, {moment.day} {MIESIACE_DOPELNIACZ[moment.month - 1]} {moment.year}"
	godzina = f"{moment.hour:02d}:{moment.minute:02d}"
	krotko = f"{DNI_KROTKO[moment.weekday()]} {moment.day:02d}.{moment.month:02d}"
	return pelna, godzina, krotko


def formatuj_date(wartosc: object) -> str:
	"""Pełna data słownie ("wtorek, 30 września 2026") dla pola typu Date
	(`custom_kolejny_kontakt`). Pusty string dla `wartosc` pustej/nierozpoznanej."""
	moment = _parsuj_moment(wartosc)
	if moment is None:
		return ""
	return f"{DNI_TYGODNIA[moment.weekday()]}, {moment.day} {MIESIACE_DOPELNIACZ[moment.month - 1]} {moment.year}"


def czy_zmienil_sie_termin(stary: object, nowy: object) -> bool:
	"""True, gdy `stary` i `nowy` (każde `None`/string/`datetime`) nie oznaczają tej
	samej chwili po normalizacji przez `_parsuj_moment` - `None` i `""` są równe sobie
	(oba normalizują do `None`), a string i `datetime` tej samej chwili są równe."""
	return _parsuj_moment(stary) != _parsuj_moment(nowy)


def nazwy_produktow(tokeny: str | None) -> str:
	"""`"PV+ME"` -> `"Fotowoltaika, magazyn energii"`: pierwsza etykieta w oryginalnej
	postaci ze słownika `ETYKIETY_PRODUKTOW`, każda kolejna z małą pierwszą literą
	(sklejone zdanie, nie lista własnych nazw). Nieznany token wraca bez zmian, na
	KAŻDEJ pozycji - to jedyny token, którego ta funkcja nie przerabia wcale, bo nie
	wiadomo, czy to w ogóle nazwa własna. Pusty/`None` wejście daje pusty string."""
	if not tokeny:
		return ""
	czesci = [token for token in tokeny.split("+") if token]
	etykiety: list[str] = []
	for indeks, token in enumerate(czesci):
		etykieta = ETYKIETY_PRODUKTOW.get(token)
		if etykieta is None:
			etykiety.append(token)
			continue
		if indeks == 0 or not etykieta:
			etykiety.append(etykieta)
		else:
			etykiety.append(etykieta[0].lower() + etykieta[1:])
	return ", ".join(etykiety)


def link_do_mapy(adres: str) -> str:
	"""Link do wyszukiwarki Google Maps dla `adres` (już sklejonego, patrz `sklej_adres`).
	Pusty string dla pustego adresu - wołający pomija cały wiersz "Pokaż na mapie"."""
	if not adres:
		return ""
	return f"https://www.google.com/maps/search/?api=1&query={quote_plus(adres)}"


def sklej_adres(lead: dict) -> str:
	"""`{"custom_install_address": "Parkowa", "custom_nr_domu": "5",
	"custom_install_postal_code": "64-100", "custom_install_city": "Leszno"}` ->
	`"Parkowa 5, 64-100 Leszno"`. Puste części pomijane (brak wiodących/końcowych
	przecinków); zwraca pusty string, gdy nic z tego nie jest ustawione. Nie mutuje
	`lead`."""
	ulica = (lead.get("custom_install_address") or "").strip()
	nr = (lead.get("custom_nr_domu") or "").strip()
	kod = (lead.get("custom_install_postal_code") or "").strip()
	miasto = (lead.get("custom_install_city") or "").strip()
	czesc_ulicy = " ".join(czesc for czesc in (ulica, nr) if czesc)
	czesc_miasta = " ".join(czesc for czesc in (kod, miasto) if czesc)
	return ", ".join(czesc for czesc in (czesc_ulicy, czesc_miasta) if czesc)


def nazwa_przydzielajacego(full_name: str | None, *, maskuj: bool) -> str:
	"""Nazwa autora przydziału/zmiany gotowa do pokazania odbiorcy: `AUTOR_ZASTEPCZY_CC`
	("Call center", stała z `crm.volteo_aktywnosc`, współdzielona z maskowaniem w
	Aktywności) gdy `maskuj`, w przeciwnym razie `full_name` bez zmian (pusty string,
	gdy `full_name` jest `None`/puste)."""
	if maskuj:
		return AUTOR_ZASTEPCZY_CC
	return full_name or ""


def _skroc(tekst: str, limit: int = _UWAGI_LIMIT_ZNAKOW) -> str:
	"""`tekst` obcięty do `limit` znaków z "..." na końcu, gdy był dłuższy; bez zmian
	w przeciwnym razie (w tym dla pustego stringa)."""
	if len(tekst) <= limit:
		return tekst
	return tekst[:limit] + "..."


def _przycisk(url: str) -> str:
	"""Przycisk-link "Otwórz klienta w CRM" - inline style, bez `<style>` (poza
	allowlistą bleach: table/tr/td/div/p/strong/small/a/br/span, atrybuty
	style/bgcolor/width/align/href/class)."""
	return (
		'<p style="margin:24px 0 0 0;">'
		f'<a href="{html.escape(url)}" style="background-color:{KOLOR_MARKI};color:#ffffff;'
		'padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;'
		'font-weight:bold;">Otwórz klienta w CRM</a>'
		"</p>"
	)


def _stopka() -> str:
	return (
		'<p style="margin-top:24px;color:#6b7280;font-size:12px;">'
		"Wiadomość automatyczna z CRM ProEnergy. Termin i dane klienta możesz zmienić w jego karcie."
		"</p>"
	)


def _blok_terminu(etykieta: str, pelna: str, godzina: str, adres: str, brak_terminu_tekst: str) -> str:
	"""Blok "SPOTKANIE"/"NOWY TERMIN": lewa krawędź 4px `KOLOR_MARKI`, jasne tło,
	etykieta, data słownie + godzina, adres z linkiem "Pokaż na mapie" (gdy adres
	niepusty). Gdy `pelna` jest pusta (termin nieustalony/odwołany), zamiast tego
	jedno zdanie `brak_terminu_tekst` w tym samym bloku."""
	if not pelna:
		return (
			'<table role="presentation" width="100%" style="margin:16px 0;">'
			f'<tr><td style="border-left:4px solid {KOLOR_MARKI};background-color:#fff7ed;padding:12px 16px;">'
			f'<p style="margin:0;color:#78350f;">{html.escape(brak_terminu_tekst)}</p>'
			"</td></tr></table>"
		)
	link_mapy = link_do_mapy(adres) if adres else ""
	wiersz_adresu = ""
	if adres:
		wiersz_adresu = f'<p style="margin:4px 0 0 0;">{html.escape(adres)}'
		if link_mapy:
			wiersz_adresu += (
				f' <a href="{html.escape(link_mapy)}" style="color:{KOLOR_MARKI};">Pokaż na mapie</a>'
			)
		wiersz_adresu += "</p>"
	return (
		'<table role="presentation" width="100%" style="margin:16px 0;">'
		f'<tr><td style="border-left:4px solid {KOLOR_MARKI};background-color:#fff7ed;padding:12px 16px;">'
		f'<p style="margin:0;font-size:11px;letter-spacing:1px;color:{KOLOR_MARKI};font-weight:bold;">'
		f"{html.escape(etykieta)}</p>"
		f'<p style="margin:4px 0 0 0;font-weight:bold;">{html.escape(pelna)}, godz. {html.escape(godzina)}</p>'
		f"{wiersz_adresu}"
		"</td></tr></table>"
	)


def _wiersz_tabeli(etykieta: str, wartosc: str) -> str:
	if not wartosc:
		return ""
	return (
		f'<tr><td style="padding:4px 8px 4px 0;color:#6b7280;white-space:nowrap;vertical-align:top;">'
		f"{html.escape(etykieta)}</td>"
		f'<td style="padding:4px 0;">{html.escape(wartosc)}</td></tr>'
	)


def _tabela(wiersze: list[tuple[str, str]]) -> str:
	"""Tabela dwukolumnowa (etykieta/wartość), puste wiersze pomijane. Pusty string,
	gdy po odfiltrowaniu nic nie zostało."""
	wewnetrzne = "".join(_wiersz_tabeli(etykieta, wartosc) for etykieta, wartosc in wiersze)
	if not wewnetrzne:
		return ""
	return f'<table role="presentation" width="100%" style="margin:16px 0;border-collapse:collapse;">{wewnetrzne}</table>'


def zbuduj_powiadomienie_przydzialu(
	lead: dict,
	*,
	url: str,
	pokaz_przekazujacego: bool,
	przekazujacy: str,
) -> dict:
	"""Treść maila/dzwonka o przydziale leada handlowcowi: temat z terminem spotkania,
	gdy jest ustalony (`"Spotkanie: <Klient>, czw. 25.09, godz. 14:30"`), inaczej
	`"Nowy klient do kontaktu: <Klient>"`. Zwraca dict gotowy do `doc.update(...)` na
	`Notification Log`: `subject`, `title` (= `subject`), `email_header`,
	`email_content`, `description` (= `email_content`). Nie mutuje `lead`."""
	klient = lead.get("lead_name") or ""
	pelna, godzina, krotko = formatuj_termin(lead.get("custom_termin_spotkania"))
	ma_termin = bool(pelna and godzina)

	if ma_termin:
		subject = f"Spotkanie: {klient}, {krotko}, godz. {godzina}"
		email_header = "Nowe spotkanie z klientem"
	else:
		subject = f"Nowy klient do kontaktu: {klient}"
		email_header = "Nowy klient do kontaktu"

	if ma_termin:
		if pokaz_przekazujacego and przekazujacy:
			powitanie = (
				f"Dzień dobry,<br>{html.escape(przekazujacy)} przekazał Ci klienta. "
				"Poniżej wszystko, czego potrzebujesz przed wizytą."
			)
		else:
			powitanie = (
				"Dzień dobry,<br>call center umówiło dla Ciebie spotkanie. "
				"Poniżej wszystko, czego potrzebujesz przed wizytą."
			)
	elif pokaz_przekazujacego and przekazujacy:
		# Przydział masowy admina/backoffice (crm.api.volteo_leady.przydziel): brak
		# terminu jest normalny (lead dopiero co trafił do handlowca), a przekazujący
		# NIE jest CC, więc nie ma powodu maskować go generycznym "call center".
		powitanie = f"Dzień dobry,<br>{html.escape(przekazujacy)} przekazał Ci klienta do kontaktu."
	else:
		powitanie = "Dzień dobry,<br>call center przekazało Ci klienta do kontaktu."

	adres = sklej_adres(lead)
	blok = _blok_terminu("SPOTKANIE", pelna, godzina, adres, "Termin spotkania nie jest jeszcze ustalony.")
	tabela = _tabela(
		[
			("Klient", klient),
			("Telefon", lead.get("mobile_no") or ""),
			("Posiada już", nazwy_produktow(lead.get("custom_posiadane_produkty"))),
			("Kolejny kontakt", formatuj_date(lead.get("custom_kolejny_kontakt"))),
			("Uwagi z rozmowy", _skroc(lead.get("custom_uwagi_import") or "")),
		]
	)

	email_content = (
		f'<div {ZNACZNIK_TRESCI}>'
		f'<p style="margin:0 0 16px 0;">{powitanie}</p>{blok}{tabela}{_przycisk(url)}{_stopka()}'
		"</div>"
	)

	return {
		"subject": subject,
		"title": subject,
		"email_header": email_header,
		"email_content": email_content,
		"description": email_content,
	}


def zbuduj_powiadomienie_odebrania(lead: dict, *, url: str) -> dict:
	"""Treść powiadomienia dla handlowca, któremu ODEBRANO przydział leada (lead
	poszedł do kogoś innego) - tekst neutralny, bez żadnych nazwisk (ani nowego, ani
	poprzedniego właściciela). Ten sam kształt zwrotu co
	`zbuduj_powiadomienie_przydzialu`. Nie mutuje `lead`."""
	klient = lead.get("lead_name") or ""
	subject = f"Klient {klient} został przekazany innemu handlowcowi"
	email_header = "Zmiana przydziału"
	email_content = (
		f'<div {ZNACZNIK_TRESCI}>'
		'<p style="margin:0 0 16px 0;">Dzień dobry,<br>ten klient został przekazany innemu handlowcowi '
		f"i nie widnieje już jako Twoje przypisanie.</p>{_przycisk(url)}{_stopka()}"
		"</div>"
	)
	return {
		"subject": subject,
		"title": subject,
		"email_header": email_header,
		"email_content": email_content,
		"description": email_content,
	}


def zbuduj_powiadomienie_zmiany_terminu(
	lead: dict,
	*,
	url: str,
	stary: object,
	nowy: object,
	pokaz_zmieniajacego: bool,
	zmieniajacy: str,
) -> dict:
	"""Treść powiadomienia o zmianie (albo odwołaniu) terminu spotkania na leadzie,
	który ma już handlowca. Temat `"Zmiana terminu: <Klient>, pt. 26.09, godz. 10:00"`
	gdy `nowy` niesie termin, `"Odwołany termin: <Klient>"` gdy `nowy` jest
	puste/nierozpoznane. Ten sam kształt zwrotu co `zbuduj_powiadomienie_przydzialu`.
	Nie mutuje `lead`."""
	klient = lead.get("lead_name") or ""
	pelna_nowy, godzina_nowy, krotko_nowy = formatuj_termin(nowy)
	ma_nowy = bool(pelna_nowy and godzina_nowy)

	if ma_nowy:
		subject = f"Zmiana terminu: {klient}, {krotko_nowy}, godz. {godzina_nowy}"
	else:
		subject = f"Odwołany termin: {klient}"
	email_header = "Zmiana terminu spotkania"

	if pokaz_zmieniajacego and zmieniajacy:
		powitanie = f"Dzień dobry,<br>{html.escape(zmieniajacy)} zmienił termin spotkania z klientem."
	else:
		powitanie = "Dzień dobry,<br>call center zmieniło termin spotkania z klientem."

	brak_terminu_tekst = "Termin spotkania został odwołany."
	blok = _blok_terminu("NOWY TERMIN", pelna_nowy, godzina_nowy, sklej_adres(lead), brak_terminu_tekst)

	pelna_stary, godzina_stary, _krotko_stary = formatuj_termin(stary)
	poprzedni = f"{pelna_stary}, godz. {godzina_stary}" if pelna_stary and godzina_stary else ""

	tabela = _tabela(
		[
			("Poprzedni termin", poprzedni),
			("Klient", klient),
			("Telefon", lead.get("mobile_no") or ""),
		]
	)

	email_content = (
		f'<div {ZNACZNIK_TRESCI}>'
		f'<p style="margin:0 0 16px 0;">{powitanie}</p>{blok}{tabela}{_przycisk(url)}{_stopka()}'
		"</div>"
	)

	return {
		"subject": subject,
		"title": subject,
		"email_header": email_header,
		"email_content": email_content,
		"description": email_content,
	}


def wzbogac_notification_log(doc, method: str | None = None) -> None:
	"""Hak `Notification Log.before_insert` (rejestrowany w `crm/hooks.py`). Rdzeń
	Frappe (`assign_to.notify_assignment`) tworzy tu wiersz typu "Assignment" dla
	`CRM Lead`/`CRM Deal`/`CRM Task`, zarówno przy przydziale, jak i przy odebraniu
	przydziału (`assign_to.set_status`, wołane z `crm.api.doc.remove_assignments`).
	Guard `not doc.email_header` chroni przed nadpisaniem wiersza, który już ma
	treść z innego źródła (nie powinno się zdarzyć w praktyce, ale to tani do
	sprawdzenia warunek).

	Kontroler `NotificationLog.before_insert` (kopiuje `subject` -> `title` i
	`email_content` -> `description`) biegnie PRZED hakami `doc_events` tego samego
	eventu - `Document.run_method` woła najpierw własną metodę kontrolera, dopiero
	potem hooki (zweryfikowane na lokalnym kontenerze, Frappe 15.118). Czyli
	kopiowanie już się wydarzyło, zanim ten hak w ogóle zacznie działać - stąd
	`doc.update(...)` musi nadpisać wszystkie cztery pola (robi to, bo
	`zbuduj_powiadomienie_*` zwraca komplet), nie tylko `subject`/`email_content`.

	Rozróżnienie przydział/odebranie NIE odpytuje `ToDo`: wiersz `Notification Log`
	powstaje w zadaniu RQ (`assign_to._add` -> `notify_assignment` w tle), które
	potrafi odpalić się, zanim transakcja HTTP-a, który wstawił `ToDo`, w ogóle się
	zacommitowała - `frappe.db.exists("ToDo", ...)` dla świeżego przydziału umiałby
	wtedy zwrócić `False` i handlowiec dostałby tekst "przekazany innemu
	handlowcowi" mimo że właśnie DOSTAŁ leada. Zamiast tego czytamy sygnał, który
	rdzeń sam już ustawił, bez wyścigu: `assign_to._add` zawsze woła
	`notify_assignment` z niepustym `description` (domyślnie "Assignment for {0}
	{1}"), więc wiersz ASSIGN przychodzi z ustawionym `doc.email_content`; ścieżka
	CLOSE (`assign_to.set_status` -> `notify_assignment(..., description=None)`)
	przychodzi z pustym `email_content`. `strip_html` odcina tagi/encje rdzenia, a
	dodatkowy test na `"<img"` łapie przypadek, w którym cały "tekst" to sam obrazek
	(strip_html zwróciłby dla niego pusty string).

	Owinięte w try/except: błąd tutaj nie ma prawa zablokować wstawienia
	`Notification Log` (mail z rdzenia, choćby uboższy, jest lepszy niż brak
	powiadomienia w ogóle)."""
	import frappe
	from frappe.utils import strip_html

	try:
		if not (doc.type == "Assignment" and doc.document_type == "CRM Lead" and not doc.email_header):
			return

		lead = frappe.db.get_value("CRM Lead", doc.document_name, list(POLA_LEADA), as_dict=True)
		if not lead:
			# Lead jeszcze nie zacommitowany (np. after_insert świeżo utworzonego
			# leada z od razu ustawionym lead_owner) - po cichu zostawiamy tekst
			# rdzenia, zamiast dopisywać treść dla leada, którego nie da się
			# odczytać.
			return

		wciaz_przypisany = bool(
			strip_html(doc.email_content or "").strip() or "<img" in (doc.email_content or "")
		)

		from crm.permissions.org_hierarchy import BYPASS_ROLES, czy_autor_ma_role_cc

		pokaz = (
			doc.for_user == "Administrator"
			or bool(set(frappe.get_roles(doc.for_user)) & BYPASS_ROLES)
			or not czy_autor_ma_role_cc(doc.from_user)
		)
		url = frappe.utils.get_url(f"/crm/leads/{doc.document_name}")

		if wciaz_przypisany:
			tresc = zbuduj_powiadomienie_przydzialu(
				lead,
				url=url,
				pokaz_przekazujacego=pokaz,
				przekazujacy=frappe.utils.get_fullname(doc.from_user),
			)
		else:
			tresc = zbuduj_powiadomienie_odebrania(lead, url=url)

		doc.update(tresc)
		doc.link = url
	except Exception:
		frappe.log_error(title="volteo_powiadomienia.wzbogac_notification_log")


def powiadom_o_zmianie_terminu(doc) -> None:
	"""Wołane z `CRMLead.on_update`: gdy termin spotkania (`custom_termin_spotkania`)
	zmienił się na leadzie, który ma już handlowca (a nie właśnie go dostaje - ta
	ścieżka jest `wzbogac_notification_log` powyżej), wysyła osobne powiadomienie
	typu "Assignment" (rdzeń nie ma osobnego typu na to, a zgoda na mail w
	`Notification Settings` jest per-typ, więc nowy typ oznaczałby dla handlowca
	osobną, domyślnie wyłączoną zgodę - "Assignment" jest już włączone).

	Warunki wyjścia (w kolejności): brak stanu sprzed zapisu (`get_doc_before_save`
	zwraca `None` na pierwszym `insert`), brak `lead_owner` (nie ma komu wysłać),
	`lead_owner == frappe.session.user` (sam sobie nie wysyła powiadomienia),
	`lead_owner` właśnie się zmienił (to obsługuje `wzbogac_notification_log`, nie
	tutaj - inaczej handlowiec dostałby dwa powiadomienia o tym samym zdarzeniu),
	termin się nie zmienił (`czy_zmienil_sie_termin`).

	Owinięte w try/except: błąd tutaj nie ma prawa zablokować zapisu leada."""
	import frappe
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	try:
		przed = doc.get_doc_before_save()
		if not przed:
			return
		if not doc.lead_owner:
			return
		if doc.lead_owner == frappe.session.user:
			return
		if doc.has_value_changed("lead_owner"):
			return
		if not czy_zmienil_sie_termin(przed.custom_termin_spotkania, doc.custom_termin_spotkania):
			return

		from crm.permissions.org_hierarchy import BYPASS_ROLES, czy_autor_ma_role_cc

		odbiorca = doc.lead_owner
		autor = frappe.session.user
		pokaz = (
			odbiorca == "Administrator"
			or bool(set(frappe.get_roles(odbiorca)) & BYPASS_ROLES)
			or not czy_autor_ma_role_cc(autor)
		)
		url = frappe.utils.get_url(f"/crm/leads/{doc.name}")
		lead = {pole: doc.get(pole) for pole in POLA_LEADA}

		tresc = zbuduj_powiadomienie_zmiany_terminu(
			lead,
			url=url,
			stary=przed.custom_termin_spotkania,
			nowy=doc.custom_termin_spotkania,
			pokaz_zmieniajacego=pokaz,
			zmieniajacy=frappe.utils.get_fullname(autor),
		)

		enqueue_create_notification(
			odbiorca,
			{
				"type": "Assignment",
				"document_type": "CRM Lead",
				"document_name": doc.name,
				"from_user": autor,
				"link": url,
				**tresc,
			},
		)
	except Exception:
		frappe.log_error(title="volteo_powiadomienia.powiadom_o_zmianie_terminu")
