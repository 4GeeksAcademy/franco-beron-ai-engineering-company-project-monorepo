from tinydb import TinyDB

from app.config import SERVICE_DIR


db = TinyDB(SERVICE_DIR / "db.json")
users = db.table("users")
profiles = db.table("profiles")
incidents = db.table("nexova_incidents")
central_incidents = db.table("central_incidents")
incident_seed_keys = db.table("incident_seed_keys")
reset_tokens = db.table("reset_tokens")
suppliers = db.table("suppliers")
