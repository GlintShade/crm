# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Lookup kodu pocztowego (ops#329): logika czysta, bez `frappe`.

Przeniesienie logiki Server Scriptu `volteo_postal_lookup` do forka, zeby webhook
leadow (`crm.api.leady_webhook`) i panel leada mogly z niej korzystac. Dwa stopnie:

1. cache: doctype `Postal Code` (pola `miejscowosc`, `gmina`, `powiat`,
   `wojewodztwo`, `cities` = lista miejscowosci rozdzielona `\\n`, plus `lat`/`lng`);
2. przy braku wiersza ALBO wierszu niekompletnym (brak `cities` lub `gmina`, tak
   wyglada wiekszosc ok. 20 300 wierszy z GeoNames) API Adresy.app
   (`https://api.adresy.app/api/v1/match?q=<kod>&api_key=...`), a wynik
   uzupelnia cache.

Ten modul zawiera tylko walidacje kodu, parsowanie odpowiedzi Adresy.app, decyzje
"czy wiersz jest kompletny" i scalanie wiersza z odpowiedzia. Zapytania do bazy,
HTTP i zapis cache sa w cienkim adapterze `crm/api/kod_pocztowy.py`.
Nie mutuje argumentow wejsciowych.
"""

import re
from collections.abc import Mapping
from typing import Any

from crm.volteo_leady_import import normalizuj_wojewodztwo

URL_ADRESY: str = "https://api.adresy.app/api/v1/match"
"""Endpoint dopasowania Adresy.app (parametry `q` i `api_key`)."""

TIMEOUT_ADRESY_SEK: int = 5
"""Krotki timeout HTTP: webhook i panel nie moga czekac dluzej na zewnetrzne API."""

POLA_TEKSTOWE: tuple[str, ...] = ("miejscowosc", "gmina", "powiat", "wojewodztwo")
"""Pola tekstowe wiersza `Postal Code` i odpowiedzi lookupu (bez `cities`)."""

_WZOR_KODU = re.compile(r"^(\d{2})-?(\d{3})$")
_PREFIKS_WOJ = re.compile(r"^\s*(?:wojew[oó]dztwo|woj\.?)\s+", re.IGNORECASE)
_KLUCZE_KODU_W_ODPOWIEDZI: tuple[str, ...] = ("kod", "kod_pocztowy", "kod_pna", "postal_code", "pna")


def normalizuj_kod(tekst: Any) -> str | None:
	"""Kod pocztowy do postaci `dd-ddd` albo `None`.

	Akceptuje `dd-ddd` i `ddddd` (po `strip()`); wszystko inne, takze kod z
	dopiskiem, to `None`. Tolerancyjna wersja dla ladunku webhooka to
	`crm.volteo_leady_webhook.normalizuj_kod_tolerancyjnie`."""
	if not isinstance(tekst, str):
		return None
	dopasowanie = _WZOR_KODU.match(tekst.strip())
	if not dopasowanie:
		return None
	return "%s-%s" % dopasowanie.groups()


def _tekst(wartosc: Any) -> str:
	if wartosc is None or isinstance(wartosc, (Mapping, list, tuple, bool)):
		return ""
	return str(wartosc).strip()


def rozdziel_miejscowosci(wartosc: Any) -> list[str]:
	"""Lista miejscowosci z pola `cities` (tekst rozdzielony `\\n`) albo z listy.

	Puste pozycje odpadaja, duplikaty tez (pierwsze wystapienie wygrywa)."""
	if isinstance(wartosc, (list, tuple)):
		elementy = [_tekst(e) for e in wartosc]
	else:
		elementy = [e.strip() for e in _tekst(wartosc).split("\n")]
	wynik: list[str] = []
	for element in elementy:
		if element and element not in wynik:
			wynik.append(element)
	return wynik


def normalizuj_wojewodztwo_kodu(surowe: Any) -> str | None:
	"""Wojewodztwo z cache albo Adresy.app do kanonu 16 nazw malymi literami.

	Zdejmuje prefiks `województwo `/`woj. ` i przechodzi przez
	`normalizuj_wojewodztwo` (13 wierszy `Postal Code` ma WIELKIE litery, ops#322).
	Spoza kanonu: `None`."""
	tekst = _PREFIKS_WOJ.sub("", _tekst(surowe))
	return normalizuj_wojewodztwo(tekst) if tekst else None


def wiersz_kompletny(wiersz: Mapping[str, Any] | None) -> bool:
	"""Czy wiersz cache wystarcza bez pytania Adresy.app.

	Kompletny = ma niepusta liste `cities` i `gmina`. Sam fakt istnienia wiersza nic
	nie znaczy: wiekszosc wierszy z GeoNames nie ma ani jednego, ani drugiego."""
	if not wiersz:
		return False
	return bool(rozdziel_miejscowosci(wiersz.get("cities"))) and bool(_tekst(wiersz.get("gmina")))


def parsuj_odpowiedz_adresy(odpowiedz: Any, kod: str) -> dict[str, Any] | None:
	"""Dane z odpowiedzi Adresy.app albo `None`, gdy nic uzytecznego.

	Bierze `results[0].match` (pola `miejscowosc`, `gmina`, `powiat`, `wojewodztwo`)
	i liste `results[0].extended_search.postal_localities[].miejscowosc`; pusta lista
	zastepowana jest `[match.miejscowosc]`. Gdy dopasowanie niesie wlasny kod
	pocztowy i jest on inny niz `kod`, wynik jest odrzucany (API dopasowuje
	rozmyto). Zwraca `{miejscowosc, gmina, powiat, wojewodztwo, cities}` z
	surowym wojewodztwem (normalizacja w `scal_wynik`)."""
	if not isinstance(odpowiedz, Mapping):
		return None
	wyniki = odpowiedz.get("results")
	if not isinstance(wyniki, (list, tuple)) or not wyniki or not isinstance(wyniki[0], Mapping):
		return None
	pierwszy = wyniki[0]
	dopasowanie = pierwszy.get("match")
	if not isinstance(dopasowanie, Mapping):
		return None
	for klucz in _KLUCZE_KODU_W_ODPOWIEDZI:
		kod_odpowiedzi = normalizuj_kod(_tekst(dopasowanie.get(klucz)))
		if kod_odpowiedzi and kod_odpowiedzi != kod:
			return None
	dane = {pole: _tekst(dopasowanie.get(pole)) for pole in POLA_TEKSTOWE}
	rozszerzone = pierwszy.get("extended_search")
	lokalnosci = rozszerzone.get("postal_localities") if isinstance(rozszerzone, Mapping) else None
	miejscowosci = rozdziel_miejscowosci(
		[e.get("miejscowosc") for e in lokalnosci or [] if isinstance(e, Mapping)]
		if isinstance(lokalnosci, (list, tuple))
		else []
	)
	if not miejscowosci and dane["miejscowosc"]:
		miejscowosci = [dane["miejscowosc"]]
	if not miejscowosci and not any(dane.values()):
		return None
	return {**dane, "cities": miejscowosci}


def scal_wynik(wiersz: Mapping[str, Any] | None, adresy: Mapping[str, Any] | None) -> dict[str, Any]:
	"""Odpowiedz lookupu: `{found, wojewodztwo, powiat, gmina, miejscowosc, cities}`.

	Kazde pole tekstowe z wiersza cache, gdy niepuste, inaczej z Adresy.app (Adresy
	wolamy tylko, gdy w wierszu brakuje `cities` albo `gmina`, wiec te dwa w praktyce
	przychodza z Adresy). `cities` to lista; `wojewodztwo` znormalizowane do kanonu
	(spoza kanonu: pusty tekst). `lat`/`lng` przechodza z wiersza, gdy sa (dla
	webhooka; front ich nie uzywa)."""
	wiersz = wiersz or {}
	adresy = adresy or {}
	if not wiersz and not adresy:
		return {"found": False, "wojewodztwo": "", "powiat": "", "gmina": "", "miejscowosc": "", "cities": []}
	wynik: dict[str, Any] = {"found": True}
	for pole in POLA_TEKSTOWE:
		wynik[pole] = _tekst(wiersz.get(pole)) or _tekst(adresy.get(pole))
	wynik["wojewodztwo"] = normalizuj_wojewodztwo_kodu(wynik["wojewodztwo"]) or ""
	wynik["cities"] = rozdziel_miejscowosci(wiersz.get("cities")) or rozdziel_miejscowosci(
		adresy.get("cities")
	)
	if wiersz.get("lat") and wiersz.get("lng"):
		wynik["lat"] = wiersz["lat"]
		wynik["lng"] = wiersz["lng"]
	return wynik


def pola_do_uzupelnienia_cache(wiersz: Mapping[str, Any] | None, adresy: Mapping[str, Any]) -> dict[str, str]:
	"""Pola istniejacego wiersza `Postal Code`, ktore Adresy.app uzupelnia.

	Tylko pola PUSTE w wierszu i niepuste w odpowiedzi (istniejace wartosci GeoNames
	zostaja, centroid tez). `cities` jako tekst `"\\n".join`. Wojewodztwo zapisujemy
	znormalizowane; spoza kanonu nie zapisujemy wcale."""
	wiersz = wiersz or {}
	zmiany: dict[str, str] = {}
	for pole in POLA_TEKSTOWE:
		nowe = _tekst(adresy.get(pole))
		if pole == "wojewodztwo":
			nowe = normalizuj_wojewodztwo_kodu(nowe) or ""
		if nowe and not _tekst(wiersz.get(pole)):
			zmiany[pole] = nowe
	miejscowosci = rozdziel_miejscowosci(adresy.get("cities"))
	if miejscowosci and not rozdziel_miejscowosci(wiersz.get("cities")):
		zmiany["cities"] = "\n".join(miejscowosci)
	return zmiany


def nowy_wiersz_cache(kod: str, adresy: Mapping[str, Any]) -> dict[str, str]:
	"""Pola nowego wiersza `Postal Code` (bez `doctype`) z odpowiedzi Adresy.app."""
	return {"kod": kod, **pola_do_uzupelnienia_cache(None, adresy)}


def jedyna_miejscowosc(wynik: Mapping[str, Any] | None) -> str:
	"""Miejscowosc, gdy kod ma DOKLADNIE jedna (z listy `cities`), inaczej pusty tekst.

	Gdy lista jest nieznana (pusta), nie zgadujemy z `miejscowosc` GeoNames (jedna na
	kod, czesto nie ta, ops#306)."""
	miejscowosci = rozdziel_miejscowosci((wynik or {}).get("cities"))
	return miejscowosci[0] if len(miejscowosci) == 1 else ""
