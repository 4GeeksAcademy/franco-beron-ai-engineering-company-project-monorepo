# Shared Validation

`incident_validation.py` contains pure validation and CSV transformation functions shared by the support API and `scripts/seed_incidents.py`.

The historical CSV is not stored in this repository. Supply its path explicitly when running the seed script; customer email is validated but never persisted or printed.
