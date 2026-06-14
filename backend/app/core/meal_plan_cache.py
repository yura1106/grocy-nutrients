"""Redis cache keys + invalidation for meal-plan units.

Lives in `core` (not `services`) so both `services/meal_plan.py` (writer/reader)
and `services/product.py` (invalidator on sync) can import it without a circular
import — `meal_plan` already lazy-imports `sync_single_grocy_product` from `product`.
"""

import logging

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

UNITS_TTL = 86400  # 24h backstop for conversions changed directly in Grocy


def units_key(household_id: int, grocy_product_id: int) -> str:
    # v2: payload shape includes stock_to_grams_ml.
    return f"meal_plan:units:v2:household:{household_id}:product:{grocy_product_id}"


def invalidate_units_cache(household_id: int, grocy_product_id: int) -> None:
    """Drop the cached units payload for a product. Best-effort.

    A cache-eviction failure must NEVER fail a sync write path: the per-product
    loop in `sync_grocy_products` swallows exceptions as failed products, and
    `sync_single_grocy_product` re-raises as `ProductSyncError`. The 24h TTL is
    the backstop if Redis is unreachable here.
    """
    try:
        get_redis().delete(units_key(household_id, grocy_product_id))
    except Exception as e:
        logger.warning(
            "invalidate_units_cache failed for household=%s product=%s: %s",
            household_id,
            grocy_product_id,
            e,
        )
