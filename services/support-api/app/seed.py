from sqlmodel import Session, select


SEED_USER_UUID = "00000000-0000-0000-0000-000000000000"

ASSET_SEEDS = (
    ("Laptop 14\" Business", "NXV-IT-001", "hardware", "Valencia"),
    ("Laptop 14\" Business", "NXV-IT-002", "hardware", "Miami"),
    ("Ergonomic mouse", "NXV-PER-001", "peripherals", "Valencia"),
    ("USB-C Hub", "NXV-PER-002", "peripherals", "Miami"),
    ("A4 paper ream", "NXV-OFF-001", "office_supplies", "Valencia"),
    (
        "Leadership training workbook",
        "NXV-TRN-001",
        "training_materials",
        "Valencia",
    ),
)

ENTRY_SEEDS = (
    ("NXV-IT-001", 10, "TechDistrib Valencia S.L.", "Valencia"),
    ("NXV-IT-001", 5, "TechDistrib Valencia S.L.", "Valencia"),
    ("NXV-PER-001", 20, "TechDistrib Valencia S.L.", "Valencia"),
    ("NXV-PER-002", 12, "Office Depot Miami", "Miami"),
    ("NXV-OFF-001", 100, "Office Depot Valencia", "Valencia"),
)

EXIT_SEEDS = (
    ("NXV-IT-001", 2, "allocation", "Empleado de prueba", "Valencia"),
    ("NXV-PER-002", 1, "allocation", "Empleado de Miami", "Miami"),
    ("NXV-OFF-001", 3, "consumption", None, "Valencia"),
)


def seed_inventory(session: Session, Asset, AssetEntry, AssetExit) -> None:
    assets = {}
    for name, sku, category, office in ASSET_SEEDS:
        asset = session.exec(select(Asset).where(Asset.sku == sku)).first()
        if asset is None:
            asset = Asset(name=name, sku=sku, category=category, office=office)
            session.add(asset)
            session.flush()
        assets[sku] = asset

    for sku, quantity, supplier, office in ENTRY_SEEDS:
        asset = assets[sku]
        existing = session.exec(
            select(AssetEntry).where(
                AssetEntry.asset_id == asset.id,
                AssetEntry.quantity == quantity,
                AssetEntry.supplier == supplier,
                AssetEntry.office == office,
                AssetEntry.user_uuid == SEED_USER_UUID,
            )
        ).first()
        if existing is None:
            session.add(
                AssetEntry(
                    asset_id=asset.id,
                    quantity=quantity,
                    supplier=supplier,
                    office=office,
                    user_uuid=SEED_USER_UUID,
                )
            )

    for sku, quantity, exit_type, assigned_to, office in EXIT_SEEDS:
        asset = assets[sku]
        existing = session.exec(
            select(AssetExit).where(
                AssetExit.asset_id == asset.id,
                AssetExit.quantity == quantity,
                AssetExit.exit_type == exit_type,
                AssetExit.assigned_to == assigned_to,
                AssetExit.office == office,
                AssetExit.user_uuid == SEED_USER_UUID,
            )
        ).first()
        if existing is None:
            session.add(
                AssetExit(
                    asset_id=asset.id,
                    quantity=quantity,
                    exit_type=exit_type,
                    assigned_to=assigned_to,
                    office=office,
                    user_uuid=SEED_USER_UUID,
                )
            )

    session.commit()