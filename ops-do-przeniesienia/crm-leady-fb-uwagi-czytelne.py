# -*- coding: utf-8 -*-
"""
Volteo Frappe CRM - czytelne Uwagi na istniejacych leadach z Facebooka (b83)
============================================================================

Co to jest
----------
Od b83 webhook Make (`crm.volteo_leady_webhook`) zapisuje Uwagi
(`CRM Lead.custom_uwagi_import`) w czytelnym formacie dla call center
(decyzja wlasciciela 2026-11-04). Ten skrypt jednorazowo przepisuje stare
Uwagi leadow FB tak, by wygladaly jak z nowego webhooka.

    PRZED: Zrodlo: Facebook Lead Ads | Kampania: [S][KAMPANIA LEADOWA][WROCŁAW][27.10.2026]
           | Posiada PV: Tak, bez magazynu | System rozliczen: Stare zasady
    PO:    Kampania: Wrocław, 27.10 | Ma PV bez magazynu | System rozliczeń: stare zasady

KOLEJNOSC (wazne): skrypt importuje funkcje formatujace z obrazu aplikacji, wiec
na produkcji uruchamiac go DOPIERO po wdrozeniu obrazu b83 (inaczej blad importu).

Reguly per odcinek (separator `SEPARATOR_UWAG`, " | ")
------------------------------------------------------
- `Zrodlo: ...`                               -> usuniety (dubel pola Zrodlo)
- `Kampania: X`                               -> `Kampania: <kampania_czytelna(X)>`, na poczatek
- `Posiada PV: E` (rozpoznane)                -> `Ma PV bez magazynu` / `Ma PV z magazynem` /
                                                 `Ma PV` / `Nie ma PV`
- `Posiada PV (nierozpoznane): X`             -> bez zmian
- `System rozliczen: E`                       -> `System rozliczeń: stare zasady` /
                                                 `nowe zasady (net-billing)`
- `System rozliczen (<wariant>): E`           -> `System rozliczeń (<wariant>): ...`
- `Data zgloszenia (brak): ...`               -> usuniety (szum techniczny)
- `Data zgloszenia (nierozpoznana): X`        -> `Data zgłoszenia (nierozpoznana): X`
- `Kod pocztowy (nierozpoznany): X`           -> `Kod pocztowy (do sprawdzenia): X`
- `Kod pocztowy spoza bazy kodów, ...`        -> `UWAGA_KOD_SPOZA_BAZY` (krotsza)
- `Produkt (nierozpoznany): X`                -> usuniety (decyzja 2026-11-04, produkt z reklamy)
- `Lokalizacja uzupelniona ...`               -> usuniety (decyzja wlasciciela 2026-11-04)
- `pytanie_ze_slugiem: odpowiedz_slug`        -> po ludzku (`pytanie_formularza`)
- kazdy inny odcinek (np. reczna notatka CC)  -> BEZ ZMIAN, w tej samej kolejnosci

Ponowne zgloszenie (ops#324): stary odcinek
`Ponowne zgłoszenie FB 2026-11-02 (lead FB <id>): Zrodlo: ... | Kampania: ... | ...`
ma w srodku ten sam separator. Blok wewnetrzny to kolejne odcinki znanych typow
webhooka, az do odcinka nieznanego, nastepnego ponownego zgloszenia albo
powtorzenia typu (druga `Kampania:`). Blok jest skladany przez
`zloz_linie_ponownego_zgloszenia` z aplikacji, czyli tak jak w nowym webhooku:
`Ponowne zgłoszenie 02.11: Szczecin, 27.10 (lead FB <id>)`.

Zakres: leady `custom_import_source = "FB"` (wszystkie reguly) ORAZ leady innych
zrodel z ponownym zgloszeniem FB w Uwagach (tylko bloki ponownego zgloszenia,
reszta ich Uwag bez zmian).

Bezpieczniki
------------
- Znacznik idempotencji webhooka `lead FB <id>)` musi przetrwac: kazdy znacznik
  z tekstu PRZED musi byc w tekscie PO, inaczej skrypt przerywa (wyjatek).
- Compare-and-set: tuz przed zapisem Uwagi czytane sa ponownie; gdy zmienily sie
  od odczytu (np. webhook dopisal zgloszenie), lead jest pomijany i raportowany.
- Skrypt nigdy nie drukuje tresci Uwag (dane osobowe), tylko ID i liczby.
  Wyjatek: lista `PODGLAD` z nazwami leadow, ktore operator chce zobaczyc PRZED/PO.
- Backup w trybie `wykonaj`: JSON {nazwa: stare Uwagi} w prywatnych plikach site'u
  (sciezka drukowana). Zawiera dane osobowe: usunac po potwierdzeniu wyniku.
- Bez sladu w Aktywnosci: `frappe.db.set_value(..., update_modified=False)`, jeden
  `frappe.db.commit()` na koncu. Bez SMS (SMS wysyla tylko webhook).
- Idempotentny: drugi przebieg ma 0 zmian (nowy format nie pasuje do starych regul).

Jak uruchomic (bench console, wzorzec base64 + exec)
----------------------------------------------------
    SITE=crm.proenergy.pro
    B64=$(base64 < ops/crm-leady-fb-uwagi-czytelne.py | tr -d '\\n')
    printf 'import base64\\nexec(base64.b64decode("%s").decode(), {})\\n' "$B64" \\
      | ssh ovh "docker compose -p crm exec -T backend bench --site $SITE console"

Lokalnie (`crm.localhost`, stos `~/Documents/volteo-local`):
    cd ~/Documents/volteo-local
    B64=$(base64 < ops/crm-leady-fb-uwagi-czytelne.py | tr -d '\\n')
    printf 'import base64\\nexec(base64.b64decode("%s").decode(), {})\\n' "$B64" \\
      | docker compose exec -T backend bench --site crm.localhost console

TRYB
----
    TRYB = "dry"       (domyslny) - raport, nic nie zapisuje.
    TRYB = "wykonaj"   - backup, zapis, jawny commit, blok VERIFY.
"""

import json
import re
from collections import Counter

try:
    import frappe
except ImportError:  # test czystej funkcji bez frappe
    frappe = None

SEP = " | "
ZNACZNIK = re.compile(r"lead FB [^)]*\)")
PONOWNE_STARE = re.compile(r"^Ponowne zgłoszenie FB (\S*) \(lead FB ([^)]*)\): ?(.*)$", re.S)

# Typy odcinkow starego webhooka (prefiks -> typ). Kolejnosc ma znaczenie (dluzsze najpierw).
_TYPY = (
    ("Zrodlo: ", "zrodlo"),
    ("Formularz: ", "formularz"),
    ("Kampania: ", "kampania"),
    ("Posiada PV (nierozpoznane): ", "pv_nierozpoznane"),
    ("Posiada PV: ", "pv"),
    ("System rozliczen (", "system_wariant"),
    ("System rozliczen: ", "system"),
    ("Data zgloszenia (brak)", "data_brak"),
    ("Data zgloszenia (nierozpoznana): ", "data_nierozpoznana"),
    ("Kod pocztowy (nierozpoznany): ", "kod_nierozpoznany"),
    ("Kod pocztowy spoza bazy kodów", "kod_spoza_bazy"),
    ("Produkt (nierozpoznany): ", "produkt"),
    ("Lokalizacja uzupelniona", "lokalizacja"),
)


def typ_odcinka(segment):
    """Typ odcinka starego formatu albo "slug" (pytanie z podkreslnikiem) albo None."""
    for prefiks, typ in _TYPY:
        if segment.startswith(prefiks):
            return typ
    klucz, dwukropek, _ = segment.partition(": ")
    if dwukropek and "_" in klucz:
        return "slug"
    return None


def _odwrotny(slownik):
    """{etykieta.lower(): wartosc} ze slownika `ODPOWIEDZI_*` aplikacji."""
    return {etykieta.lower(): wartosc for wartosc, etykieta in slownik.values()}


def konwertuj_odcinek(segment, h, liczniki):
    """Jeden odcinek starego formatu -> (nowy odcinek albo None, wartosc_pv, wartosc_zasad).

    `h` to slownik funkcji i stalych z aplikacji (patrz `pomocnicy_z_aplikacji`).
    Wartosci PV/zasad sa zwracane tylko dla rozpoznanych odcinkow (inaczej None)."""
    typ = typ_odcinka(segment)
    if typ in ("zrodlo", "data_brak", "produkt", "lokalizacja"):
        liczniki["usuniety: " + typ] += 1
        return None, None, None
    if typ == "kampania":
        stara = segment[len("Kampania: ") :]
        nowa = h["kampania_czytelna"](stara)
        liczniki["kampania skrocona" if nowa != stara else "kampania bez zmian"] += 1
        return h["PREFIKS_KAMPANII"] + nowa, None, None
    if typ == "pv":
        etykieta = segment[len("Posiada PV: ") :]
        wartosc = h["pv_z_etykiety"].get(etykieta.lower())
        if wartosc is None:
            wartosc = h["rozpoznaj_posiada_pv"](etykieta)[0]
        if wartosc is None:
            liczniki["pv nierozpoznane (bez zmian)"] += 1
            return segment, None, None
        wartosc = h["normalizuj_posiadane_produkty"](wartosc) if wartosc else ""
        liczniki["pv czytelne"] += 1
        return h["opis_posiada_pv"](wartosc, etykieta), wartosc, None
    if typ == "system":
        etykieta = segment[len("System rozliczen: ") :]
        zasady = h["zasady_z_etykiety"].get(etykieta.lower()) or h["rozpoznaj_system_rozliczen"](etykieta)[0]
        liczniki["system czytelny"] += 1
        if zasady is None:
            return h["PREFIKS_SYSTEMU"] + etykieta, None, None
        return h["PREFIKS_SYSTEMU"] + h["OPISY_ZASAD"][zasady], None, zasady
    if typ == "system_wariant":
        reszta = segment[len("System rozliczen ") :]
        wariant, dwukropek, etykieta = reszta.partition(": ")
        if dwukropek and wariant != "(nierozpoznane)":
            zasady = h["zasady_z_etykiety"].get(etykieta.lower()) or h["rozpoznaj_system_rozliczen"](etykieta)[0]
            if zasady is not None:
                etykieta = h["OPISY_ZASAD"][zasady]
        liczniki["system wariant"] += 1
        return "System rozliczeń %s%s%s" % (wariant, dwukropek, etykieta), None, None
    if typ == "data_nierozpoznana":
        liczniki["data nierozpoznana"] += 1
        return "Data zgłoszenia (nierozpoznana): " + segment[len("Data zgloszenia (nierozpoznana): ") :], None, None
    if typ == "kod_nierozpoznany":
        liczniki["kod do sprawdzenia"] += 1
        return "Kod pocztowy (do sprawdzenia): " + segment[len("Kod pocztowy (nierozpoznany): ") :], None, None
    if typ == "kod_spoza_bazy":
        liczniki["kod spoza bazy"] += 1
        return h["UWAGA_KOD_SPOZA_BAZY"], None, None
    if typ == "slug":
        pytanie, _, odpowiedz = segment.partition(": ")
        liczniki["odpowiedz po ludzku"] += 1
        return "%s: %s" % (h["pytanie_formularza"](pytanie), h["tekst_formularza"](odpowiedz)), None, None
    if typ in ("formularz", "pv_nierozpoznane"):
        return segment, None, None
    liczniki["nieznany (bez zmian)"] += 1
    return segment, None, None


def _blok_ponownego(segmenty, start):
    """Indeks konca (wylacznie) bloku wewnetrznego starego ponownego zgloszenia."""
    widziane = set()
    koniec = start
    while koniec < len(segmenty):
        segment = segmenty[koniec]
        typ = typ_odcinka(segment)
        if segment.startswith("Ponowne zgłoszenie") or typ is None or typ in ("lokalizacja", "kod_spoza_bazy"):
            break
        if typ != "slug" and typ in widziane:
            break
        widziane.add(typ)
        koniec += 1
    return koniec


def przepisz(uwagi, pola, h, z_fb=True):
    """Czysta logika per lead. Zwraca (nowe_uwagi, Counter liczniki).

    `pola` to pola leada (`custom_posiadane_produkty`, `custom_zasady_dotacji`) do
    porownania w ponownym zgloszeniu. `z_fb=False` (lead z arkusza): przepisywane sa
    tylko bloki ponownego zgloszenia. Rzuca ValueError, gdy zginalby znacznik."""
    liczniki = Counter()
    uwagi = uwagi or ""
    segmenty = uwagi.split(SEP) if uwagi else []
    wynik = []
    i = 0
    while i < len(segmenty):
        segment = segmenty[i]
        stare = PONOWNE_STARE.match(segment)
        if stare:
            data_iso, lead_id, pierwszy = stare.groups()
            wnetrze = [pierwszy] if pierwszy else []
            koniec = _blok_ponownego(segmenty, i + 1)
            wnetrze += segmenty[i + 1 : koniec]
            nowe, pv, zasady = [], None, None
            for w in wnetrze:
                n, w_pv, w_zas = konwertuj_odcinek(w, h, Counter())
                pv = w_pv if w_pv is not None else pv
                zasady = w_zas if w_zas is not None else zasady
                if n:
                    nowe.append(n)
            wynik.append(h["zloz_linie_ponownego_zgloszenia"](data_iso, lead_id, nowe, pv, zasady, pola))
            liczniki["ponowne zgloszenie"] += 1
            i = koniec
            continue
        if z_fb:
            nowy, _, _ = konwertuj_odcinek(segment, h, liczniki)
            if nowy:
                wynik.append(nowy)
        else:
            wynik.append(segment)
        i += 1
    if z_fb:
        idx = next((k for k, s in enumerate(wynik) if s.startswith(h["PREFIKS_KAMPANII"])), None)
        if idx:
            wynik = [wynik[idx]] + wynik[:idx] + wynik[idx + 1 :]
    nowe_uwagi = SEP.join(wynik)
    brakujace = set(ZNACZNIK.findall(uwagi)) - set(ZNACZNIK.findall(nowe_uwagi))
    if brakujace:
        raise ValueError("Zginalby znacznik idempotencji: %s" % sorted(brakujace))
    return nowe_uwagi, liczniki


def pomocnicy_z_aplikacji():
    """Funkcje i stale z obrazu aplikacji (b83+)."""
    from crm.volteo_leady_import import normalizuj_posiadane_produkty
    from crm import volteo_leady_webhook as w

    return {
        "kampania_czytelna": w.kampania_czytelna,
        "opis_posiada_pv": w.opis_posiada_pv,
        "rozpoznaj_posiada_pv": w.rozpoznaj_posiada_pv,
        "rozpoznaj_system_rozliczen": w.rozpoznaj_system_rozliczen,
        "normalizuj_posiadane_produkty": normalizuj_posiadane_produkty,
        "pv_z_etykiety": _odwrotny(w.ODPOWIEDZI_POSIADA_PV),
        "zasady_z_etykiety": _odwrotny(w.ODPOWIEDZI_SYSTEM_ROZLICZEN),
        "OPISY_ZASAD": w.OPISY_ZASAD,
        "PREFIKS_KAMPANII": w.PREFIKS_KAMPANII,
        "PREFIKS_SYSTEMU": w.PREFIKS_SYSTEMU,
        "UWAGA_KOD_SPOZA_BAZY": w.UWAGA_KOD_SPOZA_BAZY,
        "pytanie_formularza": w.pytanie_formularza,
        "tekst_formularza": w.tekst_formularza,
        "zloz_linie_ponownego_zgloszenia": w.zloz_linie_ponownego_zgloszenia,
    }


if frappe is not None:
    # =================================================================
    # KONFIGURACJA
    # =================================================================
    TRYB = "dry"  # "dry" | "wykonaj"
    PODGLAD = []  # nazwy leadow, dla ktorych wydrukowac PRZED/PO (dane osobowe!)

    if TRYB not in ("dry", "wykonaj"):
        frappe.throw(f"Nieprawidlowy TRYB: {TRYB!r} (dozwolone: 'dry', 'wykonaj')")

    from crm.volteo_leady_import import SEPARATOR_UWAG

    if SEPARATOR_UWAG != SEP:
        frappe.throw("SEPARATOR_UWAG w aplikacji to %r, skrypt zaklada %r" % (SEPARATOR_UWAG, SEP))

    H = pomocnicy_z_aplikacji()
    POLA = [
        "name",
        "custom_import_source",
        "custom_uwagi_import",
        "custom_posiadane_produkty",
        "custom_zasady_dotacji",
    ]

    def kandydaci():
        fb = frappe.get_all("CRM Lead", filters={"custom_import_source": "FB"}, fields=POLA, limit_page_length=0)
        scalone = frappe.get_all(
            "CRM Lead",
            filters={"custom_uwagi_import": ["like", "%Ponowne zgłoszenie FB %"]},
            fields=POLA,
            limit_page_length=0,
        )
        po_nazwie = {ld.name: ld for ld in fb + scalone}
        return [po_nazwie[n] for n in sorted(po_nazwie)]

    def policz(leady):
        zmiany, suma, bledy = {}, Counter(), {}
        for ld in leady:
            try:
                nowe, liczniki = przepisz(ld.custom_uwagi_import, ld, H, z_fb=ld.custom_import_source == "FB")
            except ValueError as e:
                bledy[ld.name] = str(e)
                continue
            suma.update(liczniki)
            if nowe != (ld.custom_uwagi_import or ""):
                zmiany[ld.name] = nowe
        return zmiany, suma, bledy

    leady = kandydaci()
    oryginaly = {ld.name: ld.custom_uwagi_import or "" for ld in leady}
    zmiany, suma, bledy = policz(leady)

    nieznane = sorted(
        ld.name
        for ld in leady
        if ld.custom_import_source == "FB"
        and any(typ_odcinka(s) is None and not s.startswith("Ponowne zgłoszenie") for s in oryginaly[ld.name].split(SEP) if s)
        and ld.name in zmiany
    )
    edytowane = sorted(
        set(
            frappe.get_all(
                "Version",
                filters={"ref_doctype": "CRM Lead", "data": ["like", "%custom_uwagi_import%"]},
                pluck="docname",
                limit_page_length=0,
            )
        )
        & set(zmiany)
    )

    print("=" * 70)
    print("TRYB:", TRYB)
    print("Kandydaci:", len(leady), "(FB: %d)" % sum(1 for ld in leady if ld.custom_import_source == "FB"))
    print("Do zmiany:", len(zmiany), "| bez zmian:", len(leady) - len(zmiany) - len(bledy))
    print("Odcinki:")
    for klucz, ile in sorted(suma.items()):
        print("   %-32s %d" % (klucz, ile))
    print("Leady z odcinkiem nieznanym (zostaje bez zmian, sprawdz recznie):", len(nieznane), nieznane)
    print("Leady z reczna edycja Uwag w historii (przepisane, nieznane odcinki zostaja):", len(edytowane), edytowane)
    if bledy:
        print("BLAD, znacznik by zginal (lead pominiety):", bledy)
    for nazwa in PODGLAD:
        if nazwa in oryginaly:
            print("-" * 70)
            print(nazwa, "PRZED:", oryginaly[nazwa])
            print(nazwa, "PO:   ", zmiany.get(nazwa, oryginaly[nazwa]))

    if TRYB == "wykonaj" and zmiany:
        sciezka = frappe.get_site_path(
            "private", "files", "backup-uwagi-fb-%s.json" % frappe.utils.now_datetime().strftime("%Y%m%d-%H%M%S")
        )
        with open(sciezka, "w", encoding="utf-8") as plik:
            json.dump({n: oryginaly[n] for n in zmiany}, plik, ensure_ascii=False, indent=1)
        print("Backup:", sciezka, "(dane osobowe, usunac po potwierdzeniu)")

        zapisane, zmienione_w_trakcie = 0, []
        for nazwa, nowe in zmiany.items():
            teraz = frappe.db.get_value("CRM Lead", nazwa, "custom_uwagi_import") or ""
            if teraz != oryginaly[nazwa]:
                zmienione_w_trakcie.append(nazwa)
                continue
            frappe.db.set_value("CRM Lead", nazwa, {"custom_uwagi_import": nowe}, update_modified=False)
            zapisane += 1
        frappe.db.commit()
        print("Zapisane:", zapisane, "| pominiete (zmienione w trakcie):", zmienione_w_trakcie)

    # VERIFY: po zapisie drugi przebieg ma 0 zmian; znaczniki zachowane
    po = kandydaci()
    zmiany_po, _, bledy_po = policz(po)
    znaczniki_przed = sum(len(ZNACZNIK.findall(t)) for t in oryginaly.values())
    znaczniki_po = sum(len(ZNACZNIK.findall(ld.custom_uwagi_import or "")) for ld in po)
    print("=" * 70)
    print("VERIFY: do zmiany teraz:", len(zmiany_po), "(po 'wykonaj' oczekiwane 0)")
    print("VERIFY: znaczniki 'lead FB <id>)' przed/po:", znaczniki_przed, znaczniki_po)
    print("VERIFY: bledy:", len(bledy_po))
