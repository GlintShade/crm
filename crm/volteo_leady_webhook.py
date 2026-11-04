# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Webhook leadow z Facebook Lead Ads przez Make.com (ops#296): logika czysta.

Scenariusz Make.com ("Facebook Lead Ads > Watch Leads") wysyla kazdy nowy lead
jako POST JSON do `crm.api.leady_webhook.przyjmij`. Ten modul zamienia ladunek
na slownik pol `CRM Lead`; sam insert, bramka roli, idempotencja i log odrzuconych
mieszkaja w cienkim adapterze `crm/api/leady_webhook.py`.

Modul celowo nie importuje ``frappe`` (precedens `crm/volteo_leady_import.py`),
zeby dalo sie go przetestowac lokalnie. Nie mutuje argumentow wejsciowych.

Odrzucenie calego ladunku (`LadunekOdrzucony`): brak albo zly telefon, brak
`facebook_lead_id` (klucz idempotencji). Kazde inne pole, ktorego nie da sie
rozpoznac, NIE gubi leada: surowa wartosc trafia jako linia do
`custom_uwagi_import`, a pole docelowe zostaje puste.
"""

import re
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from crm.volteo_kod_pocztowy import jedyna_miejscowosc
from crm.volteo_leady_import import (
	SEPARATOR_UWAG,
	normalizuj_pisownie_osoby,
	normalizuj_posiadane_produkty,
	normalizuj_telefon,
	normalizuj_wojewodztwo,
	rozdziel_imie_nazwisko,
	wyglada_na_firme,
)

ROLA_INTEGRACJI: str = "Volteo Integracja"
"""Rola konta integracji Make.com: jedyna bramka endpointu (bez zadnego DocPerm)."""

TOKEN_ZRODLA_FB: str = "FB"
"""Token w `custom_import_source` dla leadow z Facebooka."""

ZRODLO_LEADA: str = "Facebook"
"""Wartosc `CRM Lead.source` (wiersz `CRM Lead Source` istnieje z patcha upstreamu)."""

IMIE_ZASTEPCZE: str = "Lead Facebook"
"""`first_name`, gdy formularz nie niesie imienia (kontroler wymaga imienia)."""

LIMIT_ZADAN_NA_MINUTE: int = 3
"""Decyzja wlasciciela 2026-10-22: liczy KAZDE wywolanie endpointu przez konto integracji (utworzony, duplikat i odrzucony tak samo); okno przesuwne celowo pominiete, stale okno minuty kalendarzowej wystarcza jako hamulec."""


def klucz_limitu(uzytkownik: str, teraz: datetime) -> str:
	"""Klucz licznika limitu w Redis: uzytkownik plus minuta kalendarzowa."""
	return f"volteo:webhook_leady:limit:{uzytkownik}:{teraz.strftime('%Y%m%d%H%M')}"


def limit_przekroczony(licznik: int, limit: int = LIMIT_ZADAN_NA_MINUTE) -> bool:
	"""True, gdy `licznik` (wlacznie z biezacym zadaniem) przekracza `limit`."""
	return licznik > limit


_TAK = frozenset({"tak", "yes", "true", "1"})
_NIE = frozenset({"nie", "no", "false", "0"})

_SYSTEM_NOWE = ("net-billing", "net billing", "netbilling", "nowe", "nowy")
_SYSTEM_STARE = ("net-metering", "net metering", "netmetering", "opust", "stare", "stary")

_WZOR_DATY = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ].*)?$")
_WZOR_SLOW = re.compile(r"[^\W_]+", re.UNICODE)

_SLOWA_PV = frozenset({"pv", "fotowoltaika", "fotowoltaiki", "fotowoltaike", "fotowoltaiczna"})
# Porownanie idzie po zdjeciu diakrytykow, wiec "fotowoltaike/fotowoltaika" z ogonkami tez pasuja.
_SLOWA_ME = frozenset({"mag", "magazyn", "magazyny", "magazynem", "magazynu", "me"})
_SLOWA_PC = frozenset({"pc", "pompa", "pompy", "pompe", "ciepla", "ciepła"})
_SLOWA_CP = frozenset({"cp", "czyste", "powietrze"})
_SLOWA_LACZNIKI = frozenset({"i", "z", "oraz", "plus", "energii"})


# Dwie cyfry, opcjonalny separator (dowolna kreska Unicode, kropka, podkreslnik, spacje), trzy cyfry;
# calosc nie moze byc czescia dluzszego ciagu cyfr.
_WZOR_KODU = re.compile(r"(?<!\d)(\d{2})[\s\-\u2010-\u2015\u2212._]*(\d{3})(?!\d)")


def normalizuj_kod_tolerancyjnie(tekst: str) -> str | None:
	"""Tolerancyjna normalizacja kodu pocztowego do `dd-ddd` (tylko webhook).

	Akceptuje `00000`, `00 000`, `00 - 000`, rozne kreski Unicode, kropke albo
	podkreslnik zamiast kreski oraz dopiski (`64-000 Koscian`, `kod 64000`).
	Dokladnie jedno unikalne dopasowanie albo `None` (brak lub kilka roznych
	kodow). Scisly `normalizuj_kod` z importu arkusza zostaje bez zmian."""
	kody = {f"{a}-{b}" for a, b in _WZOR_KODU.findall(_tekst(tekst))}
	if len(kody) != 1:
		return None
	return next(iter(kody))


class LadunekOdrzucony(ValueError):
	"""Ladunek webhooka nie nadaje sie do zalozenia leada; `powod` czytelny dla logu."""

	def __init__(self, powod: str):
		super().__init__(powod)
		self.powod = powod


def _tekst(wartosc: Any) -> str:
	"""Sprowadza dowolna wartosc ladunku do przyciętego tekstu.

	`None` -> "", liczby -> tekst (`5.0` -> "5"), listy/krotki -> niepuste elementy
	przez ", " (Make potrafi wyslac liste jednoelementowa), reszta przez `str()`."""
	if wartosc is None:
		return ""
	if isinstance(wartosc, bool):
		return "true" if wartosc else "false"
	if isinstance(wartosc, float) and wartosc.is_integer():
		return str(int(wartosc))
	if isinstance(wartosc, (list, tuple)):
		return ", ".join(t for t in (_tekst(e) for e in wartosc) if t)
	if isinstance(wartosc, Mapping):
		return ""
	return str(wartosc).strip()


def _klucze_malymi(ladunek: Mapping[str, Any]) -> dict[str, Any]:
	"""Kopia ladunku z kluczami po `strip()` i malymi literami (nowy slownik)."""
	return {str(k).strip().lower(): v for k, v in ladunek.items()}


def _bez_diakrytykow(tekst: str) -> str:
	"""Zdejmuje polskie znaki diakrytyczne (`fotowoltaikę` -> `fotowoltaike`)."""
	rozlozone = unicodedata.normalize("NFD", tekst.replace("\u0142", "l").replace("\u0141", "L"))
	return "".join(z for z in rozlozone if not unicodedata.combining(z))


def normalizuj_posiada_pv(tekst: str) -> str | None:
	"""Mapuje odpowiedz na pytanie "Czy masz juz PV?" na tokeny `custom_posiadane_produkty`.

	`tak/yes/true/1` -> `"PV"`, `nie/no/false/0` albo pusty -> `""`. Odpowiedzi opisowe
	formularza Facebooka (takze jako slugi Meta, np. `mam_fotowoltaike_z_magazynem_energii`),
	rozpoznawane po slowach: `nie` + `mam` -> `""`; `mam` + PV + magazyn -> `"PV+ME"`
	(chyba ze jest slowo `bez` -> `"PV"`); `mam` + PV bez magazynu -> `"PV"`.
	Inne -> `None`."""
	czysty = _tekst(tekst).lower()
	if not czysty or czysty in _NIE:
		return ""
	if czysty in _TAK:
		return "PV"
	slowa = set(_WZOR_SLOW.findall(_bez_diakrytykow(czysty)))
	if "mam" not in slowa:
		return None
	if "nie" in slowa:
		return ""
	if not slowa & _SLOWA_PV:
		return None
	if slowa & _SLOWA_ME and "bez" not in slowa:
		return normalizuj_posiadane_produkty("PV+ME")
	return normalizuj_posiadane_produkty("PV")


def normalizuj_system_rozliczen(tekst: str) -> str | None:
	"""Mapuje opis systemu rozliczen na literaly `custom_zasady_dotacji`.

	Net-billing / nowe -> `"Nowe zasady"`, net-metering / opust / stare ->
	`"Stare zasady"`. Pusty, nierozpoznany albo dwuznaczny (oba rodzaje naraz) -> `None`."""
	czysty = _tekst(tekst).lower()
	if not czysty:
		return None
	nowe = any(w in czysty for w in _SYSTEM_NOWE)
	stare = any(w in czysty for w in _SYSTEM_STARE)
	if nowe and not stare:
		return "Nowe zasady"
	if stare and not nowe:
		return "Stare zasady"
	return None


def normalizuj_produkt_reklamy(tekst: str) -> str | None:
	"""Mapuje produkt z reklamy na token `KOLEJNOSC_PRODUKTOW_PROCESU`.

	WYLACZONE z webhooka decyzja wlasciciela 2026-11-04: `zbuduj_leada_z_webhooka` juz tego nie
	wywoluje (wartosc `produkt` od agencji jest per formularz, nie per klient). Funkcja zostaje
	wraz z testami (polityka: wygaszaj, nie usuwaj).

	PV + magazyn / `pvme` -> `PVME`, sam magazyn / `me` -> `ME`, sam `pv` -> `PV`,
	pompa ciepla / `pc` -> `PC`, czyste powietrze / `cp` -> `CP`. Kazde nieznane
	slowo albo mieszanka rodzin (np. PV i pompa) -> `None` (surowy tekst idzie do Uwag)."""
	czysty = _tekst(tekst).lower()
	slowa = _WZOR_SLOW.findall(czysty)
	if not slowa:
		return None
	pv = me = pc = cp = False
	for slowo in slowa:
		if slowo == "pvme":
			pv = me = True
		elif slowo in _SLOWA_PV:
			pv = True
		elif slowo in _SLOWA_ME or slowo.startswith("magazyn"):
			me = True
		elif slowo in _SLOWA_PC:
			pc = True
		elif slowo in _SLOWA_CP:
			cp = True
		elif slowo in _SLOWA_LACZNIKI:
			continue
		else:
			return None
	rodziny = sum((pv or me, pc, cp))
	if rodziny != 1:
		return None
	if cp:
		return "CP"
	if pc:
		return "PC"
	if pv and me:
		return "PVME"
	if me:
		return "ME"
	return "PV"


def normalizuj_date_zgloszenia(tekst: str) -> str | None:
	"""Czesc daty z ISO `YYYY-MM-DD` albo ISO datetime; inaczej `None`."""
	dopasowanie = _WZOR_DATY.match(_tekst(tekst))
	if not dopasowanie:
		return None
	try:
		return date.fromisoformat(dopasowanie.group(1)).isoformat()
	except ValueError:
		return None


def splaszcz_odpowiedzi(odpowiedzi: Any) -> list[tuple[str, str]]:
	"""Splaszcza `odpowiedzi` do listy `(pytanie, odpowiedz)`, bez pustych odpowiedzi.

	Akceptuje slownik `{pytanie: odpowiedz}` albo liste Facebookowa
	`[{"name": ..., "values": [...]}]` (tez z kluczem `value`). Inne ksztalty -> `[]`."""
	wynik: list[tuple[str, str]] = []
	if isinstance(odpowiedzi, Mapping):
		pary = list(odpowiedzi.items())
	elif isinstance(odpowiedzi, (list, tuple)):
		pary = []
		for element in odpowiedzi:
			if not isinstance(element, Mapping):
				continue
			klucze = _klucze_malymi(element)
			pary.append((klucze.get("name"), klucze.get("values", klucze.get("value"))))
	else:
		return wynik
	for pytanie, odpowiedz in pary:
		nazwa = _tekst(pytanie)
		tresc = _tekst(odpowiedz)
		if nazwa and tresc:
			wynik.append((nazwa, tresc))
	return wynik


ODPOWIEDZI_POSIADA_PV: dict[str, tuple[str, str]] = {
	"tak,_bez_magazynu": ("PV", "Tak, bez magazynu"),
	"tak,_z_magazynem": ("PV+ME", "Tak, z magazynem"),
	"mam_fotowoltaikę_bez_magazynu_energii": ("PV", "Mam fotowoltaikę bez magazynu energii"),
	"nie_mam_jeszcze_fotowoltaiki": ("", "Nie mam jeszcze fotowoltaiki"),
	"mam_fotowoltaikę_z_magazynem_energii": ("PV+ME", "Mam fotowoltaikę z magazynem energii"),
}
ODPOWIEDZI_SYSTEM_ROZLICZEN: dict[str, tuple[str, str]] = {
	"stare_zasady": ("Stare zasady", "Stare zasady"),
	"nowe_zasady_(net-billing)": ("Nowe zasady", "Nowe zasady (net-billing)"),
}


def rozpoznaj_posiada_pv(surowe: Any) -> tuple[str | None, str]:
	"""Zwraca (wartosc pola, etykieta do Uwag) dla odpowiedzi "Czy masz PV?".

	Najpierw dokladny slownik `ODPOWIEDZI_POSIADA_PV` (klucz: `_tekst(surowe).lower()`),
	potem `normalizuj_posiada_pv`; poza slownikiem etykieta to surowy tekst. Nierozpoznane
	daje `(None, surowy tekst)`."""
	tekst = _tekst(surowe)
	trafienie = ODPOWIEDZI_POSIADA_PV.get(tekst.lower())
	if trafienie is not None:
		wartosc, etykieta = trafienie
		return (normalizuj_posiadane_produkty(wartosc) if wartosc else ""), etykieta
	return normalizuj_posiada_pv(tekst), tekst


def rozpoznaj_system_rozliczen(surowe: Any) -> tuple[str | None, str]:
	"""Jak `rozpoznaj_posiada_pv`, dla systemu rozliczen (`ODPOWIEDZI_SYSTEM_ROZLICZEN`,
	potem `normalizuj_system_rozliczen`)."""
	tekst = _tekst(surowe)
	trafienie = ODPOWIEDZI_SYSTEM_ROZLICZEN.get(tekst.lower())
	if trafienie is not None:
		return trafienie
	return normalizuj_system_rozliczen(tekst), tekst


PREFIKS_KAMPANII: str = "Kampania: "
"""Prefiks linii z kampania w `custom_uwagi_import` (patrz `zbuduj_leada_z_webhooka`).
Czytaja go `kampania_z_uwag` i SMS dyzurny (`crm.volteo_dyzury.wyciagnij_z_uwag`)."""

_SEGMENT_KAMPANII = re.compile(r"\[([^\]]*)\]")
_DATA_KAMPANII = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.\d{2,4})?$")
_SEGMENTY_KAMPANII_POMIJANE = frozenset({"S"})


def kampania_czytelna(kampania: Any) -> str:
	"""Skraca nazwe kampanii FB do `<Miasto>, <DD.MM>` dla call center.

	`[S][KAMPANIA LEADOWA][WROCŁAW][27.10.2026]` -> `Wrocław, 27.10`. Segmenty `[S]` i
	zawierajace slowo `KAMPANIA` odpadaja, data traci rok, miasto pisane WIELKIMI
	literami dostaje wielka litere tylko na poczatku slow (polskie znaki zostaja).
	Tekst bez nawiasow albo bez zadnego segmentu do pokazania wraca bez zmian, wiec
	funkcja jest idempotentna (`Wrocław, 27.10` -> `Wrocław, 27.10`)."""
	tekst = _tekst(kampania)
	segmenty = [s.strip() for s in _SEGMENT_KAMPANII.findall(tekst)]
	if not segmenty:
		return tekst
	miejsca: list[str] = []
	daty: list[str] = []
	for segment in segmenty:
		wielkie = segment.upper()
		if not segment or wielkie in _SEGMENTY_KAMPANII_POMIJANE or "KAMPANIA" in wielkie:
			continue
		data = _DATA_KAMPANII.match(segment)
		if data:
			daty.append("%02d.%02d" % (int(data.group(1)), int(data.group(2))))
		else:
			miejsca.append(segment.title() if segment == wielkie else segment)
	czesci = miejsca + daty
	return ", ".join(czesci) if czesci else tekst


def opis_posiada_pv(wartosc: str, surowe: Any = "") -> str:
	"""Czytelna linia Uwag dla rozpoznanej odpowiedzi o PV (`wartosc` z `rozpoznaj_posiada_pv`).

	`""` -> `Nie ma PV`, z magazynem -> `Ma PV z magazynem`, samo PV -> `Ma PV bez
	magazynu`, gdy odpowiedz mowila "bez" (np. "Tak, bez magazynu"), inaczej `Ma PV`
	(golym "Tak" klient nie powiedzial nic o magazynie)."""
	tokeny = set((wartosc or "").split("+"))
	if "PV" not in tokeny:
		return "Nie ma PV"
	if "ME" in tokeny:
		return "Ma PV z magazynem"
	slowa = set(_WZOR_SLOW.findall(_bez_diakrytykow(_tekst(surowe).lower())))
	return "Ma PV bez magazynu" if "bez" in slowa else "Ma PV"


OPISY_ZASAD: dict[str, str] = {
	"Stare zasady": "stare zasady",
	"Nowe zasady": "nowe zasady (net-billing)",
}
"""Literal `custom_zasady_dotacji` -> tekst w linii `System rozliczeń: ...`."""

PREFIKS_SYSTEMU: str = "System rozliczeń: "
"""Prefiks linii Uwag z rozpoznanym systemem rozliczen (klient z PV)."""

PREFIKSY_PV: tuple[str, ...] = ("Ma PV", "Nie ma PV")
"""Poczatki czytelnych linii Uwag o PV (patrz `opis_posiada_pv`)."""


def tekst_formularza(tekst: Any) -> str:
	"""Pytanie albo odpowiedz z `odpowiedzi` po ludzku: podkreslniki na spacje.

	Slugi Meta (`jaki_jest_twój_rachunek?`, `300-500_zł`) dostaja spacje; pytanie traci
	koncowe `?`/`:` i dostaje wielka litere w `pytanie_formularza`. Polskie znaki zostaja."""
	return " ".join(_tekst(tekst).replace("_", " ").split())


def pytanie_formularza(pytanie: Any) -> str:
	"""Pytanie z `odpowiedzi` jako etykieta linii Uwag (bez `?`/`:` na koncu, wielka litera)."""
	tekst = tekst_formularza(pytanie).rstrip("?: ").strip()
	return tekst[:1].upper() + tekst[1:]


def zbuduj_leada_z_webhooka(ladunek: Mapping[str, Any], dzisiaj: str) -> dict[str, Any]:
	"""Zamienia ladunek webhooka na slownik pol `CRM Lead` (bez `doctype`).

	Rzuca `LadunekOdrzucony` przy braku/zlym telefonie albo braku `facebook_lead_id`.
	Klucze wyjsciowe puste sa pomijane. `dzisiaj` (ISO) to wartosc zastepcza
	`custom_import_date`. Nie mutuje `ladunek`."""
	if not isinstance(ladunek, Mapping):
		raise LadunekOdrzucony("Ladunek nie jest obiektem JSON.")
	dane = _klucze_malymi(ladunek)

	telefon_surowy = _tekst(dane.get("telefon"))
	if not telefon_surowy:
		raise LadunekOdrzucony("Brak numeru telefonu.")
	telefon = normalizuj_telefon(telefon_surowy)
	if telefon is None:
		raise LadunekOdrzucony("Niepoprawny numer telefonu: %s" % telefon_surowy)

	id_leada = _tekst(dane.get("facebook_lead_id"))
	if not id_leada:
		raise LadunekOdrzucony("Brak facebook_lead_id.")

	linie_odpowiedzi: list[str] = []

	# Imie i nazwisko
	pelne = _tekst(dane.get("imie_nazwisko"))
	if not pelne:
		imie, nazwisko = IMIE_ZASTEPCZE, ""
	elif wyglada_na_firme(pelne):
		imie, nazwisko = pelne, ""
	else:
		imie, nazwisko = rozdziel_imie_nazwisko(pelne, "")
		imie = normalizuj_pisownie_osoby(imie)
		nazwisko = normalizuj_pisownie_osoby(nazwisko)

	# Czy posiada PV
	posiada_surowe = _tekst(dane.get("posiada_pv"))
	posiada: str | None = ""
	if posiada_surowe:
		posiada, _etykieta_pv = rozpoznaj_posiada_pv(posiada_surowe)
		if posiada is None:
			linie_odpowiedzi.append("Posiada PV (nierozpoznane): %s" % posiada_surowe)
		else:
			linie_odpowiedzi.append(opis_posiada_pv(posiada, posiada_surowe))

	# System rozliczen: pole tylko gdy klient ma PV
	system_surowy = _tekst(dane.get("system_rozliczen"))
	zasady = ""
	if system_surowy:
		rozpoznane, etykieta_sys = rozpoznaj_system_rozliczen(system_surowy)
		opis_sys = OPISY_ZASAD.get(rozpoznane or "", etykieta_sys)
		if not posiada_surowe:
			linie_odpowiedzi.append("System rozliczeń (brak odpowiedzi o PV): %s" % opis_sys)
		elif posiada is None:
			linie_odpowiedzi.append("System rozliczeń (PV nierozpoznane): %s" % opis_sys)
		elif "PV" in posiada.split("+"):
			if rozpoznane is None:
				linie_odpowiedzi.append("System rozliczeń (nierozpoznane): %s" % system_surowy)
			else:
				zasady = rozpoznane
				linie_odpowiedzi.append(PREFIKS_SYSTEMU + opis_sys)
		else:
			linie_odpowiedzi.append("System rozliczeń (klient bez PV): %s" % opis_sys)
	posiada = posiada or ""

	# Produkt z reklamy: klucz `produkt` jest CELOWO ignorowany (decyzja wlasciciela 2026-11-04).
	# Agencja ustawia go per formularz w scenariuszu Make, nie per klient, wiec wprowadzal
	# call center w blad. Wartosc nie trafia ani do `custom_produkt_procesu`, ani do Uwag.

	# Data zgloszenia
	data_surowa = _tekst(dane.get("data_zgloszenia"))
	data = normalizuj_date_zgloszenia(data_surowa) if data_surowa else None
	if data is None:
		data = dzisiaj
		if data_surowa:
			linie_odpowiedzi.append("Data zgłoszenia (nierozpoznana): %s" % data_surowa)

	# Kod pocztowy: klucz `kod_pocztowy`; wsteczna zgodnosc, gdy kod przyszedl pod `miasto`
	kod_surowy = _tekst(dane.get("kod_pocztowy"))
	miasto = _tekst(dane.get("miasto"))
	kod = ""
	if kod_surowy:
		kod = normalizuj_kod_tolerancyjnie(kod_surowy) or ""
		if not kod:
			linie_odpowiedzi.append("Kod pocztowy (do sprawdzenia): %s" % kod_surowy)
	elif miasto:
		kod_z_miasta = normalizuj_kod_tolerancyjnie(miasto)
		if kod_z_miasta:
			kod, miasto = kod_z_miasta, ""

	# Kolejnosc linii (decyzja wlasciciela 2026-11-04): kampania pierwsza, bo lista leadow
	# pokazuje tylko pierwsza linie, a z niej call center widzi okreg. Bez linii "Zrodlo"
	# (dubel pola Zrodlo).
	linie: list[str] = []
	kampania = kampania_czytelna(dane.get("kampania"))
	if kampania:
		linie.append(PREFIKS_KAMPANII + kampania)
	formularz = _tekst(dane.get("formularz"))
	if formularz:
		linie.append("Formularz: %s" % formularz)
	linie.extend(linie_odpowiedzi)
	for pytanie, odpowiedz in splaszcz_odpowiedzi(dane.get("odpowiedzi")):
		etykieta = pytanie_formularza(pytanie)
		tresc = tekst_formularza(odpowiedz)
		linie.append("%s: %s" % (etykieta, tresc) if etykieta else tresc)

	wynik: dict[str, Any] = {
		"first_name": imie,
		"mobile_no": telefon,
		"source": ZRODLO_LEADA,
		"custom_import_source": TOKEN_ZRODLA_FB,
		"custom_import_date": data,
		"facebook_lead_id": id_leada,
	}
	opcjonalne = {
		"custom_uwagi_import": SEPARATOR_UWAG.join(linie),
		"last_name": nazwisko,
		"custom_install_city": miasto,
		"custom_install_postal_code": kod,
		"custom_posiadane_produkty": posiada,
		"custom_zasady_dotacji": zasady,
		"facebook_form_id": _tekst(dane.get("facebook_form_id")),
	}
	return {**wynik, **{k: v for k, v in opcjonalne.items() if v}}


UWAGA_KOD_SPOZA_BAZY: str = "Kod spoza bazy, brak pinezki na mapie"
"""Notka w Uwagach, gdy kod pocztowy leada nie ma centroidu (brak w `Postal Code` i w Adresy.app,
albo wiersz bez wspolrzednych) lub gdy lookup sie nie udal."""

POLE_GMINY_LEADA: str = "custom_gmina"
"""Pole gminy na `CRM Lead` (Custom Field ze skryptu ops#329); adapter podaje je tylko, gdy istnieje."""


def dane_z_kodu_pocztowego(
	dane: dict, wiersz: Mapping[str, Any] | None, pole_gminy: str | None = None
) -> dict:
	"""Nowy słownik z danymi lookupu kodu: centroid, województwo, powiat, gmina, miejscowość.

	`wiersz` to wynik `crm.api.kod_pocztowy.dane_kodu` (cache `Postal Code` uzupełniony
	z Adresy.app), stary kształt samego wiersza `Postal Code` też przechodzi; `None` albo
	`found: False` oznacza kod nieznany. Miejscowość (`custom_install_city`) wpisujemy
	TYLKO, gdy lista `cities` ma dokładnie jedną pozycję i lead nie ma już miasta z
	ładunku; przy kilku albo nieznanej liście pole zostaje puste (wybór z listy w panelu),
	bo `miejscowosc` GeoNames to jedna na kod, często nie ta (ops#306, ops#329).
	Gmina tylko do `pole_gminy`, gdy adapter je poda (pole istnieje na leadzie).
	Województwo przechodzi przez `normalizuj_wojewodztwo` (w tabeli bywa WIELKIMI
	literami, a `custom_voivodeship` to Select z małymi): wartość spoza kanonu jest
	pomijana, nigdy nie wywala insertu (ops#322). Brak centroidu: notka w Uwagach.
	Nie mutuje `dane`."""
	wynik = dict(dane)
	if wiersz and wiersz.get("found", True):
		wojewodztwo = normalizuj_wojewodztwo(_tekst(wiersz.get("wojewodztwo")))
		if wojewodztwo:
			wynik["custom_voivodeship"] = wojewodztwo
		if _tekst(wiersz.get("powiat")):
			wynik["custom_powiat"] = _tekst(wiersz.get("powiat"))
		if pole_gminy and _tekst(wiersz.get("gmina")):
			wynik[pole_gminy] = _tekst(wiersz.get("gmina"))
		miejscowosc = jedyna_miejscowosc(wiersz)
		if miejscowosc and not wynik.get("custom_install_city"):
			wynik["custom_install_city"] = miejscowosc
		if wiersz.get("lat") and wiersz.get("lng"):
			wynik.update(
				custom_lat=wiersz["lat"],
				custom_lng=wiersz["lng"],
				custom_geo_dokladnosc="kod",
				custom_geo_zrodlo="kod",
			)
			return wynik
	uwagi = wynik.get("custom_uwagi_import") or ""
	wynik["custom_uwagi_import"] = SEPARATOR_UWAG.join(filter(None, [uwagi, UWAGA_KOD_SPOZA_BAZY]))
	return wynik


POLA_TAGOW_DO_UZUPELNIENIA: tuple[str, ...] = (
	"custom_posiadane_produkty",
	"custom_zasady_dotacji",
	"custom_produkt_procesu",
)
"""Pola, ktore ponowne zgloszenie FB uzupelnia na istniejacym leadzie, wylacznie gdy sa puste (ops#324)."""


def _znacznik_zgloszenia(facebook_lead_id: str) -> str:
	"""Fragment linii Uwag identyfikujacy zgloszenie; z nawiasem, by id 123 nie pasowalo do 1234."""
	return "lead FB %s)" % facebook_lead_id


def _dzien_miesiac(data_iso: Any) -> str:
	"""`2026-11-02` -> `02.11`; inny tekst bez zmian."""
	tekst = _tekst(data_iso)
	dopasowanie = _WZOR_DATY.match(tekst)
	if not dopasowanie:
		return tekst
	_rok, miesiac, dzien = dopasowanie.group(1).split("-")
	return "%s.%s" % (dzien, miesiac)


def zloz_linie_ponownego_zgloszenia(
	data_iso: Any,
	facebook_lead_id: str,
	segmenty: list[str],
	posiadane: str | None,
	zasady: str | None,
	istniejacy: Mapping[str, Any] | None = None,
) -> str:
	"""Jedna linia Uwag dla ponownego zgloszenia (ops#324), bez wewnetrznego `SEPARATOR_UWAG`.

	`Ponowne zgłoszenie 02.11: Szczecin, 27.10; Ma PV bez magazynu (lead FB <id>)`.
	`segmenty` to linie Uwag nowego zgloszenia w obecnym formacie: z linii kampanii zostaje
	sama wartosc, czytelne linie PV i `System rozliczeń: ...` odpadaja, gdy `posiadane` /
	`zasady` zgadzaja sie z polami `istniejacy` (scalanie pol nie nadpisuje, wiec rozna
	odpowiedz musi zostac w tekscie). Reszta linii zostaje, laczona "; ".
	Znacznik `lead FB <id>)` zostaje doslownie: na nim stoi `juz_scalone`."""
	ist = istniejacy or {}
	pv_zgodne = istniejacy is not None and (posiadane or "") == (ist.get("custom_posiadane_produkty") or "")
	zasady_zgodne = istniejacy is not None and (zasady or "") == (ist.get("custom_zasady_dotacji") or "")
	czesci: list[str] = []
	for segment in segmenty:
		segment = segment.strip()
		if not segment:
			continue
		if segment.startswith(PREFIKS_KAMPANII):
			segment = segment[len(PREFIKS_KAMPANII) :].strip()
		elif pv_zgodne and segment.startswith(PREFIKSY_PV):
			continue
		elif zasady_zgodne and segment.startswith(PREFIKS_SYSTEMU):
			continue
		if segment:
			czesci.append(segment)
	naglowek = "Ponowne zgłoszenie %s" % _dzien_miesiac(data_iso)
	tresc = "; ".join(czesci)
	znacznik = "(%s" % _znacznik_zgloszenia(facebook_lead_id)
	return "%s: %s %s" % (naglowek, tresc, znacznik) if tresc else "%s %s" % (naglowek, znacznik)


def linia_ponownego_zgloszenia(dane: Mapping[str, Any], istniejacy: Mapping[str, Any] | None = None) -> str:
	"""Linia dopisywana do Uwag istniejacego leada (ops#324).

	`dane` to wynik `zbuduj_leada_z_webhooka` dla NOWEGO zgloszenia, `istniejacy` to pola
	leada, do ktorego scalamy (PV i zasady zgodne z nimi nie sa powtarzane)."""
	uwagi = dane.get("custom_uwagi_import") or ""
	return zloz_linie_ponownego_zgloszenia(
		dane.get("custom_import_date"),
		dane["facebook_lead_id"],
		uwagi.split(SEPARATOR_UWAG) if uwagi else [],
		dane.get("custom_posiadane_produkty"),
		dane.get("custom_zasady_dotacji"),
		istniejacy,
	)


def juz_scalone(uwagi_istniejace: str | None, facebook_lead_id: str) -> bool:
	"""Czy Uwagi istniejacego leada juz zawieraja to zgloszenie (idempotencja retry Make)."""
	return _znacznik_zgloszenia(facebook_lead_id) in (uwagi_istniejace or "")


def kampania_z_uwag(uwagi: str | None) -> str:
	"""Wartosc linii `Kampania: ...` z Uwag nowego ladunku, albo pusty tekst."""
	for linia in (uwagi or "").split(SEPARATOR_UWAG):
		if linia.startswith(PREFIKS_KAMPANII):
			return linia[len(PREFIKS_KAMPANII) :].strip()
	return ""


def tresc_sladu_ponownego_zgloszenia(dane: Mapping[str, Any]) -> str:
	"""Tresc komentarza `Info` w Aktywnosci leada."""
	kampania = kampania_z_uwag(dane.get("custom_uwagi_import"))
	return "Ponowne zgłoszenie z Facebooka: %s" % (kampania or "brak kampanii")


def pola_do_scalenia(istniejacy: Mapping[str, Any], nowy: Mapping[str, Any]) -> dict[str, str]:
	"""Tylko te pola, ktore trzeba zapisac na istniejacym leadzie.

	`custom_uwagi_import` zawsze (stare Uwagi plus nowa linia, `SEPARATOR_UWAG`); trzy pola
	tagow tylko gdy puste u istniejacego, a niepuste w nowym. Status, wlasciciel, CC, adres,
	imie i `facebook_lead_id` nigdy nie wchodza do wyniku. Nie mutuje argumentow."""
	uwagi = SEPARATOR_UWAG.join(
		filter(
			None, [istniejacy.get("custom_uwagi_import") or "", linia_ponownego_zgloszenia(nowy, istniejacy)]
		)
	)
	wynik = {"custom_uwagi_import": uwagi}
	for pole in POLA_TAGOW_DO_UZUPELNIENIA:
		if not istniejacy.get(pole) and nowy.get(pole):
			wynik[pole] = nowy[pole]
	return wynik
