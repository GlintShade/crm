# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Zarządzanie kontami Volteo — zakładanie użytkowników i nadawanie ról
======================================================================

Model uprawnień
----------------
`Volteo Core Admin` (poziom zarządu) może zakładać konta i nadawać role z
zamkniętej białej listy `NADAWALNE_ROLE`, WŁĄCZNIE z nadawaniem samej roli
`Volteo Core Admin` — właściciel świadomie zgodził się, by Core Admin mógł
tworzyć sobie równych. Jedyną twardą granicą jest `System Manager`.

Dlaczego `System Manager` jest wykluczona bezwzględnie
--------------------------------------------------------
`System Manager` to rola PLATFORMOWA, nie biznesowa: daje edycję Server
Scriptów (dowolny kod na serwerze), zmianę uprawnień innych ról i kasowanie
doctypów. To furtka do przejęcia całej instalacji, nie kolejny szczebel
hierarchii sprzedażowej. Dlatego nie ma tu żadnego wyjątku "chyba że wołający
sam ją ma" — por. `crm.api.invite_by_email`, gdzie wołający z `System
Manager` MOŻE zapraszać do `System Manager`. Tutaj celowo NIE powielamy tego
wyjątku: jedna reguła, jedna ścieżka, łatwa do zaudytowania. Ktoś, kto
potrzebuje nadać `System Manager`, ma do tego Desk (`/app/user`) i pełne
uprawnienia Frappe — ten moduł nie jest i nie będzie do tego furtką.

Rola bazowa `Sales User` jest dodawana zawsze
------------------------------------------------
Zweryfikowane czytając `get_session_role_flags()` w `crm/api/session.py`:
ta funkcja rzuca `frappe.PermissionError`, jeśli role sesji nie przecinają
się ze zbiorem `CRM_ALLOWED_ROLES = ["System Manager", "Sales Manager",
"Sales User"]`, i jest wywoływana na każdym starcie sesji CRM (m.in. przez
`get_users`). Żadna rola `Volteo *` nie należy do tego zbioru — użytkownik
mający WYŁĄCZNIE np. `Volteo D2D Sales` zostałby odrzucony przy pierwszym
kontakcie z aplikacją. Stąd `volteo_utworz_uzytkownika` zawsze dokłada
`Sales User` obok roli Volteo, a `volteo_zmien_role` nigdy jej nie usuwa i
dokłada, jeśli z jakiegoś powodu brakuje jej na koncie.

Wzorzec zaczerpnięty z `crm.api.invite_by_email` i `crm.api.user.remove_roles`
--------------------------------------------------------------------------------
Bramka wejścia (`frappe.only_for`), jawna odmowa nadania roli własnego
poziomu-lub-wyższego oraz walidacja względem twardej białej listy powtarzają
kształt `invite_by_email`. Usuwanie ról z tabeli potomnej `roles` powtarza
kształt `remove_roles()` z `crm/api/user.py` (`doc.get("roles").remove(row)`,
nie `doc.remove(row)`).

Czego NIE robimy inaczej niż `invite_by_email`, i dlaczego
--------------------------------------------------------------
`invite_by_email` tworzy `CRM Invitation` i wysyła e-mail z linkiem. Ta
instalacja nie ma skonfigurowanego konta e-mail — link zaproszenia nigdy by
nie dotarł. Dlatego `volteo_utworz_uzytkownika` zakłada konto OD RAZU, z
hasłem wygenerowanym serwerowo i zwróconym w odpowiedzi DOKŁADNIE RAZ; dalsze
przekazanie hasła użytkownikowi odbywa się poza tym API (ustnie / komunikator
zaufanego kanału), tak jak w `ops/crm-onboard-users.py`.

Hasło nigdy nie trafia do logów: nie jest przekazywane do `frappe.log_error`,
`print` ani jakiegokolwiek komunikatu (`frappe.msgprint`/`frappe.throw`), i
nie jest nigdzie zapisywane jawnie — ustawiane jest przez `user.new_password`
przed `insert()`, więc Frappe haszuje je samo w standardowym `before_insert`.
"""

import secrets
import string

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

from crm.api import VOLTEO_POZIOMY_PROWIZJI
from crm.permissions.org_hierarchy import BYPASS_ROLES, _in_hierarchy, _team_mem_query, hierarchy_enabled
from crm.volteo_wzmianki import wybierz_wzmiankowalnych

# Role, których konta liczą się jako "wszyscy użytkownicy CRM" w
# uzytkownicy_do_wzmianek() poniżej — świadomie szerszy zbiór niż
# NADAWALNE_ROLE (obejmuje też role platformowe/Sales*, bo bypass ma
# pokazywać KAŻDEGO użytkownika CRM, nie tylko konta zakładane tym modułem).
WSZYSTKIE_ROLE_CRM = (
	"System Manager",
	"Sales Manager",
	"Sales User",
	"Volteo Core Admin",
	"Volteo Backend",
	"Volteo D2D Sales",
)

# Role, które ten moduł wolno nadać. Zamknięta biała lista — cokolwiek spoza
# niej jest odrzucane, niezależnie od tego, kto woła (patrz docstring modułu).
# `System Manager` CELOWO nie znajduje się na tej liście.
NADAWALNE_ROLE = (
	"Volteo D2D Sales",
	"Volteo Backend",
	"Volteo Ecom Sales",
	"Volteo Core Admin",
)

# Kto może wołać którąkolwiek funkcję tego modułu.
DOPUSZCZONE_ROLE_WOLAJACEGO = ["Volteo Core Admin", "System Manager"]

# Rola bazowa CRM wymagana przez get_session_role_flags() — patrz docstring.
ROLA_BAZOWA = "Sales User"

# Parametry generowania hasła. Bez cudzysłowów/apostrofów/backslasha, żeby
# hasło dało się bezpiecznie przekazać ustnie lub wkleić bez escapowania.
DLUGOSC_HASLA = 24
ALFABET_HASLA = string.ascii_letters + string.digits + "!@#$%^&*-_=+"


def _wygeneruj_haslo() -> str:
	"""Silne, losowe hasło generowane serwerowo (`secrets`, nie `random`)."""
	return "".join(secrets.choice(ALFABET_HASLA) for _ in range(DLUGOSC_HASLA))


def _sprawdz_biala_liste_roli(rola: str) -> None:
	if rola not in NADAWALNE_ROLE:
		frappe.throw(
			_("Nie można nadać roli {0}. Dozwolone role: {1}.").format(
				rola, ", ".join(NADAWALNE_ROLE)
			),
			frappe.PermissionError,
		)


def _usun_role(user_doc, *role_names) -> None:
	"""Usuń wskazane role z tabeli potomnej `roles`.

	Wzorzec identyczny z `remove_roles()` w `crm/api/user.py`: operujemy na
	liście zwróconej przez `user_doc.get("roles")` i wołamy na niej `.remove()`
	— to działa na potomnej tabeli dokumentu Frappe; `user_doc.remove(row)`
	to inne (i tutaj niewłaściwe) API.
	"""
	istniejace = {d.role: d for d in user_doc.get("roles")}
	for rola in role_names:
		if rola in istniejace:
			user_doc.get("roles").remove(istniejace[rola])


@frappe.whitelist()
def volteo_utworz_uzytkownika(email: str, imie: str, nazwisko: str, rola: str) -> dict:
	"""Zakłada nowe konto `User` i nadaje mu rolę Volteo z białej listy.

	Dostępne wyłącznie dla `Volteo Core Admin` / `System Manager`. Hasło jest
	generowane serwerowo i zwracane RAZ w odpowiedzi — nigdzie indziej nie
	jest logowane ani zapisywane jawnie. Konto zawsze otrzymuje też rolę
	bazową `Sales User` (patrz docstring modułu), bez której sesja CRM
	byłaby odrzucana przy pierwszym żądaniu.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	_sprawdz_biala_liste_roli(rola)

	email = (email or "").strip()
	imie = (imie or "").strip()
	nazwisko = (nazwisko or "").strip()

	if not email:
		frappe.throw(_("Adres e-mail jest wymagany."))
	# validate_email_address z throw=True rzuca frappe.InvalidEmailAddressError
	# przy niepoprawnym formacie — dokładnie ta funkcja, której używa
	# invite_by_email (tam z throw=False, bo obsługuje listę adresów).
	validate_email_address(email, throw=True)

	if not imie:
		frappe.throw(_("Imię jest wymagane."))
	if not nazwisko:
		frappe.throw(_("Nazwisko jest wymagane."))

	if frappe.db.exists("User", email):
		frappe.throw(_("Konto o adresie {0} już istnieje.").format(email))

	haslo = _wygeneruj_haslo()

	user_doc = frappe.new_doc("User")
	user_doc.email = email
	user_doc.first_name = imie
	user_doc.last_name = nazwisko
	user_doc.user_type = "System User"
	user_doc.enabled = 1
	# Poczta nie jest skonfigurowana na tej instalacji — wysyłka maila
	# powitalnego rzuciłaby wyjątkiem. Hasło przekazujemy poza tym API.
	user_doc.send_welcome_email = 0
	# Frappe haszuje new_password samo w before_insert — nigdy nie trafia
	# do bazy jawnym tekstem.
	user_doc.new_password = haslo
	user_doc.append("roles", {"role": ROLA_BAZOWA})
	user_doc.append("roles", {"role": rola})
	user_doc.insert(ignore_permissions=True)

	return {
		"user": user_doc.name,
		"haslo": haslo,
		"role": [d.role for d in user_doc.get("roles")],
	}


@frappe.whitelist()
def volteo_zmien_role(email: str, rola: str) -> dict:
	"""Zmienia rolę Volteo istniejącego użytkownika.

	Usuwa dotychczasowe role Volteo z białej listy (`NADAWALNE_ROLE`) i
	nadaje wskazaną. Nigdy nie rusza `System Manager` — jeśli konto ją ma,
	zostaje nietknięta niezależnie od zmiany roli Volteo obok. Rola bazowa
	`Sales User` jest zachowywana (dokładana, jeśli z jakiegoś powodu jej
	brakuje). Odmawia, jeśli operacja odebrałaby wołającemu jego własną
	rolę `Volteo Core Admin`, a nie zostałby na koncie żaden inny Core
	Admin — takie żądanie zostawiłoby system bez administratora.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	_sprawdz_biala_liste_roli(rola)

	email = (email or "").strip()
	if not email:
		frappe.throw(_("Adres e-mail jest wymagany."))

	if not frappe.db.exists("User", email):
		frappe.throw(_("Konto o adresie {0} nie istnieje.").format(email))

	user_doc = frappe.get_doc("User", email)
	obecne_role = {d.role for d in user_doc.get("roles")}

	# Nie pozwól wołającemu odebrać samemu sobie ostatniej roli Core Admin
	# w systemie — po takiej zmianie nikt nie mógłby już zarządzać kontami
	# ani rolami przez ten moduł (Desk nadal by działał dla System Managera,
	# ale to nie jest ścieżka, na której warto polegać awaryjnie).
	if (
		email == frappe.session.user
		and "Volteo Core Admin" in obecne_role
		and rola != "Volteo Core Admin"
	):
		inni_core_adminowie = frappe.get_all(
			"Has Role",
			filters={
				"parenttype": "User",
				"role": "Volteo Core Admin",
				"parent": ["!=", email],
			},
			pluck="parent",
		)
		if not inni_core_adminowie:
			frappe.throw(
				_(
					"Nie można odebrać samemu sobie roli Volteo Core Admin — "
					"system zostałby bez żadnego administratora."
				),
				frappe.PermissionError,
			)

	# System Manager nigdy nie jest ruszana — nie ma jej na białej liście,
	# więc poniższe usunięcie jej nie dotyka.
	_usun_role(user_doc, *NADAWALNE_ROLE)

	if ROLA_BAZOWA not in {d.role for d in user_doc.get("roles")}:
		user_doc.append("roles", {"role": ROLA_BAZOWA})

	user_doc.append("roles", {"role": rola})
	user_doc.save(ignore_permissions=True)

	return {
		"user": user_doc.name,
		"role": [d.role for d in user_doc.get("roles")],
	}


@frappe.whitelist()
def volteo_ustaw_linie(email: str, oze: int, cp: int, leady: int = 0) -> dict:
	"""Ustawia flagi dostępu do linii produktowych (`custom_linia_oze` /
	`custom_linia_cp`, issue #16) oraz dostępu do modułu Leady
	(`custom_linia_leady`, issue #27) na koncie `User`.

	Dostępne wyłącznie dla `Volteo Core Admin` / `System Manager`. Flagi
	dotyczą wyłącznie zwykłych pól Check na `User` — proste `db.set_value`
	wystarcza, bez potrzeby `.save()` (żadnych hooków kontrolera nie trzeba
	tu przechodzić, w odróżnieniu od zmiany ról w `volteo_zmien_role`
	powyżej). Rola/uprawnienia bypassujące flagi (`System Manager`,
	`Volteo Core Admin`, `Volteo Backend`) są rozstrzygane po stronie
	`crm.api.volteo_ma_linie` (OZE/CP) i
	`crm.permissions.org_hierarchy._ma_linie_leady` (Leady) przy każdym
	odczycie — ten endpoint jedynie zapisuje surowe wartości flag,
	niezależnie od roli konta docelowego. `leady` domyślnie 0 (zgodnie z
	bezpiecznym rolloutem z issue #27 — patrz `ops/crm-linia-leady.py`), żeby
	istniejące wywołania bez tego parametru nie włączały modułu Leady
	niechcący.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	email = (email or "").strip()
	if not email:
		frappe.throw(_("Adres e-mail jest wymagany."))

	if not frappe.db.exists("User", email):
		frappe.throw(_("Konto o adresie {0} nie istnieje.").format(email))

	oze_flaga = 1 if cint(oze) else 0
	cp_flaga = 1 if cint(cp) else 0
	leady_flaga = 1 if cint(leady) else 0

	frappe.db.set_value(
		"User",
		email,
		{
			"custom_linia_oze": oze_flaga,
			"custom_linia_cp": cp_flaga,
			"custom_linia_leady": leady_flaga,
		},
		update_modified=False,
	)

	return {
		"user": email,
		"custom_linia_oze": oze_flaga,
		"custom_linia_cp": cp_flaga,
		"custom_linia_leady": leady_flaga,
	}


@frappe.whitelist()
def volteo_ustaw_prowizje(email: str, widzi_prowizje: int, poziom_prowizji: str) -> dict:
	"""Ustawia widoczność prowizji (`custom_widzi_prowizje`) i poziom prowizji
	(`custom_poziom_prowizji`) na koncie `User` (issue #51, schemat: #48/ops#46).

	Dostępne wyłącznie dla `Volteo Core Admin` / `System Manager`.

	Celowo ODDZIELNY endpoint od `volteo_ustaw_linie` powyżej, nie kolejne
	parametry z wartością domyślną dołożone do tamtej funkcji. Gdyby
	`widzi_prowizje`/`poziom_prowizji` miały wartości domyślne na
	`volteo_ustaw_linie`, każdy zapis linii produktowych z nieodświeżonego
	(albo równoległego) formularza — który nie wie nic o prowizjach —
	cichcem zresetowałby ustawienia prowizji tego użytkownika do wartości
	domyślnych. Dwa niezależne formularze w UI (sekcja "Linie produktowe" i
	sekcja "Prowizje" w `VolteoUsers.vue`) wołają dwa niezależne, wąskie
	endpointy, każdy odpowiedzialny tylko za swoje pola — ten sam powód, dla
	którego `volteo_zmien_role` i `volteo_ustaw_linie` też są rozdzielone.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	email = (email or "").strip()
	if not email:
		frappe.throw(_("Adres e-mail jest wymagany."))

	if not frappe.db.exists("User", email):
		frappe.throw(_("Konto o adresie {0} nie istnieje.").format(email))

	if poziom_prowizji not in VOLTEO_POZIOMY_PROWIZJI:
		frappe.throw(
			_("Nieznany poziom prowizji {0}. Dozwolone: {1}.").format(
				poziom_prowizji, ", ".join(sorted(VOLTEO_POZIOMY_PROWIZJI))
			)
		)

	widzi_flaga = 1 if cint(widzi_prowizje) else 0

	frappe.db.set_value(
		"User",
		email,
		{
			"custom_widzi_prowizje": widzi_flaga,
			"custom_poziom_prowizji": poziom_prowizji,
		},
		update_modified=False,
	)

	return {
		"user": email,
		"custom_widzi_prowizje": widzi_flaga,
		"custom_poziom_prowizji": poziom_prowizji,
	}


@frappe.whitelist()
def widoczni_uzytkownicy() -> list[str] | None:
	"""Użytkownicy widoczni dla bieżącej sesji w poddrzewie Sales Hierarchy.

	Ops#72: dropdown filtrów typu User (np. „Opiekun" nad listą Klienci,
	„Doradca"/deal_owner w panelu filtrów szans) korzystał dotąd z
	`frappe.desk.search.search_link(doctype="User")`, które zwraca WSZYSTKICH
	aktywnych użytkowników systemowych, niezależnie od tego, kogo wołający
	faktycznie widzi w hierarchii. Ta funkcja daje frontowi (Link.vue, prop
	`userScope`) listę, którą może dołożyć jako dodatkowy filtr `name` do
	tego samego wywołania search_link.

	Reguły widoczności są DOKŁADNIE te same co w
	`crm.permissions.contact_visibility._conditions` — importujemy stamtąd
	(pośrednio, przez org_hierarchy) `BYPASS_ROLES`, `_in_hierarchy`,
	`_team_mem_query`, `hierarchy_enabled`, zamiast kopiować logikę, żeby
	oba miejsca nie mogły się rozjechać:

	- Administrator, rola z BYPASS_ROLES (System Manager / Volteo Core Admin
	  / Volteo Backend) albo Sales Manager SPOZA drzewa hierarchii → `None`
	  (dla wołającego oznacza „bez dodatkowego ograniczenia" — dokładnie tak
	  jak dziś, zanim to API istniało).
	- W drzewie hierarchii → siebie + całe poddrzewo podwładnych
	  (`_team_mem_query` zawiera samego managera, bo warunek to
	  `Member.lft >= Mgr.lft`).
	- Poza drzewem (Sales User bez roli Sales Manager, hierarchia wyłączona
	  albo węzeł usunięty) → tylko siebie.

	Dostępna dla każdego zalogowanego użytkownika CRM — `frappe.whitelist()`
	bez dodatkowej bramki ról, bo nie zwraca nic poza nazwami (adresami
	e-mail) kont User, które i tak są widoczne każdemu przez search_link.

	Uwaga o `None` na froncie: Frappe nie serializuje zwróconego `None` jako
	`"message": null` — cały klucz `message` znika z odpowiedzi JSON, więc
	HTTP body dla wołających bez ograniczenia to dosłownie `{}`. frappe-ui
	odczytuje to jako `response.message === undefined`, nie `null` — dlatego
	`Link.vue` (prop `userScope`) sprawdza wynik przez luźne `== null`,
	które łapie oba przypadki naraz.
	"""
	user = frappe.session.user

	if user == "Administrator":
		return None

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return None

	in_tree = hierarchy_enabled() and _in_hierarchy(user)

	# Sales Manager spoza drzewa widzi wszystkich — jak w contact_visibility.
	if "Sales Manager" in roles and not in_tree:
		return None

	if in_tree:
		czlonkowie = _team_mem_query(user).run(pluck=True)
		return sorted(set(czlonkowie))

	return [user]


@frappe.whitelist()
def uzytkownicy_do_wzmianek() -> list[dict[str, str]]:
	"""Użytkownicy podpowiadani po `@` przy wzmiankach (Trify i komentarze szansy, ops#75).

	Decyzja właściciela 2026-09-04 — lista pokazuje WYŁĄCZNIE zarząd (rola
	`Volteo Core Admin`) + backoffice (rola `Volteo Backend`) + podwładnych
	wołającego w drzewie `CRM Sales Hierarchy` (jego poddrzewo). NIE
	przełożonych, NIE inne poddrzewa, NIE użytkowników spoza drzewa. Wołający
	z `BYPASS_ROLES` (System Manager / Volteo Core Admin / Volteo Backend)
	albo `Administrator` widzą wszystkich użytkowników CRM. Zawsze: tylko
	`enabled=1`, nigdy sam wołający, nigdy `Administrator`/`Guest`.

	Sama reguła doboru (kogo zsumować, kiedy uciąć do "wszystkich") mieszka w
	`crm.volteo_wzmianki.wybierz_wzmiankowalnych` — module frappe-free, patrz
	jego docstring. Ta funkcja tylko zbiera trzy zbiory z bazy (zarząd,
	backoffice, poddrzewo — dokładnie ten sam `_team_mem_query` co
	`widoczni_uzytkownicy` powyżej) i "wszyscy_crm" wtedy, gdy wołający ma
	bypass, po czym wykonuje JEDNO `frappe.get_all("User", ...)`, żeby
	odfiltrować do `enabled=1` i pobrać `full_name` do wyświetlenia — zamiast
	ryzykować, że lista pokaże zablokowane albo dawno wyłączone konto.

	Bez `@rate_limit`: to zapytanie tylko do odczytu, tego samego kształtu co
	`widoczni_uzytkownicy` powyżej (które też go nie ma) — zwraca wyłącznie
	nazwy/imiona kont, które i tak są widoczne każdemu przez inne endpointy
	wyszukiwania użytkowników. Frontend cache'uje wynik przez mechanizm
	`cache` frappe-ui (nie odpytuje przy każdym wciśniętym `@`), więc nie ma
	tu wzorca "jeden klawisz = jedno żądanie", który uzasadniałby limiter.

	Nie ma tu `frappe.throw` dla Guest — `frappe.whitelist()` bez
	`allow_guest=True` i tak odrzuca niezalogowane żądania, zanim ciało
	funkcji w ogóle się wykona.
	"""
	user = frappe.session.user
	role_wolajacego = set(frappe.get_roles(user))
	bypass = user == "Administrator" or bool(role_wolajacego & BYPASS_ROLES)

	zarzad = frappe.get_all(
		"Has Role",
		filters={"role": "Volteo Core Admin", "parenttype": "User"},
		pluck="parent",
	)
	backoffice = frappe.get_all(
		"Has Role",
		filters={"role": "Volteo Backend", "parenttype": "User"},
		pluck="parent",
	)

	poddrzewo = None
	if hierarchy_enabled() and _in_hierarchy(user):
		poddrzewo = _team_mem_query(user).run(pluck=True)

	wszyscy_crm: list[str] = []
	if bypass:
		wszyscy_crm = frappe.get_all(
			"Has Role",
			filters={"role": ["in", WSZYSTKIE_ROLE_CRM], "parenttype": "User"},
			pluck="parent",
		)

	nazwy = wybierz_wzmiankowalnych(
		wolajacy=user,
		role_wolajacego=role_wolajacego,
		bypass=bypass,
		zarzad=zarzad,
		backoffice=backoffice,
		poddrzewo=poddrzewo,
		wszyscy_crm=wszyscy_crm,
	)

	if not nazwy:
		return []

	return frappe.get_all(
		"User",
		filters={"name": ["in", nazwy], "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
