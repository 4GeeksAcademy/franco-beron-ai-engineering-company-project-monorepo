from getpass import getpass
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError
from pydantic.networks import EmailStr
from tinydb import Query

from app.db import users
from app.security import hash_password


def main():
    email_input = input("Correo interno: ").strip().lower()
    try:
        email = TypeAdapter(EmailStr).validate_python(email_input)
    except ValidationError:
        print("Correo inválido; no se creó la cuenta.")
        return

    name = input("Nombre: ").strip()
    password = getpass("Contraseña (mínimo 8 caracteres): ")
    confirmation = getpass("Repetir contraseña: ")

    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        print("La contraseña debe tener entre 8 y 72 bytes.")
        return
    if password != confirmation:
        print("Las contraseñas no coinciden.")
        return

    user_query = Query()
    if users.search(user_query.email == str(email).lower()):
        print("La cuenta ya existe.")
        return

    users.insert(
        {
            "uuid": str(uuid4()),
            "email": str(email).lower(),
            "name": name,
            "password_hash": hash_password(password),
        }
    )
    print("Cuenta interna creada.")


if __name__ == "__main__":
    main()
