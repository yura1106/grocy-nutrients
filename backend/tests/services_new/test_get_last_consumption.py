"""get_last_consumption — most recent ConsumedProduct for a (product, user), any origin."""

from datetime import UTC, date, datetime

from sqlmodel import Session

from app.models.product import ConsumedProduct, Product, ProductData
from app.services.product import get_last_consumption

HH = 1
USER = 501


def _product_with_data(db: Session, name: str, grocy_id: int, *, calories: float) -> ProductData:
    product = Product(
        grocy_id=grocy_id, name=name, product_group_id=1, household_id=HH,
        created_at=datetime.now(UTC),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    pd = ProductData(
        product_id=product.id, calories=calories, proteins=0.1, created_at=datetime.now(UTC)
    )
    db.add(pd)
    db.commit()
    db.refresh(pd)
    return pd


def _consume(db: Session, pd: ProductData, *, day: date, qty: float, recipe_grocy_id=None) -> None:
    db.add(
        ConsumedProduct(
            product_data_id=pd.id, date=day, quantity=qty, user_id=USER,
            household_id=HH, recipe_grocy_id=recipe_grocy_id, created_at=datetime.now(UTC),
        )
    )
    db.commit()


def test_returns_none_when_never_consumed(db: Session) -> None:
    pd = _product_with_data(db, "Банан", 1, calories=1.0)
    assert get_last_consumption(db, pd.product_id, USER) is None


def test_latest_by_date(db: Session) -> None:
    pd = _product_with_data(db, "Банан", 1, calories=2.0)
    _consume(db, pd, day=date(2026, 6, 1), qty=50)
    _consume(db, pd, day=date(2026, 6, 10), qty=100)

    out = get_last_consumption(db, pd.product_id, USER)
    assert out is not None
    assert out["date"] == "2026-06-10"
    assert out["quantity"] == 100
    # 2 kcal/g x 100 g = 200
    assert out["calories"] == 200.0


def test_includes_recipe_origin_rows(db: Session) -> None:
    pd = _product_with_data(db, "Цукор", 2, calories=4.0)
    _consume(db, pd, day=date(2026, 6, 5), qty=10, recipe_grocy_id=77)

    out = get_last_consumption(db, pd.product_id, USER)
    assert out is not None
    assert out["quantity"] == 10


def test_scoped_to_user(db: Session) -> None:
    pd = _product_with_data(db, "Банан", 1, calories=2.0)
    db.add(
        ConsumedProduct(
            product_data_id=pd.id, date=date(2026, 6, 9), quantity=999, user_id=USER + 1,
            household_id=HH, created_at=datetime.now(UTC),
        )
    )
    db.commit()
    assert get_last_consumption(db, pd.product_id, USER) is None
