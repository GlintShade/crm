# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do zaproszonego użytkownika CRM: logika czysta.

Po wysłaniu maila z zaproszeniem (`CRM Invitation.invite_via_email`) adapter
`crm/api/sms_zaproszenie.py` wysyła na numer z zaproszenia krótki SMS, że w skrzynce
czeka e-mail z linkiem do aktywacji konta. SMS NIE niesie linku ani klucza zaproszenia:
jedynym nośnikiem sekretu zostaje e-mail.

Moduł celowo nie importuje ``frappe`` (precedens `crm/volteo_sms.py`), żeby dało się
go przetestować bez bench.
"""

from collections.abc import Mapping
from typing import Any

from crm.volteo_dyzury import normalizuj_numer_pl
from crm.volteo_sms import LIMIT_JEDNEJ_CZESCI, dlugosc_gsm7, numer_do_smsapi, transliteruj_gsm7

POLE_PRZELACZNIKA: str = "zaproszenie_wlaczone"
"""Pole w Single `Volteo SMS Ustawienia`. Brak pola na site oznacza: kanał włączony."""

TRESC_Z_ADRESEM: str = (
	"CRM ProEnergy: wyslalismy zaproszenie do CRM na adres {email}. "
	"Otworz e-mail i kliknij link, aby aktywowac konto i sie zalogowac."
)
TRESC_BEZ_ADRESU: str = (
	"CRM ProEnergy: wyslalismy Ci e-mail z zaproszeniem do CRM. "
	"Otworz go i kliknij link, aby aktywowac konto i sie zalogowac."
)
"""Literały bez polskich znaków celowo (GSM-7, jedna część SMS)."""


def czy_kanal_wlaczony(ustawienia: Mapping[str, Any]) -> bool:
	"""True, gdy pola przełącznika nie ma (site bez skryptu ops) albo jest prawdziwe.

	`get_singles_dict` zwraca stringi i nie ma klucza dla pola nigdy nie zapisanego,
	dlatego brak klucza i pusta wartość to "domyślnie włączony", a tylko jawne 0 wyłącza.
	"""
	wartosc = ustawienia.get(POLE_PRZELACZNIKA)
	if wartosc in (None, ""):
		return True
	try:
		return int(str(wartosc).strip()) != 0
	except ValueError:
		return True


def numer_zaproszonego(mobile_no: str | None) -> str | None:
	"""Numer z formularza zaproszenia w formacie SMSAPI (`48XXXXXXXXX`) albo None.

	Formularz przyjmuje dowolny zapis (`600 100 200`, `+48 600-100-200`, `0048...`),
	więc najpierw normalizujemy do `+48XXXXXXXXX`. Numer zagraniczny lub stacjonarny
	z błędną długością daje None.
	"""
	return numer_do_smsapi(normalizuj_numer_pl(mobile_no))


def zbuduj_tresc_zaproszenia(email: str | None) -> str:
	"""Treść SMS w GSM-7, zawsze w jednej części (160 znaków).

	Wersja z adresem e-mail, gdy się mieści; dla długiego adresu wersja bez adresu.
	"""
	adres = transliteruj_gsm7((email or "").strip())
	if adres:
		z_adresem = TRESC_Z_ADRESEM.format(email=adres)
		if dlugosc_gsm7(z_adresem) <= LIMIT_JEDNEJ_CZESCI:
			return z_adresem
	return TRESC_BEZ_ADRESU
