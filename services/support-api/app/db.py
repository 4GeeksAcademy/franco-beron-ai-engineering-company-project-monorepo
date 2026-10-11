from tinydb import TinyDB

from app.config import SERVICE_DIR


db = TinyDB(SERVICE_DIR / "db.json")
users = db.table("users")
profiles = db.table("profiles")
incidents = db.table("nexova_incidents")
reset_tokens = db.table("reset_tokens")
suppliers = db.table("suppliers")
