# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Zakładki „OSD” i „Dotacja” na szansie OZE (ops#202), frappe-free.

Dwie nowe zakładki na szansie, wyglądem identyczne z Montażem: karta z ręcznym
statusem (kolorowy dropdown dla backoffice/adminów, kolorowa plakietka dla
handlowca) nad strumieniem notatek tej zakładki (`NotatkiStrumien`, issue W2).
Zmianę statusu zapisuje wyłącznie backoffice/admin (`BYPASS_ROLES`) przez
`crm.api.osd_dotacja.ustaw_status`: moduł tutaj niesie WYŁĄCZNIE czyste
słowniki i formatowanie tekstu, bez żadnej walidacji uprawnień ani zapisu do
bazy (to żyje w `crm.api.osd_dotacja`, bo wymaga `frappe`).

Moduł celowo nie importuje ``frappe`` (to jedyny sposób, żeby dało się go
przetestować lokalnie na tej maszynie, gdzie ``frappe`` nie jest instalowalne;
reszta backendu ma wyłącznie bramkę składniową `ruff`/`py_compile`).

Faza 1 (ten cykl) dotyczy wyłącznie szans OZE (`crm.volteo_pipeline.
OZE_RODZAJE`). Schemat i backend są jednak wspólne od razu (pola i uprawnienia
na `CRM Deal` nie różnicują linii produktowej), żeby Czyste Powietrze w fazie 2
nie wymagało migracji, tylko odblokowania w `Deal.vue`/`MobileDeal.vue`.

Słowniki i kolory są kanonem TUTAJ i lustrzane w dwóch innych miejscach, które
trzeba synchronizować ręcznie przy każdej zmianie:
  - ``ops/crm-osd-dotacja.py`` (opcje pól Select `custom_status_osd` /
    `custom_status_dotacja` na `CRM Deal`);
  - ``frontend/src/utils/osdDotacja.js`` (lustro JS: `STATUSY`, `KOLORY`,
    `ETYKIETY`, `kolorStatusu()`).

Pusta wartość w bazie (pole nigdy nie ustawione) renderuje się jak „Nie
rozpoczęto” (gray), bez żadnego zapisu. „Nie rozpoczęto” jest też PRAWDZIWĄ
wartością w `STATUSY` (backoffice może jawnie ustawić ten status, np. żeby
cofnąć omyłkowy wybór), tylko domyślny (nieustawiony) stan renderuje się
identycznie.
"""

__all__ = [
	"ETYKIETY_KART",
	"KOLORY",
	"POLE",
	"STATUSY",
	"ZAKLADKI",
	"tekst_sladu_statusu",
]

ZAKLADKI: tuple[str, ...] = ("OSD", "Dotacja")
"""Klucze zakładki, co do litery jak `name` zakładek w `Deal.vue`/`MobileDeal.vue`."""

POLE: dict[str, str] = {
	"OSD": "custom_status_osd",
	"Dotacja": "custom_status_dotacja",
}
"""Zakładka -> fieldname pola Select na `CRM Deal` (permlevel 3, `ops/crm-osd-dotacja.py`)."""

STATUSY: dict[str, tuple[str, ...]] = {
	"OSD": (
		"Nie rozpoczęto",
		"Zgłoszenie wysłane",
		"Uwagi OSD",
		"Umowa przyłączeniowa",
		"Licznik wymieniony",
		"Zakończone",
	),
	"Dotacja": (
		"Nie rozpoczęto",
		"Wniosek złożony",
		"Uzupełnienie",
		"Decyzja pozytywna",
		"Wypłacona",
		"Odrzucona",
	),
}
"""Zakładka -> krotka dozwolonych wartości pola Select, w kolejności wyświetlania
w dropdownie. Pierwsza wartość każdej krotki jest zawsze „Nie rozpoczęto” (stan
początkowy). Pusty string NIE jest członkiem żadnej krotki, więc
`crm.api.osd_dotacja.ustaw_status` odrzuca pusty `status` samą przynależnością
do tej krotki, bez osobnego sprawdzenia."""

KOLORY: dict[str, dict[str, str]] = {
	"OSD": {
		"Nie rozpoczęto": "gray",
		"Zgłoszenie wysłane": "blue",
		"Uwagi OSD": "blue",
		"Umowa przyłączeniowa": "blue",
		"Licznik wymieniony": "blue",
		"Zakończone": "green",
	},
	"Dotacja": {
		"Nie rozpoczęto": "gray",
		"Wniosek złożony": "blue",
		"Uzupełnienie": "blue",
		"Decyzja pozytywna": "lime",
		"Wypłacona": "green",
		"Odrzucona": "red",
	},
}
"""Kolor (klucz `COLOR_BUTTON_CLASS_MAP` we `frontend/src/utils/statusColors.js`) dla
każdej wartości `STATUSY`. Decyzja właściciela 2026-09-28: statusy „w trakcie” są
zawsze niebieskie (ten sam wybór co `Procesowane` na statusie finansowania
formularza kredytowego, ops#197), tylko stany terminalne dostają inny kolor.
`Odrzucona` jest czerwona, `Zakończone`/`Wypłacona` zielone, `Decyzja pozytywna`
jasnozielona (`lime`, klucz dopisany do `COLOR_BUTTON_CLASS_MAP` przez ten
issue)."""

ETYKIETY_KART: dict[str, str] = {
	"OSD": "Status OSD",
	"Dotacja": "Status dotacji",
}
"""Etykieta karty statusu wyświetlana nad strumieniem notatek każdej zakładki."""

_ETYKIETY_SLADU: dict[str, str] = {
	"OSD": "OSD",
	"Dotacja": "dotacji",
}
"""Rzeczownik/skrót wplatany w środek zdania śladu Aktywności (odmiana: „status
OSD”, skrót się nie odmienia, ale „status dotacji”, dopełniacz). Prywatne:
konsumowane wyłącznie przez `tekst_sladu_statusu` poniżej."""


def tekst_sladu_statusu(zakladka: str, stary: str | None, nowy: str) -> str:
	"""Tekst linii Aktywności dla zmiany statusu zakładki OSD/Dotacja. Wołane z
	`crm.volteo_aktywnosc.tekst_sladu` (gałąź `"status_zakladki"`), strzałka `→`
	jak `status_auto`/`kredyt_status_finansowania`. `stary` puste/`None` (pierwsze
	ustawienie statusu) daje „ustawiono status …: <nowy>” zamiast strzałki.
	Rzuca `ValueError` dla nieznanej zakładki."""
	etykieta = _ETYKIETY_SLADU.get(zakladka)
	if etykieta is None:
		raise ValueError(f"Nieznana zakładka: {zakladka!r}")
	if stary:
		return f"status {etykieta}: {stary} → {nowy}"
	return f"ustawiono status {etykieta}: {nowy}"
