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
from frappe.utils import validate_email_address

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
