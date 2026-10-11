from getpass import getpass
import sys
from pydantic import TypeAdapter, ValidationError
from pydantic.networks import EmailStr
from tinydb import Query

from app.db import users
from app.schemas import UserRole
from app.user_service import create_user as persist_user


def main():
    email_input = input("Correo interno: ").strip().lower()
    try:
        email = TypeAdapter(EmailStr).validate_python(email_input)
    except ValidationError:
        print("Correo inválido; no se creó la cuenta.", file=sys.stderr)
        return 1

    name = input("Nombre: ").strip()
    role_input = input("Rol (admin/manager/user) [user]: ").strip() or "user"
    try:
        role = UserRole(role_input)
    except ValueError:
        print("Rol inválido; use admin, manager o user.", file=sys.stderr)
        return 1

    password = getpass("Contraseña (mínimo 8 caracteres): ")
    confirmation = getpass("Repetir contraseña: ")

    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        print("La contraseña debe tener entre 8 y 72 bytes.", file=sys.stderr)
        return 1
    if password != confirmation:
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1

    user_query = Query()
    try:
        if users.search(user_query.email == str(email).lower()):
            print("La cuenta ya existe.", file=sys.stderr)
            return 1
        persist_user(str(email), password, {"name": name}, role=role)
    except Exception:
        print("Error: no se pudo guardar la cuenta. Revisa la base local antes de reintentar.", file=sys.stderr)
        return 1
    print("Cuenta interna creada.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print("Error: creación de cuenta cancelada.", file=sys.stderr)
        raise SystemExit(1) from None
