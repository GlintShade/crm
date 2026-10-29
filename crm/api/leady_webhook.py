# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
Webhook leadów z Facebook Lead Ads przez Make.com (ops#296)
======================================================================

Scenariusz Make.com ("Facebook Lead Ads > Watch Leads") wysyła każdy nowy lead
jako POST JSON do `przyjmij`. Endpoint zakłada wyłącznie NOWEGO `CRM Lead`: bez
aktualizacji, bez przydziału (`lead_owner` i `custom_cc` zostają puste, lead
trafia do puli admina), bez geokodowania po adresie.

Make musi wołać tę metodę PEŁNĄ ścieżką kropkowaną:
`POST /api/method/crm.api.leady_webhook.przyjmij` (gołą nazwą rozwiązuje się
tylko Server Script).

Model uprawnień
----------------
Pierwszą instrukcją jest `frappe.only_for("Volteo Integracja")`: Guest i każda
inna rola dostają PermissionError (403); Administrator przechodzi (sonda).
Konto integracji (`ops/crm-integracja-make.py`) ma wyłącznie tę rolę i NIE ma
żadnego DocPerm na `CRM Lead`, dlatego insert idzie z `ignore_permissions=True`
(wzór upstreamowy `lead_syncing/.../facebook.py::sync_single_lead`). Bramka NDA
(`crm.api.oswiadczenie`) jest dla tej metody zdjęta w `_ALLOWLIST`.

Idempotencja i odrzucenia
----------------------------
- Ten sam `facebook_lead_id` drugi raz: HTTP 200 `{"status": "duplikat",
  "lead": <name>}`, bez insertu i bez wpisu w logu błędów (powtórka z Make to
  normalny retry).
- Ładunek nie do przyjęcia (zły telefon, brak `facebook_lead_id`): wiersz
  `Failed Lead Sync Log` i HTTP 200 `{"status": "odrzucony", "powod": ...}`.
  Celowo NIE `frappe.throw`: zły telefon nie naprawi się przy retry Make, a
  wyjątek cofnąłby wpis logu. Nieoczekiwane wyjątki lecą dalej (HTTP 500, Make
  ponawia).
- Sukces: `{"status": "utworzony", "lead": <name>}`.

Limit żądań
------------
Konto integracji może wywołać endpoint 3 razy na minutę (`LIMIT_ZADAN_NA_MINUTE`).
Licznik to stałe okno minuty kalendarzowej w Redis (`klucz_limitu`), liczone PO
bramce roli, więc wywołania niezalogowane nie zużywają budżetu. Czwarte żądanie w
minucie dostaje HTTP 429, więc Make ponowi je później. Liczy się KAŻDE wywołanie,
także duplikat i odrzucony. To hamulec przed zalaniem puli leadów przez wyciekły
klucz, a nie wartość przepustowości.

SMS powitalny (ops#305)
-----------------------
Po udanym insercie NOWEGO leada (status `utworzony`, nigdy duplikat ani odrzucony)
rejestrujemy callback `frappe.db.after_commit`, który kolejkuje
`crm.api.sms_powitalny.wyslij_sms_powitalny` (kolejka "short"). To jedyna ścieżka
wyzwalająca SMS. Awaria SMS nie cofa leada i nie zmienia odpowiedzi webhooka.
Funkcja sama sprawdza przełącznik `wlaczone` w `Volteo SMS Ustawienia` (domyślnie
wyłączony) i zapisuje wynik na leadzie.

Cała logika mapowania jest w `crm/volteo_leady_webhook.py` (bez `frappe`).
"""

import json

import frappe
from frappe import _

from crm.volteo_leady_webhook import (
	LIMIT_ZADAN_NA_MINUTE,
	ROLA_INTEGRACJI,
	SEPARATOR_UWAG,
	LadunekOdrzucony,
	klucz_limitu,
	limit_przekroczony,
	zbuduj_leada_z_webhooka,
)

UWAGA_KOD_SPOZA_BAZY = "Kod pocztowy spoza bazy kodów, brak pinezki na mapie"
KOMUNIKAT_LIMITU = "Przekroczono limit %d żądań na minutę. Spróbuj ponownie za chwilę."


def _sprawdz_limit_zadan() -> None:
	"""Stałe okno minuty w Redis; wołać po `only_for`, by niezalogowani nie zużywali budżetu."""
	cache = frappe.cache()
	klucz = klucz_limitu(frappe.session.user, frappe.utils.now_datetime())
	licznik = cache.incr(klucz)
	if licznik == 1:
		cache.expire(klucz, 120)
	if limit_przekroczony(licznik):
		frappe.throw(_(KOMUNIKAT_LIMITU) % LIMIT_ZADAN_NA_MINUTE, frappe.RateLimitExceededError)


def _wczytaj_ladunek() -> dict:
	"""Kopia `frappe.form_dict` bez `cmd`/`data`; zagnieżdżony `ladunek` ma pierwszeństwo."""
	ladunek = {k: v for k, v in dict(frappe.form_dict).items() if k not in ("cmd", "data")}
	zagniezdzony = ladunek.get("ladunek")
	if isinstance(zagniezdzony, str):
		try:
			zagniezdzony = json.loads(zagniezdzony)
		except ValueError:
			raise LadunekOdrzucony("Pole 'ladunek' nie jest poprawnym JSON.") from None
	if isinstance(zagniezdzony, dict):
		return dict(zagniezdzony)
	return ladunek


def _zapisz_odrzucenie(ladunek: dict, powod: str) -> None:
	frappe.get_doc(
		{
			"doctype": "Failed Lead Sync Log",
			"type": "Failure",
			"lead_data": frappe.as_json(ladunek),
			"traceback": powod,
		}
	).insert(ignore_permissions=True)


def _z_centroidem_kodu(dane: dict) -> dict:
	"""Nowy słownik z danymi `Postal Code`: centroid, województwo i powiat.

	Miejscowości z tabeli NIE przenosimy (GeoNames trzyma jedną na kod, często
	nie tę). Kod spoza bazy zostaje zapisany bez współrzędnych, z notką w Uwagach."""
	kod = dane.get("custom_install_postal_code")
	if not kod:
		return dane
	wiersz = frappe.db.get_value(
		"Postal Code", {"kod": kod}, ["lat", "lng", "wojewodztwo", "powiat"], as_dict=True
	)
	if not wiersz:
		uwagi = dane.get("custom_uwagi_import") or ""
		return {
			**dane,
			"custom_uwagi_import": SEPARATOR_UWAG.join(filter(None, [uwagi, UWAGA_KOD_SPOZA_BAZY])),
		}
	wynik = dict(dane)
	if wiersz.get("wojewodztwo"):
		wynik["custom_voivodeship"] = wiersz["wojewodztwo"]
	if wiersz.get("powiat"):
		wynik["custom_powiat"] = wiersz["powiat"]
	if wiersz.get("lat") and wiersz.get("lng"):
		wynik.update(
			custom_lat=wiersz["lat"],
			custom_lng=wiersz["lng"],
			custom_geo_dokladnosc="kod",
			custom_geo_zrodlo="kod",
		)
	return wynik


def _zakolejkuj_sms_powitalny(lead: str) -> None:
	"""Kolejkuje SMS dopiero po commicie leada, z własnym try/except w callbacku.

	Nie używamy `enqueue_after_commit=True`: Frappe woła callbacki `after_commit` bez
	obsługi wyjątków, a `sync_database()` jest w `frappe/app.py` poza blokiem except,
	więc błąd Redis przy kolejkowaniu dałby gołe HTTP 500 po już zapisanym leadzie
	(Make ponowiłby żądanie i dostał `duplikat`). Własny callback łapie wszystko i
	zostawia wpis w Error Log.
	"""

	def _enqueue() -> None:
		try:
			frappe.enqueue("crm.api.sms_powitalny.wyslij_sms_powitalny", queue="short", lead=lead)
		except Exception:
			frappe.log_error(
				title="SMS powitalny",
				message=f"Lead {lead}: nie udało się zakolejkować\n{frappe.get_traceback()}",
			)

	try:
		frappe.db.after_commit.add(_enqueue)
	except Exception:
		frappe.log_error(
			title="SMS powitalny",
			message=f"Lead {lead}: nie udało się zarejestrować callbacku\n{frappe.get_traceback()}",
		)


@frappe.whitelist(methods=["POST"])
def przyjmij() -> dict:
	"""Zakłada `CRM Lead` z ładunku Make.com; patrz docstring modułu."""
	frappe.only_for(ROLA_INTEGRACJI)
	_sprawdz_limit_zadan()

	ladunek = {}
	try:
		ladunek = _wczytaj_ladunek()
		dane = zbuduj_leada_z_webhooka(ladunek, frappe.utils.today())
	except LadunekOdrzucony as blad:
		_zapisz_odrzucenie(ladunek or dict(frappe.form_dict), blad.powod)
		return {"status": "odrzucony", "powod": blad.powod}

	istniejacy = frappe.db.get_value("CRM Lead", {"facebook_lead_id": dane["facebook_lead_id"]}, "name")
	if istniejacy:
		return {"status": "duplikat", "lead": istniejacy}

	doc = frappe.get_doc({"doctype": "CRM Lead", **_z_centroidem_kodu(dane)}).insert(
		ignore_permissions=True
	)
	_zakolejkuj_sms_powitalny(doc.name)
	return {"status": "utworzony", "lead": doc.name}
