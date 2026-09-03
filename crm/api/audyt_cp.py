# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Whitelisted API audytu specjalnego Czyste Powietrze (doctype `Volteo Audyt CP`).

`Volteo Audyt CP` jest 1:1 z `CRM Deal` (`autoname: "field:deal"` — nazwa
dokumentu to nazwa szansy), analogicznie do `Volteo Umowa`/`Volteo Kredyt`.
Frontend woła te endpointy WYŁĄCZNIE pełną kropkowaną ścieżką
(`crm.api.audyt_cp.volteo_audyt_cp_*`) — gołe nazwy metod działają tylko dla
Server Scriptów, nie dla wywołań `call()` frontendu na whitelisted API forka
(patrz pułapka HTTP 417 udokumentowana przy `Volteo Umowa`/`AudytTab.vue`).

Cała logika domenowa (katalog slotów, walidacja werdyktów, agregacja stanu
weryfikacji, reset werdyktów po zmianie źródłowego pliku) żyje w
`crm.czyste_powietrze.audyt` — frappe-free, testowalne bez frappe
zainstalowanego lokalnie (`crm/czyste_powietrze/test_audyt.py`). Ten moduł
tylko odczytuje/zapisuje dokumenty `Volteo Audyt CP`, sprawdza uprawnienia i
dyspozytuje powiadomienia — żadnej wiedzy o KSZTAŁCIE formularza tu nie ma.

Semantyka jest świadomie przeniesiona z poprzednika, audytu technicznego OZE
(`Volteo Audyt`, `ops/crm-audyt.py`, Server Scripty SUBMIT/SET_STATUS/
SET_VERDICT/Lock Guard) — cykl statusu Szkic → Weryfikacja → Zatwierdzony,
read-modify-write na `weryfikacja_json` przez `frappe.db.set_value` (celowo
omija hooki dokumentu, żeby `lock_guard` mógł swobodnie blokować zwykłe
zapisy bez blokowania też PRZYCISKÓW submit/set-status/set-verdict), i
komentarz `Info` po każdym przejściu (bo `db.set_value` pomija tworzenie
wersji/timeline). Różnica od poprzednika: to zwykłe API forka (importy
dozwolone), nie Server Script, więc logika domenowa nie jest duplikowana w
locie tylko importowana wprost z `crm.czyste_powietrze.audyt`; i celowo ZERO
automatyzacji rurociągu (`advance_deal_status`) — decyzja właściciela, audyt
specjalny CP niczego w statusie szansy nie przesuwa.
"""

import json
from typing import Any

import frappe
from frappe import _

from crm.api.pipeline import dispatch_notification
from crm.czyste_powietrze.audyt import (
    KLUCZ_ZDJECIA,
    MAX_NOTATKA,
    MAX_ZDJEC,
    SLOTY_DOKUMENTOW,
    STATUSY,
    agreguj,
    braki_do_przeslania,
    elementy_weryfikacji,
    etykieta_dla,
    parsuj_liste,
    parsuj_mape,
    resetuj_werdykty,
    waliduj_werdykt,
)
from crm.permissions.org_hierarchy import BYPASS_ROLES
from crm.volteo_aktywnosc import roznice_plikow_audytu

DOCTYPE = "Volteo Audyt CP"

REVIEWER_ROLES = BYPASS_ROLES
"""Role recenzenta (backoffice/core-admin) audytu specjalnego CP — identyczny
zbiór co `crm.permissions.org_hierarchy.BYPASS_ROLES` (widoczność Deal/Kontakt/
Faktura i brama `volteo_podzadania_set`), więc importujemy zamiast duplikować,
dla spójności z resztą rurociągu CP zamiast osobnego, przypadkiem zbieżnego
literału."""

ADMIN_ROLES = frozenset({"System Manager", "Volteo Core Admin"})
"""Role administratora — WĘŻSZY zbiór niż `REVIEWER_ROLES` (bez `Volteo
Backend`): tylko admin może zatwierdzać/usuwać nieodwracalnie, backoffice
wykonuje bieżącą recenzję. Celowo zdefiniowane lokalnie, nie importowane —
`delete_lockdown.py`/`kalkulator_guard.py` w tym repo trzymają swoje zbiory
ról osobno z tego samego powodu (patrz CLAUDE.md), więc ten moduł idzie tym
samym wzorcem zamiast zbiegać się z `BYPASS_ROLES`, który akurat NIE pasuje
tutaj (zawiera `Volteo Backend`, którego tu nie chcemy)."""

_SLOTY_KLUCZE = frozenset(slot["klucz"] for slot in SLOTY_DOKUMENTOW)
"""Katalog dozwolonych kluczy slotów dokumentów — zaporowa lista dla
`lock_guard`, żeby `dokumenty_json` nie mógł znosić dowolnych kluczy spoza
formularza."""

_ETYKIETY_SLOTOW: dict[str, str] = {slot["klucz"]: slot["etykieta"] for slot in SLOTY_DOKUMENTOW}
"""Mapa klucz slotu -> etykieta, dla `crm.volteo_aktywnosc.roznice_plikow_audytu`
(ops#70) — `lock_guard` loguje nią zmiany plików audytu jako ślady `Info`."""


def _is_reviewer() -> bool:
    return bool(set(frappe.get_roles()) & REVIEWER_ROLES)


def _is_admin() -> bool:
    return bool(set(frappe.get_roles()) & ADMIN_ROLES)


def _sprawdz_dostep_do_szansy(deal: str, ptype: str = "read") -> None:
    """Sprawdza istnienie szansy i uprawnienie `ptype` (domyślnie `read`) wywołującego do niej.

    Ten sam wzorzec co `crm.api.pipeline._sprawdz_dostep_do_szansy`/
    `crm.api.umowa._sprawdz_dostep_do_szansy` — powtórzony lokalnie (nie
    importowany), bo każdy z tych modułów ma go jako prywatny helper bez
    współdzielonego miejsca; zachowanie musi jednak zostać identyczne.
    """
    if not deal or not frappe.db.exists("CRM Deal", deal):
        frappe.throw(_("Szansa sprzedaży nie istnieje."), frappe.DoesNotExistError)
    if not frappe.has_permission("CRM Deal", ptype, deal):
        frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)


def _pobierz_audyt(deal: str) -> "frappe.model.document.Document | None":
    """Zwraca dokument `Volteo Audyt CP` dla szansy, jeśli istnieje — inaczej `None`.

    Nazwa dokumentu jest tożsama z nazwą szansy (`autoname: field:deal`).
    """
    if frappe.db.exists(DOCTYPE, deal):
        return frappe.get_doc(DOCTYPE, deal)
    return None


def _audyt_do_dict(audyt_doc: "frappe.model.document.Document") -> dict[str, Any]:
    """Spłaszcza dokument `Volteo Audyt CP` do bloku `audyt` odpowiedzi.

    `dokumenty_json`/`zdjecia_json`/`weryfikacja_json` są zwracane jako surowy
    tekst JSON, tak jak leżą w bazie — frontend je parsuje, tak samo jak inne
    `*_json` pola w tym repozytorium (np. `custom_podzadania_json` przez
    `crm.volteo_pipeline.parsuj_podzadania` po stronie serwera, ale tu bez
    odpowiednika po stronie odczytu, bo kształt jest specyficzny per-formularz
    i żyje tylko we froncie).
    """
    return {
        "name": audyt_doc.name,
        "status": audyt_doc.status,
        "dokumenty_json": audyt_doc.dokumenty_json,
        "zdjecia_json": audyt_doc.zdjecia_json,
        "weryfikacja_json": audyt_doc.weryfikacja_json,
        "zatwierdzony_przez": audyt_doc.zatwierdzony_przez,
        "zatwierdzony_dnia": audyt_doc.zatwierdzony_dnia,
        "owner": audyt_doc.owner,
    }


def _plik_istnieje_dla(deal: str):
    """Zwraca callback `url -> bool` dla `braki_do_przeslania`, sprawdzający,
    że dany URL jest naprawdę załącznikiem TEGO audytu (nie dowolnym plikiem w
    systemie o zgadującym się URL-u) — trzy warunki filtra jednocześnie:
    doctype, nazwa dokumentu (= `deal`) i sam `file_url`.
    """

    def _sprawdz(url: str) -> bool:
        return bool(
            frappe.db.exists(
                "File",
                {"attached_to_doctype": DOCTYPE, "attached_to_name": deal, "file_url": url},
            )
        )

    return _sprawdz


@frappe.whitelist()
def volteo_audyt_cp_get(deal: str) -> dict[str, Any]:
    """Zwraca istniejący audyt (jeśli jest), KSZTAŁT formularza (`sloty`,
    `klucz_zdjecia`, `max_zdjec`, `max_notatka`) i uprawnienia wywołującego
    (`can_review`, `is_admin`, `can_edit`).

    Wymaga `read` do szansy. Pusty `audyt: None` (audyt jeszcze nie utworzony)
    jest poprawną odpowiedzią, nie błędem — frontend pokazuje wtedy pusty
    formularz startowy zamiast się wywalać.

    `can_edit` = recenzent (backoffice/core-admin) LUB (audyt istnieje i jego
    `owner` to bieżący użytkownik) LUB (audyt nie istnieje i wywołujący ma
    uprawnienie `create` na `Volteo Audyt CP`) — trzy niezależne drogi do
    edycji roboczego formularza, żaden inny użytkownik go nie widzi jako
    edytowalny.
    """
    _sprawdz_dostep_do_szansy(deal, "read")

    audyt_doc = _pobierz_audyt(deal)
    can_review = _is_reviewer()

    if audyt_doc is not None:
        can_edit = can_review or audyt_doc.owner == frappe.session.user
    else:
        can_edit = can_review or bool(frappe.has_permission(DOCTYPE, "create"))

    return {
        "audyt": _audyt_do_dict(audyt_doc) if audyt_doc else None,
        "sloty": [dict(slot) for slot in SLOTY_DOKUMENTOW],
        "klucz_zdjecia": KLUCZ_ZDJECIA,
        "max_zdjec": MAX_ZDJEC,
        "max_notatka": MAX_NOTATKA,
        "can_review": can_review,
        "is_admin": _is_admin(),
        "can_edit": can_edit,
    }


@frappe.whitelist()
def volteo_audyt_cp_submit(deal: str) -> dict[str, Any]:
    """Przesyła audyt ze statusu Szkic do Weryfikacja, po walidacji kompletu
    dokumentów/zdjęć (`braki_do_przeslania`).

    Wolno: recenzent (backoffice/core-admin) ALBO właściciel dokumentu
    (`owner`) — tak jak w poprzedniku (`ops/crm-audyt.py` SUBMIT_SCRIPT),
    przedstawiciel przesyła własny audyt, backoffice/admin może przesłać w
    jego imieniu.

    Zapis statusu przez `frappe.db.set_value` (celowo, omija `lock_guard`,
    tak jak `SUBMIT_SCRIPT` omijał Lock Guard poprzednika) — `weryfikacja_json`
    jest resetowany na `"{}"`, żeby ponowne przesłanie (po „Przywróć do
    edycji”) nie niosło nieaktualnych werdyktów z poprzedniej rundy recenzji.
    ŻADNEJ automatyzacji rurociągu (`advance_deal_status`) — decyzja
    właściciela, zero automatyzacji statusu szansy z audytu specjalnego CP.

    Uprawnienia do szansy: `write` (SEC#35 — było `read`: ten endpoint
    zapisuje status audytu przez `db.set_value`, więc `read` był
    niewystarczającą bramką; sprawdzenie recenzent/właściciel poniżej
    zostaje jako dodatkowa, węższa autoryzacja, nie zamiast tej bramki).
    """
    _sprawdz_dostep_do_szansy(deal, "write")

    audyt_doc = _pobierz_audyt(deal)
    if audyt_doc is None:
        frappe.throw(_("Audyt dla tej szansy sprzedaży nie istnieje."), frappe.DoesNotExistError)

    if not (_is_reviewer() or audyt_doc.owner == frappe.session.user):
        frappe.throw(_("Brak uprawnień do przesłania tego audytu."), frappe.PermissionError)

    if audyt_doc.status != "Szkic":
        frappe.throw(_("Audyt można przesłać tylko ze statusu Szkic."))

    dokumenty = parsuj_mape(audyt_doc.dokumenty_json)
    zdjecia = parsuj_liste(audyt_doc.zdjecia_json)

    braki = braki_do_przeslania(dokumenty, zdjecia, _plik_istnieje_dla(deal))
    if braki:
        frappe.throw(_("Nie można przesłać audytu. Braki: {0}").format(", ".join(braki)))

    frappe.db.set_value(DOCTYPE, deal, {"status": "Weryfikacja", "weryfikacja_json": "{}"})
    # db.set_value pomija tworzenie wersji/timeline -> odnotuj przejście jako
    # natywny komentarz Info, żeby pojawiło się w aktywności szansy.
    frappe.get_doc(DOCTYPE, deal).add_comment("Info", _("Audyt przesłany do weryfikacji"))

    tekst_html = (
        '<div class="mb-2 leading-5 text-ink-gray-5">'
        '<span class="font-medium text-ink-gray-9">Audyt CP</span> szansy '
        '<span class="font-medium text-ink-gray-9">' + deal + "</span> "
        "został przesłany do weryfikacji</div>"
    )
    dispatch_notification("powiadomienie_audyt_cp_przeslany", deal, tekst_html)

    return {"ok": True, "status": "Weryfikacja"}


@frappe.whitelist()
def volteo_audyt_cp_set_status(deal: str, status: str) -> dict[str, Any]:
    """Zmienia status audytu przyciskiem dedykowanym (nie zwykłym zapisem
    formularza) — tylko recenzent (backoffice/core-admin).

    Dozwolone przejścia:
    - Weryfikacja → Zatwierdzony: tylko gdy `agreguj(...)["wszystkie_zaakceptowane"]`
      jest prawdziwe (KAŻDY aktualny element weryfikacji ma werdykt „accepted”)
      — to jest AUTORYTATYWNA brama, przycisk frontowy jest tylko wygodą i
      nigdy nie wolno mu ufać samemu. Zapisuje też `zatwierdzony_przez`/
      `zatwierdzony_dnia`.
    - Zatwierdzony → Szkic („Przywróć do edycji”): czyści `weryfikacja_json`
      na `"{}"` i oba stemple zatwierdzenia (`None`) — audyt wraca do stanu
      przed jakąkolwiek recenzją.
    - Weryfikacja → Szkic jest CELOWO odrzucane: poprawki robi się edycją w
      miejscu (dozwoloną recenzentowi przez `lock_guard`, dopóki audyt jest w
      Weryfikacji), nie odsyłaniem z powrotem do przedstawiciela — tak samo
      jak w poprzedniku (`ops/crm-audyt.py` SET_STATUS_SCRIPT, b46).
    - Wszystkie inne przejścia (w tym `status == current`, czy dowolna próba
      wejścia w Weryfikację tędy zamiast przez `volteo_audyt_cp_submit`) są
      odrzucane jednym ogólnym komunikatem.

    Uprawnienia do szansy: `write` (SEC#35 — było `read`: ten endpoint
    zapisuje status/werdykty przez `db.set_value`, więc `read` był
    niewystarczającą bramką; sprawdzenie recenzenta poniżej zostaje jako
    dodatkowa, węższa autoryzacja, nie zamiast tej bramki).
    """
    _sprawdz_dostep_do_szansy(deal, "write")

    if not _is_reviewer():
        frappe.throw(_("Brak uprawnień do zmiany statusu audytu."), frappe.PermissionError)

    if status not in STATUSY:
        frappe.throw(_("Nieprawidłowy status: {0}").format(status))

    audyt_doc = _pobierz_audyt(deal)
    if audyt_doc is None:
        frappe.throw(_("Audyt dla tej szansy sprzedaży nie istnieje."), frappe.DoesNotExistError)

    current = audyt_doc.status

    if current == "Weryfikacja" and status == "Zatwierdzony":
        dokumenty = parsuj_mape(audyt_doc.dokumenty_json)
        zdjecia = parsuj_liste(audyt_doc.zdjecia_json)
        elementy = elementy_weryfikacji(dokumenty, zdjecia)
        weryfikacja = parsuj_mape(audyt_doc.weryfikacja_json)
        agregat = agreguj(weryfikacja, elementy)
        if not agregat["wszystkie_zaakceptowane"]:
            frappe.throw(
                _("Nie można zatwierdzić audytu — nie wszystkie elementy zostały zaakceptowane.")
            )
        wartosci = {
            "status": "Zatwierdzony",
            "zatwierdzony_przez": frappe.session.user,
            "zatwierdzony_dnia": frappe.utils.now(),
        }
        komunikat = _("Audyt zatwierdzony")
    elif current == "Zatwierdzony" and status == "Szkic":
        wartosci = {
            "status": "Szkic",
            "weryfikacja_json": "{}",
            "zatwierdzony_przez": None,
            "zatwierdzony_dnia": None,
        }
        komunikat = _("Audyt przywrócony do edycji (szkic)")
    elif current == "Weryfikacja" and status == "Szkic":
        frappe.throw(
            _("Audytu w weryfikacji nie można odesłać do poprawek — edytuj go bezpośrednio.")
        )
    else:
        frappe.throw(_("Nieprawidłowe przejście statusu audytu: {0} → {1}.").format(current, status))

    frappe.db.set_value(DOCTYPE, deal, wartosci)
    # db.set_value pomija tworzenie wersji/timeline -> odnotuj przejście jako
    # natywny komentarz Info, żeby pojawiło się w aktywności szansy.
    frappe.get_doc(DOCTYPE, deal).add_comment("Info", komunikat)

    return {"ok": True, "status": status}


@frappe.whitelist()
def volteo_audyt_cp_set_verdict(deal: str, key: str, status: str, note: str | None = None) -> dict[str, Any]:
    """Ustawia (albo cofa, dla `status="waiting"`) werdykt jednego elementu
    weryfikacji (slot dokumentu albo grupa zdjęć) — tylko recenzent, tylko
    gdy audyt jest w statusie Weryfikacja.

    `waliduj_werdykt` (rdzeń frappe-free) waliduje i normalizuje wejście,
    podnosząc `ValueError` z gotowym polskim komunikatem przy niepoprawnych
    danych (nieznany klucz, status spoza zbioru, brak notatki przy odrzuceniu,
    notatka za długa) — tu tylko zamieniamy to na `frappe.throw`.

    Read-modify-write na `weryfikacja_json` przez `frappe.db.set_value`
    (celowo, omija `lock_guard`, jak wszystkie przyciski w tym module) —
    świeży odczyt TUŻ przed zapisem, nie z wcześniej pobranego `audyt_doc`,
    żeby intencja read-modify-write była jawna (tak samo jak w poprzedniku,
    `ops/crm-audyt.py` SET_VERDICT_SCRIPT).

    Uprawnienia do szansy: `write` (SEC#35 — było `read`: ten endpoint
    zapisuje `weryfikacja_json` przez `db.set_value`, więc `read` był
    niewystarczającą bramką; sprawdzenie recenzenta poniżej zostaje jako
    dodatkowa, węższa autoryzacja, nie zamiast tej bramki).
    """
    _sprawdz_dostep_do_szansy(deal, "write")

    if not _is_reviewer():
        frappe.throw(_("Brak uprawnień do oceny elementów audytu."), frappe.PermissionError)

    audyt_doc = _pobierz_audyt(deal)
    if audyt_doc is None:
        frappe.throw(_("Audyt dla tej szansy sprzedaży nie istnieje."), frappe.DoesNotExistError)

    if audyt_doc.status != "Weryfikacja":
        frappe.throw(_("Ocena elementów możliwa tylko w statusie Weryfikacja."))

    dokumenty = parsuj_mape(audyt_doc.dokumenty_json)
    zdjecia = parsuj_liste(audyt_doc.zdjecia_json)

    try:
        wpis = waliduj_werdykt(key, status, note, dokumenty, zdjecia)
    except ValueError as exc:
        frappe.throw(str(exc))

    raw = frappe.db.get_value(DOCTYPE, deal, "weryfikacja_json")
    weryfikacja = dict(parsuj_mape(raw))

    etykieta = etykieta_dla(key)
    if status == "waiting":
        weryfikacja.pop(key, None)
        komunikat = _("Cofnięto ocenę elementu audytu: {0}").format(etykieta)
    else:
        weryfikacja[key] = {**wpis, "by": frappe.session.user, "at": frappe.utils.now()}
        if status == "accepted":
            komunikat = _("Zaakceptowano element audytu: {0}").format(etykieta)
        else:
            komunikat = _("Zgłoszono błąd w elemencie audytu: {0}").format(etykieta)
            if wpis.get("note"):
                komunikat = komunikat + _(' — „{0}”').format(wpis["note"])

    frappe.db.set_value(DOCTYPE, deal, {"weryfikacja_json": json.dumps(weryfikacja)})
    # db.set_value pomija tworzenie wersji/timeline -> odnotuj werdykt jako
    # natywny komentarz Info, żeby pojawił się w aktywności szansy.
    frappe.get_doc(DOCTYPE, deal).add_comment("Info", komunikat)

    return {"ok": True, "weryfikacja": weryfikacja}


def lock_guard(doc, method: str | None = None) -> None:
    """Before Save guard `Volteo Audyt CP` — odpowiednik `ops/crm-audyt.py`
    Lock Guard, ale jako zwykły hook forka (importy dozwolone).

    Uwaga: w Frappe `before_save` odpala się TAKŻE przy insercie, stąd
    rozgałęzienie na `doc.is_new()` na samym początku.

    Reguły dla NOWEGO dokumentu:
    1. status musi być „Szkic” — audyt zawsze zaczyna życie jako roboczy.
    2. szansa (`doc.deal`) musi istnieć i mieć `custom_rodzaj_umowy ==
       "Czyste Powietrze"` — formularz jest CP-only, nie da się go założyć
       pod szansę OZE.

    Reguły dla ISTNIEJĄCEGO dokumentu (porównanie ze stanem w bazie SPRZED
    tego zapisu):
    3. stary status „Weryfikacja” → zapis dozwolony wyłącznie recenzentowi
       (backoffice/core-admin) — to jest kanał, którym recenzent edytuje w
       miejscu zamiast odsyłać audyt do przedstawiciela.
    4. stary status „Zatwierdzony” → zapis zablokowany ZAWSZE (jedyne wyjście
       to „Przywróć do edycji” przez `volteo_audyt_cp_set_status`, które
       zapisuje przez `frappe.db.set_value` i omija ten hook).
    5. zwykły zapis nie może zmienić `status` — przejścia idą wyłącznie przez
       dedykowane przyciski (`volteo_audyt_cp_submit`/`_set_status`), które
       piszą przez `frappe.db.set_value`.
    6. anti-tamper: `weryfikacja_json` jest własnością serwera — porównanie
       SPARSOWANYCH map (nie surowych stringów, żeby `None` sprzed
       pierwszego werdyktu i `"{}"` po resecie nie fałszywie się różniły) z
       wejściem klienta. To jedyna rzecz, która realnie powstrzymuje zapis
       zwykłym `frappe.client.set_value` przed sfałszowaniem werdyktów —
       PRZED jakimkolwiek resetem tej rundy (patrz reguła 7 niżej: reset
       musi porównywać wejście użytkownika ze stanem SPRZED resetu, inaczej
       własny reset wpadłby w ten sam alarm).
    7. reset werdyktów: tylko gdy stary status to „Weryfikacja” — element,
       którego źródłowy dokument/zdjęcia się zmieniły (recenzent edytuje w
       miejscu), traci swój werdykt (`resetuj_werdykty`); komunikaty trafiają
       jako komentarze `Info`. Ta mutacja `doc.weryfikacja_json` jest legalna
       (systemowa), stąd wykonywana PO regule 6, na tej samej sparsowanej
       bazie, żeby nie wpaść we własny anti-tamper.
    8. twarde limity — ZAWSZE (nowy i istniejący dokument): maks. `MAX_ZDJEC`
       zdjęć; każdy klucz w `dokumenty_json` musi być w katalogu slotów
       (`SLOTY_DOKUMENTOW`), nic spoza formularza nie może się tam znaleźć.
    9. ślady zmian plików (ops#70): dla KAŻDEGO zapisu istniejącego dokumentu,
       niezależnie od statusu (Szkic również), diff starych i nowych
       `dokumenty_json`/`zdjecia_json` (stan sprzed TEGO zapisu — ten sam
       `stary`, który czyta reguła 6/7) przez
       `crm.volteo_aktywnosc.roznice_plikow_audytu` daje listę tekstów, z
       których każdy trafia jako osobny komentarz `Info` NA AUDYCIE (mostek w
       `crm/api/activities.py:549-588` już czyta stamtąd komentarze Info i
       pokazuje je w aktywności szansy). Niezależne od reguły 7 (reset
       werdyktów w Weryfikacji) — te komunikaty się NIE zastępują, oba mogą
       się pojawić przy tym samym zapisie w Weryfikacji; reguła 7 zostaje bez
       zmian.
    """
    if doc.is_new():
        if doc.status != "Szkic":
            frappe.throw(_("Nowy audyt musi mieć status Szkic."))
        if not doc.deal or not frappe.db.exists("CRM Deal", doc.deal):
            frappe.throw(_("Szansa sprzedaży nie istnieje."))
        rodzaj = frappe.db.get_value("CRM Deal", doc.deal, "custom_rodzaj_umowy")
        if rodzaj != "Czyste Powietrze":
            frappe.throw(
                _("Audyt specjalny CP dotyczy wyłącznie szans z rodzajem umowy Czyste Powietrze.")
            )
    else:
        stary = frappe.db.get_value(
            DOCTYPE,
            doc.name,
            ["status", "dokumenty_json", "zdjecia_json", "weryfikacja_json"],
            as_dict=True,
        )
        if stary is None:
            # Nie powinno się zdarzyć dla istniejącego dokumentu, ale zawodzimy
            # bezpiecznie (zablokuj) zamiast wywalić się na `None`.
            frappe.throw(_("Nie znaleziono istniejącego audytu do zapisu."))

        stary_status = stary.status

        if stary_status == "Weryfikacja" and not _is_reviewer():
            frappe.throw(
                _("Audyt jest w weryfikacji — edycja dostępna tylko dla back office / administratora.")
            )
        if stary_status == "Zatwierdzony":
            frappe.throw(_("Audyt zatwierdzony jest zablokowany — edycja niedostępna."))

        if doc.status != stary_status:
            frappe.throw(_("Zmiana statusu audytu możliwa tylko dedykowanymi przyciskami."))

        stara_weryfikacja = parsuj_mape(stary.weryfikacja_json)
        if parsuj_mape(doc.weryfikacja_json) != stara_weryfikacja:
            frappe.throw(_("Ocena elementów audytu możliwa tylko przez dedykowany przycisk."))

        # Reguła 9 (ops#70): ślad zmian plików — niezależnie od statusu (Szkic
        # również), na tym samym stanie sprzed zapisu co reguła 7 poniżej.
        for tekst in roznice_plikow_audytu(
            parsuj_mape(stary.dokumenty_json),
            parsuj_mape(doc.dokumenty_json),
            parsuj_liste(stary.zdjecia_json),
            parsuj_liste(doc.zdjecia_json),
            _ETYKIETY_SLOTOW,
        ):
            doc.add_comment("Info", tekst)

        if stary_status == "Weryfikacja":
            nowa_mapa, komunikaty = resetuj_werdykty(
                parsuj_mape(stary.dokumenty_json),
                parsuj_mape(doc.dokumenty_json),
                parsuj_liste(stary.zdjecia_json),
                parsuj_liste(doc.zdjecia_json),
                stara_weryfikacja,
            )
            doc.weryfikacja_json = json.dumps(nowa_mapa)
            for komunikat in komunikaty:
                doc.add_comment("Info", komunikat)

    if len(parsuj_liste(doc.zdjecia_json)) > MAX_ZDJEC:
        frappe.throw(_("Przekroczono limit {0} zdjęć.").format(MAX_ZDJEC))

    nieznane = set(parsuj_mape(doc.dokumenty_json).keys()) - _SLOTY_KLUCZE
    if nieznane:
        frappe.throw(_("Nieznany slot dokumentu: {0}").format(", ".join(sorted(nieznane))))


def delete_guard(doc, method: str | None = None) -> None:
    """On Trash guard `Volteo Audyt CP` — tylko administrator (System
    Manager / Volteo Core Admin) może usuwać, NIEZALEŻNIE od statusu.

    Świadomie surowsze niż poprzednik (`ops/crm-audyt.py` Delete Guard
    blokował usuwanie tylko dla statusu „Zatwierdzony”, Szkic mógł usunąć
    każdy): dokument audytu CP jest źródłem prawdy dla przesłanej
    dokumentacji klienta (PESEL, zaświadczenia o dochodach) od chwili
    powstania, nie dopiero po zatwierdzeniu, więc usuwanie zostaje
    zarezerwowane dla administratora na każdym etapie. `Administrator`
    przechodzi naturalnie — ma rolę `System Manager`.
    """
    if not _is_admin():
        frappe.throw(_("Tylko administrator może usunąć audyt specjalny CP."))
