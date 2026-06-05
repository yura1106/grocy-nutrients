from unittest.mock import MagicMock

from app.services.grocy_api import GrocyAPI


def _api():
    api = GrocyAPI.__new__(GrocyAPI)  # bypass __init__ (needs url/key)
    api.get = MagicMock()  # type: ignore[method-assign]
    api.post = MagicMock()  # type: ignore[method-assign]
    api.put = MagicMock()  # type: ignore[method-assign]
    return api


class TestGetRecipe:
    def test_calls_objects_recipes_path(self):
        api = _api()
        api.get.return_value = {"id": 75, "name": "Вечеря №1"}
        result = api.get_recipe(75)
        api.get.assert_called_once_with("/objects/recipes/75")
        assert result == {"id": 75, "name": "Вечеря №1"}


class TestGetResolvedPositions:
    def test_queries_recipes_pos_resolved_for_shadow(self):
        api = _api()
        api.get.return_value = [{"product_id_effective": 491}]
        result = api.get_resolved_positions(-44663)
        api.get.assert_called_once_with(
            "/objects/recipes_pos_resolved", {"query[]": ["recipe_id=-44663"]}
        )
        assert result == [{"product_id_effective": 491}]

    def test_none_response_returns_empty_list(self):
        api = _api()
        api.get.return_value = None
        assert api.get_resolved_positions(-44663) == []


class TestGetRecipeFulfillment:
    def test_calls_fulfillment_path(self):
        api = _api()
        api.get.return_value = {"missing_products_count": 0}
        result = api.get_recipe_fulfillment(-44663)
        api.get.assert_called_once_with("/recipes/-44663/fulfillment")
        assert result == {"missing_products_count": 0}


class TestConsumeRecipe:
    def test_posts_consume_path(self):
        api = _api()
        api.consume_recipe(-44663)
        api.post.assert_called_once_with("/recipes/-44663/consume")


class TestMarkMealPlanDone:
    def test_puts_done_flag(self):
        api = _api()
        api.mark_meal_plan_done(5531)
        api.put.assert_called_once_with("/objects/meal_plan/5531", data={"done": 1})
