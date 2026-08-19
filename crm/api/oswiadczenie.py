"""Whitelisted API oraz brama `before_request` „Oświadczenia o zachowaniu
poufności" (bramka NDA przy pierwszym logowaniu, doctype `Volteo Oswiadczenie
Poufnosci` + Single `Volteo Oswiadczenie Ustawienia`).

Schemat obu doctype'ów jest tworzony ODDZIELNYM skryptem ops i w chwili, gdy
ten moduł zaczyna działać, MOŻE JESZCZE NIE ISTNIEĆ na danej instalacji (kolejność
wdrożenia: schemat najpierw, obraz drugi — patrz CLAUDE.md). `_wymaga_oswiadczenia`
dlatego celowo failuje OTWARCIE (zwraca `False`) na dowolny wyjątek: błąd w tej
bramce nie może zablokować całego CRM-a, bo brakujący schemat to nie-zdarzenie,
nie awaria.

Rdzeń frappe-free (`crm.volteo_oswiadczenie`) dostarcza treść dokumentu, jego
sumę kontrolną wersji, generator PDF-u i porównanie imion — ten moduł tylko
spina go z Frappe: sesją, bazą, cache'em, plikami i pocztą.
"""

from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import formatdate, get_datetime, now, nowdate

from crm.volteo_oswiadczenie import imiona_zgodne, wersja_tresci, zbuduj_pdf, zbuduj_tresc

DOCTYPE = "Volteo Oswiadczenie Poufnosci"
SINGLE = "Volteo Oswiadczenie Ustawienia"

_CACHE_KLUCZ = "volteo_osw_ok"
"""Klucz hasha w cache Frappe (`frappe.cache`); pole = nazwa usera, wartość =
`"ok"` gdy podpisał. Cache'ujemy WYŁĄCZNIE werdykty pozytywne (podpisał) —
nigdy negatywne ("jeszcze nie podpisał"), żeby świeżo podpisane oświadczenie
od razu odblokowało dostęp bez czekania na wygaśnięcie wpisu."""

_ALLOWLIST = frozenset(
    {
        # Logowanie/wylogowanie — bez tego nikt nie wejdzie do aplikacji.
        "login",
        "logout",
        # Standardowe odczyty sesji/pulsu, używane przez frappe-ui i typowe
        # przepływy health-check/keep-alive; muszą przejść niezależnie od
        # stanu bramki, bo są tańsze i bardziej fundamentalne niż samo NDA.
        "frappe.auth.get_logged_user",
        "frappe.ping",
        # Router SPA czeka na `users.promise` (frontend/src/stores/users.js:17,
        # `usersStore().users`) PRZED jakąkolwiek nawigacją
        # (frontend/src/router.js:239-254, `await users.promise`) — zablokowanie
        # tego wywołania zawiesza routing w nieskończonej próbie (żadnego
        # przekierowania do gate'u, bo `beforeEach` nigdy się nie kończy).
        "crm.api.session.get_users",
        # Trzy endpointy samej bramki — czytane/wołane właśnie PRZEZ
        # użytkownika, który jeszcze nie podpisał.
        "crm.api.oswiadczenie.volteo_oswiadczenie_status",
        "crm.api.oswiadczenie.volteo_oswiadczenie_tresc",
        "crm.api.oswiadczenie.volteo_podpisz_oswiadczenie",
    }
)
"""Metody `/api/method/<dotted>` przepuszczane bez sprawdzania bramki NDA.

CELOWO bez `frappe.client.get_single_value` — ta metoda czyta DOWOLNY Single
po nazwie pola (m.in. `Volteo Kalkulator Stale`, ceny/marże kalkulatora), więc
jej odblokowanie byłoby furtką do danych kosztowych. Router SPA już woła ją
wyłącznie wewnątrz try/catch z fail-open (`frontend/src/router.js:14-26`,
`shouldCapturePersona`) — zablokowanie jej pod NDA-bramką degraduje się tam do
"kreator person nieaktywny", nie do błędu widocznego użytkownikowi.

CELOWO bez jakiegokolwiek `/api/resource/*` — ścieżki resource są zawsze
blokowane niżej w `before_request`, niezależnie od tej listy."""


def _wymaga_oswiadczenia(user: str | None) -> bool:
    """Kanoniczny predykat: czy `user` musi podpisać oświadczenie, zanim
    dostanie dostęp do danych CRM.

    `False` dla `Guest`/`Administrator`/pustego usera — Administrator jest
    kontem technicznym, nie osobą składającą oświadczenie. Cała reszta ciała
    jest owinięta w try/except: wyjątek (brakujący schemat, błąd bazy, cokolwiek)
    NIGDY nie ma prawa zablokować całego CRM-a — failujemy OTWARCIE i logujemy.
    """
    if not user or user in ("Guest", "Administrator"):
        return False

    try:
        if not frappe.db.exists("DocType", SINGLE):
            return False

        ustawienia = frappe.db.get_singles_dict(SINGLE)
        data_graniczna = ustawienia.get("data_graniczna") if ustawienia else None
        if not data_graniczna:
            frappe.log_error(
                title="Volteo Oświadczenie: brak daty granicznej",
                message=(
                    f"{SINGLE}.data_graniczna jest pusta/nieustawiona — bramka NDA "
                    "pozostaje wyłączona (fail-open) do czasu jej ustawienia."
                ),
            )
            return False

        utworzenie_konta = frappe.db.get_value("User", user, "creation")
        if not utworzenie_konta or get_datetime(utworzenie_konta) < get_datetime(data_graniczna):
            return False

        if frappe.cache.hget(_CACHE_KLUCZ, user) == "ok":
            return False

        if not frappe.db.exists("DocType", DOCTYPE):
            return False

        if frappe.db.exists(DOCTYPE, {"user": user}):
            frappe.cache.hset(_CACHE_KLUCZ, user, "ok")
            return False

        return True
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Volteo Oświadczenie: błąd bramki NDA (fail-open)",
        )
        return False


_ALLOWED_PREFIXES = ("/api/method/", "/api/v2/method/")
"""Prefiksy ścieżek, spod których wyciągamy dotted method name do sprawdzenia
przeciw `_ALLOWLIST`. Wszystko inne pod `/api/` (w tym CAŁE `/api/resource/*`)
jest blokowane bez wyjątku, gdy bramka jest wymagana."""


def _dotted_method_z_path(path: str) -> str | None:
    """Wyciąga `<dotted>` z `/api/method/<dotted>` lub `/api/v2/method/<dotted>`;
    `None`, gdy ścieżka nie pasuje do żadnego z tych dwóch kształtów (np.
    `/api/resource/...`)."""
    for prefiks in _ALLOWED_PREFIXES:
        if path.startswith(prefiks):
            return path[len(prefiks) :].strip("/")
    return None


def before_request() -> None:
    """Hook `before_request` (`crm.hooks`): blokuje każde wywołanie `/api/*`
    dla użytkownika wymagającego podpisania oświadczenia, poza wąską
    `_ALLOWLIST`.

    Celowo NIE gate'uje `/crm` (strona SPA) ani `/assets` — aplikacja musi się
    w ogóle wczytać w przeglądarce, żeby zdążyła pokazać ekran bramki; gate'owanie
    samej strony zostawiłoby użytkownika z białym ekranem bez żadnego UI do
    podpisania. Prywatne pliki (`/private/files/...`) też nie przechodzą tędy —
    rządzą nimi zwykłe uprawnienia doctype'u `File`, nie ta bramka.

    Musi być tanie i defensywne: wywoływane na KAŻDYM requeście do `/api/`, więc
    żaden krok przed finalnym `frappe.throw` nie może rzucić niespodziewanie —
    `_wymaga_oswiadczenia` sama jest już w try/except, więc jedyne ryzyko tutaj
    to odczyt `frappe.local`/`frappe.session`, zabezpieczony `getattr`.
    """
    request = getattr(frappe.local, "request", None)
    if request is None or not getattr(request, "path", "").startswith("/api/"):
        return

    user = getattr(frappe.session, "user", None) if hasattr(frappe.local, "session") else None
    if not user or user in ("Guest", "Administrator"):
        return

    dotted = _dotted_method_z_path(request.path)
    if dotted is not None and dotted in _ALLOWLIST:
        return

    if _wymaga_oswiadczenia(user):
        frappe.throw(
            _(
                "Dostęp zablokowany do czasu podpisania oświadczenia o zachowaniu "
                "poufności."
            ),
            frappe.PermissionError,
        )


@frappe.whitelist()
def volteo_oswiadczenie_status() -> dict[str, Any]:
    """Zwraca `{"wymaga": bool}` — czy zalogowany użytkownik musi podpisać
    oświadczenie. Frontend woła to przy starcie aplikacji, żeby zdecydować,
    czy pokazać bramkę."""
    return {"wymaga": _wymaga_oswiadczenia(frappe.session.user)}


def _pelne_imie_i_nazwisko(user: str) -> str:
    """Zwraca `User.full_name` dla `user`; rzuca czytelny polski błąd, gdy
    puste/białoznakowe — konto bez imienia i nazwiska nie może wygenerować
    ani podpisać spersonalizowanego oświadczenia."""
    full_name = frappe.db.get_value("User", user, "full_name")
    if not full_name or not full_name.strip():
        frappe.throw(
            _(
                "Twoje konto nie ma ustawionego imienia i nazwiska — skontaktuj się "
                "z administratorem systemu przed podpisaniem oświadczenia."
            )
        )
    return full_name


@frappe.whitelist()
def volteo_oswiadczenie_tresc() -> dict[str, Any]:
    """Zwraca spersonalizowaną treść oświadczenia dla zalogowanego użytkownika
    do wyświetlenia przed podpisaniem: `{"tresc", "imie_nazwisko", "wersja"}`.

    Odmawia (403), gdy użytkownik oświadczenia w ogóle nie potrzebuje —
    serwowanie spersonalizowanego dokumentu komuś, kto już podpisał (albo
    nigdy nie musiał), nie ma sensu i mogłoby mylić UI."""
    if not _wymaga_oswiadczenia(frappe.session.user):
        frappe.throw(_("To oświadczenie Cię nie dotyczy."), frappe.PermissionError)

    full_name = _pelne_imie_i_nazwisko(frappe.session.user)
    data_str = formatdate(nowdate(), "dd.MM.yyyy")

    return {
        "tresc": zbuduj_tresc(full_name, data_str),
        "imie_nazwisko": full_name,
        "wersja": wersja_tresci(),
    }


def _wstaw_plik_oswiadczenia(rekord: "frappe.model.document.Document", pdf: bytes) -> None:
    """Wstawia `File` z bajtami PDF-u, podpina go pod `rekord`, i zapisuje
    `file_url` z powrotem na `rekord.plik` — wzorzec z `crm.api.umowa.volteo_umowa_pdf`."""
    nazwa_pliku = f"oswiadczenie-poufnosci-{rekord.name}.pdf"
    plik = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": nazwa_pliku,
            "attached_to_doctype": DOCTYPE,
            "attached_to_name": rekord.name,
            "is_private": 1,
            "content": pdf,
        }
    )
    plik.insert(ignore_permissions=True)
    rekord.db_set("plik", plik.file_url, update_modified=False)


def _wyslij_kopie_mailem(user: str, pdf: bytes) -> None:
    """Wysyła podpisany PDF mailem jako kopię dla użytkownika. CAŁOŚĆ w
    try/except: lokalny stack nie ma skonfigurowanego konta pocztowego, więc
    to wywołanie MA prawo się nie udać — nieudana wysyłka nigdy nie może
    cofnąć ani zablokować już zapisanego podpisania."""
    try:
        frappe.sendmail(
            recipients=[user],
            subject=_("Oświadczenie o zachowaniu poufności — kopia podpisanego dokumentu"),
            message=_(
                "Dziękujemy za podpisanie oświadczenia o zachowaniu poufności. "
                "W załączniku znajduje się kopia podpisanego dokumentu."
            ),
            attachments=[{"fname": "oswiadczenie-poufnosci.pdf", "fcontent": pdf}],
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Volteo Oświadczenie: nie udało się wysłać kopii mailem",
        )


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=60)
def volteo_podpisz_oswiadczenie(imie_nazwisko: str) -> dict[str, Any]:
    """Zapisuje podpisanie oświadczenia dla zalogowanego użytkownika:
    weryfikuje zgodność wpisanego imienia i nazwiska z kontem, generuje PDF
    (renderowany na podstawie `User.full_name` — autorytatywnej tożsamości
    konta; wpisany string zostaje osobno jako `imie_nazwisko`, dowód samego
    aktu), zapisuje rekord `Volteo Oswiadczenie Poufnosci` + załącznik, i
    wysyła kopię mailem (best-effort). Zwraca `{"ok": True}`.

    Idempotentne na podwójne kliknięcie: jeśli bramka już nie wymaga podpisu
    (bo poprzednie żądanie zdążyło się zapisać), a rekord istnieje, zwraca
    sukces zamiast błędu."""
    user = frappe.session.user

    if not _wymaga_oswiadczenia(user):
        if frappe.db.exists(DOCTYPE, {"user": user}):
            return {"ok": True}
        frappe.throw(_("To oświadczenie Cię nie dotyczy."), frappe.PermissionError)

    full_name = _pelne_imie_i_nazwisko(user)

    if not imiona_zgodne(imie_nazwisko, full_name):
        frappe.throw(
            _("Wpisane imię i nazwisko nie zgadza się z danymi konta."),
            frappe.ValidationError,
        )

    data_str = formatdate(nowdate(), "dd.MM.yyyy")
    pdf = zbuduj_pdf(full_name, data_str)

    try:
        rekord = frappe.get_doc(
            {
                "doctype": DOCTYPE,
                "user": user,
                "imie_nazwisko": imie_nazwisko.strip(),
                "podpisano": now(),
                "adres_ip": frappe.local.request_ip,
                "wersja_tresci": wersja_tresci(),
            }
        )
        rekord.insert(ignore_permissions=True)
    except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
        # Wyścig: inna sesja/kliknięcie zdążyło zapisać rekord między
        # sprawdzeniem `_wymaga_oswiadczenia` a tym insertem — traktujemy to
        # jak "już podpisane", nie jak błąd.
        frappe.cache.hset(_CACHE_KLUCZ, user, "ok")
        return {"ok": True}

    _wstaw_plik_oswiadczenia(rekord, pdf)

    frappe.cache.hset(_CACHE_KLUCZ, user, "ok")

    _wyslij_kopie_mailem(user, pdf)

    return {"ok": True}


def po_usunieciu_oswiadczenia(doc: "frappe.model.document.Document", method: str | None = None) -> None:
    """`on_trash` na `Volteo Oswiadczenie Poufnosci`: usuwa pozytywny werdykt
    z cache'a, żeby usunięcie rekordu (np. cofnięcie przez admina) natychmiast
    wymusiło ponowne podpisanie zamiast serwować stare "ok" aż do wygaśnięcia."""
    frappe.cache.hdel(_CACHE_KLUCZ, doc.user)
