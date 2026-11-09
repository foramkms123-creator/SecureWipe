"""Sign-up / sign-in rules: validation, lockout, roles."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from config import LOCKOUT_MINUTES, MAX_FAILED_LOGINS, MIN_PASSWORD_LENGTH
from database import notifications_repo, users_repo
from services import settings_service
from services.passwords import DUMMY_HASH, hash_password, verify_password

USERNAME_RE = re.compile(r"^.{3,30}$", re.DOTALL)   # any characters, 3 to 30 long
FULL_NAME_RE = re.compile(r"^[A-Za-z ]+$")          # full name: letters (A-Z, a-z) and spaces only


class AuthError(Exception):
    """Raised with a message that is safe to show to the user."""


@dataclass(frozen=True)
class User:
    id: int
    username: str
    full_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def first_name(self) -> str:
        return self.full_name.split()[0] if self.full_name.strip() else self.username

    @property
    def initials(self) -> str:
        parts = self.full_name.split() or [self.username]
        return "".join(p[0] for p in parts[:2]).upper()


def _to_user(row) -> User:
    return User(row["id"], row["username"], row["full_name"], row["role"])


STRONG_MIN_LENGTH = 12


def _check_password_policy(password: str) -> None:
    """Rules from Settings > Password policy. Applies to new passwords only."""
    if settings_service.get("password_policy") == "strong":
        if len(password) < STRONG_MIN_LENGTH:
            raise AuthError(f"Password needs at least {STRONG_MIN_LENGTH} characters.")
        if not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password)
                and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password)):
            raise AuthError("Password needs upper and lower case letters, a number and a symbol.")
        return
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise AuthError("Password needs at least one letter and one number.")


def sign_up(full_name: str, username: str, password: str, confirm: str) -> User:
    full_name, username = full_name.strip(), username.strip()
    if not full_name:
        raise AuthError("Enter your full name.")
    if not FULL_NAME_RE.match(full_name):
        raise AuthError("Full name can only contain letters and spaces.")
    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3–30 characters.")
    _check_password_policy(password)
    if password != confirm:
        raise AuthError("Passwords do not match.")
    if users_repo.get_by_username(username):
        raise AuthError("That username is taken.")

    role = "admin" if users_repo.count_users() == 0 else "staff"   # first account = admin
    user_id = users_repo.create_user(username, full_name, hash_password(password), role)
    notifications_repo.add(user_id, "Account created. Welcome to SecureWipe.")
    return User(user_id, username, full_name, role)


def change_password(user: User, current: str, new: str, confirm: str) -> None:
    row = users_repo.get_by_username(user.username)
    if row is None or not verify_password(current, row["password_hash"]):
        raise AuthError("Current password is incorrect.")
    _check_password_policy(new)
    if new != confirm:
        raise AuthError("The new passwords do not match.")
    if new == current:
        raise AuthError("Choose a password different from the current one.")
    users_repo.update_password(user.id, hash_password(new))
    notifications_repo.add(user.id, "Your password was changed.")


def confirm_password(user: User, password: str) -> bool:
    """Checks the signed-in user's password (used before sensitive actions)."""
    row = users_repo.get_by_username(user.username)
    return row is not None and verify_password(password, row["password_hash"])


def sign_in(username: str, password: str) -> User:
    row = users_repo.get_by_username(username.strip())
    if row is None:
        verify_password(password, DUMMY_HASH)
        raise AuthError("Incorrect username or password.")

    now = datetime.now()
    if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now:
        minutes = int((datetime.fromisoformat(row["locked_until"]) - now).total_seconds() // 60) + 1
        raise AuthError(f"Account locked after repeated failures. Try again in {minutes} min.")

    if not verify_password(password, row["password_hash"]):
        attempts = row["failed_attempts"] + 1
        if attempts >= MAX_FAILED_LOGINS:
            until = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(timespec="seconds")
            users_repo.record_failed_login(row["id"], 0, until)
            raise AuthError(f"Too many attempts. Account locked for {LOCKOUT_MINUTES} min.")
        users_repo.record_failed_login(row["id"], attempts, None)
        raise AuthError(
            f"Incorrect username or password. {MAX_FAILED_LOGINS - attempts} "
            f"attempt{'s' if MAX_FAILED_LOGINS - attempts > 1 else ''} left.")

    users_repo.record_successful_login(row["id"])
    return _to_user(row)
