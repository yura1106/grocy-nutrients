"""get_product_detail_for_mcp — local id only, history + per-user consumption."""

from datetime import UTC, date, datetime

import pytest
from sqlmodel import Session

from app.models.product import ConsumedProduct, Product, ProductData
from app.services.product import ProductSyncError, get_product_detail_for_mcp

HH = 1
USER = 801


def _product(db: Session) -> Product:
    product = Product(
        grocy_id=1,
        name="Банан",
        product_group_id=1,
        household_id=HH,
        is_fresh=True,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_detail_has_local_id_history_and_consumption(db: Session) -> None:
    product = _product(db)
    pd = ProductData(product_id=product.id, calories=2.0, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=date(2026, 6, 1),
            quantity=100,
            user_id=USER,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = get_product_detail_for_mcp(db, product.id, HH, USER)
    assert out["id"] == product.id
    assert "grocy_id" not in out
    assert out["is_fresh"] is True
    assert len(out["history"]) == 1
    assert len(out["consumption_history"]) == 1
    assert out["consumption_history"][0]["calories"] == 200.0


def test_other_household_not_found(db: Session) -> None:
    product = _product(db)
    with pytest.raises(ProductSyncError):
        get_product_detail_for_mcp(db, product.id, HH + 99, USER)


def test_other_user_consumption_excluded(db: Session) -> None:
    product = _product(db)
    pd = ProductData(product_id=product.id, calories=2.0, created_at=datetime.now(UTC))
    db.add(pd)
    db.commit()
    db.refresh(pd)
    db.add(
        ConsumedProduct(
            product_data_id=pd.id,
            date=date(2026, 6, 1),
            quantity=100,
            user_id=USER + 1,
            household_id=HH,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    out = get_product_detail_for_mcp(db, product.id, HH, USER)
    assert out["consumption_history"] == []
