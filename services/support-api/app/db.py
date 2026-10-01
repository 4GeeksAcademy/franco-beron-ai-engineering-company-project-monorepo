from tinydb import TinyDB

from app.config import SERVICE_DIR


db = TinyDB(SERVICE_DIR / "db.json")
users = db.table("users")
incidents = db.table("incidents")
reset_tokens = db.table("reset_tokens")
