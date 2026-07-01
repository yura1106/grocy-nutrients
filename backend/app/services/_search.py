"""Shared fuzzy-name search: pg_trgm on Postgres, casefold substring elsewhere."""

from typing import TypeVar, cast

from sqlalchemy import desc, or_
from sqlalchemy.orm import InstrumentedAttribute, Mapped
from sqlmodel import Session, func, select
from sqlmodel.sql.expression import SelectOfScalar

T = TypeVar("T")

_TRGM_SIMILARITY_THRESHOLD = 0.25


def _fuzzy_match(
    db: Session,
    base_stmt: SelectOfScalar[T],
    name_col: Mapped[str],
    query: str,
    limit: int,
) -> list[T]:
    """Order an already-scoped `select(Model)` by name similarity to `query`.

    `base_stmt` must already carry household/active scoping. On Postgres matches the
    pg_trgm `%` operator (threshold 0.25) OR a plain substring (so exact substrings
    never fall below the trigram threshold), ordered by `similarity()`; elsewhere
    (SQLite tests) falls back to a Python casefold-substring filter since SQLite
    `lower()` is ASCII-only.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.exec(select(func.set_limit(_TRGM_SIMILARITY_THRESHOLD)))
        statement = (
            base_stmt.where(
                or_(name_col.op("%")(query), name_col.ilike(f"%{query}%"))
            )
            .order_by(desc(func.similarity(name_col, query)))
            .limit(limit)
        )
        return list(db.exec(statement).all())

    needle = query.casefold()
    attr = cast(InstrumentedAttribute[str], name_col).key
    rows = db.exec(base_stmt).all()
    return [r for r in rows if needle in (getattr(r, attr, "") or "").casefold()][:limit]
