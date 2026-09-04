# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Logika wpisów Trify na szansie Czyste Powietrze (ops#75), frappe-free.

Moduł celowo nie importuje ``frappe`` -- to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową). Cała logika zależna od
frameworka (walidacja dokumentu, wysyłka powiadomienia) mieszka w
``crm.api.trify``, tu tylko czyste funkcje.

Doctype ``Volteo Trify Update`` tworzy ``ops/crm-trify.py`` w
``proenergy-crm-ops`` -- tutaj (w forku) go nie ma. Frontend dodaje wpisy
przez ``frappe.client.insert`` i czyta przez ``frappe.client.get_list``; pole
``tekst`` to HTML z edytora (Text Editor), może zawierać wzmianki w postaci
``<span class="mention" data-type="mention" data-id="email" data-label="Imię
Nazwisko">@Imię</span>`` -- Frappe's sanityzacja HTML je zachowuje.
"""

import html
import re

DOCTYPE = "Volteo Trify Update"

TYPY = (
	"Notatka",
	"Wniosek Trify",
	"Decyzja Trify",
	"Umowa Trify",
	"Wypłata Trify",
	"Problem",
)
"""Dozwolone wartości pola `typ`. Lustro dwóch innych miejsc, które muszą
zostać zsynchronizowane ręcznie przy każdej zmianie: pole Select `typ` w
`ops/crm-trify.py` (definicja doctype'u) i stała `TRIFY.typy` we frontendowym
`frontend/src/utils/aktualizacje.js`."""


def tekst_pusty(tresc: str | None) -> bool:
	"""Czy `tresc` (HTML) po odarciu ze znaczników i encji nie zawiera żadnej treści.

	Edytor TipTap potrafi zapisać pusty akapit jako `'<p></p>'`, samo
	`'<p>&nbsp;</p>'` albo `'<p><br></p>'` -- żadne z nich nie jest pustym
	stringiem, więc naiwne `not tresc` przepuściłoby je jako "coś wpisano".
	Regex zamiast parsera HTML: moduł jest celowo frappe-free (bez BeautifulSoup),
	a zadanie -- "czy zostało coś poza znacznikami/spacjami" -- nie wymaga
	drzewa DOM.
	"""
	if not tresc:
		return True
	bez_tagow = re.sub(r"<[^>]*>", "", tresc)
	bez_encji = bez_tagow.replace("&nbsp;", " ")
	return bez_encji.strip() == ""


def zbuduj_powiadomienie(
	autor_email: str,
	autor_nazwa: str,
	deal: str,
	docname: str,
	odbiorca: str,
) -> dict:
	"""Składa słownik dla `notify_user`
	(`crm.fcrm.doctype.crm_notification.crm_notification.notify_user`) --
	powiadomienie-dzwoneczek o wzmiance w treści wpisu Trify.

	Kształt HTML wzorowany na `crm.api.pipeline._bell_notification`. `autor_nazwa`
	i `deal` są escapowane przez `html.escape` -- oba pochodzą z danych
	użytkownika (imię i nazwisko, nazwa szansy), nie z ustalonego słownika jak
	typ wpisu.
	"""
	autor_nazwa_bezp = html.escape(autor_nazwa)
	deal_bezp = html.escape(deal)
	tresc = (
		'<div class="mb-2 leading-5 text-ink-gray-5">'
		f'<span class="font-medium text-ink-gray-9">{autor_nazwa_bezp}</span>'
		f' wspomniał(a) Cię we wpisie Trify szansy'
		f' <span class="font-medium text-ink-gray-9">{deal_bezp}</span>'
		"</div>"
	)
	return {
		"owner": autor_email,
		"assigned_to": odbiorca,
		"notification_type": "Mention",
		"message": tresc,
		"notification_text": tresc,
		"reference_doctype": DOCTYPE,
		"reference_docname": docname,
		"redirect_to_doctype": "CRM Deal",
		"redirect_to_docname": deal,
	}
