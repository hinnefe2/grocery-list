import unittest
from unittest.mock import Mock, patch

from service import app


class GroceryListRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_recipe_upstream_error_returns_valid_json_response(self):
        upstream_response = Mock(status_code=404)

        with (
            patch("service.req.get", return_value=upstream_response),
            patch("service.parse_jtr", return_value=None),
            patch("service.parse_schollz", return_value=None),
        ):
            response = self.client.get("/?recipe_url=https://example.com/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Unable to download recipe"})

    def test_recipe_upstream_error_uses_extraction_fallback(self):
        upstream_response = Mock(status_code=402)

        with (
            patch("service.req.get", return_value=upstream_response),
            patch("service.parse_jtr", return_value=["corn", "lime"]),
            patch("service.classify_ingredients", return_value=[0, 0]),
        ):
            response = self.client.get("/?recipe_url=https://example.com/blocked")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "ingredients": {
                    "0": [
                        {"name": "corn", "section": 0},
                        {"name": "lime", "section": 0},
                    ]
                }
            },
        )

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_recipe_success_groups_classified_ingredients(self):
        upstream_response = Mock(status_code=200)

        with (
            patch("service.req.get", return_value=upstream_response),
            patch("service.parse_response", return_value=["2 apples", "1 lb chicken"]),
            patch("service.classify_ingredients", return_value=[0, 1]),
        ):
            response = self.client.get("/?recipe_url=https://example.com/recipe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "ingredients": {
                    "0": [{"name": "2 apples", "section": 0}],
                    "1": [{"name": "1 lb chicken", "section": 1}],
                }
            },
        )

    def test_single_item_returns_classified_item(self):
        with patch("service.classify_ingredients", return_value=[4]):
            response = self.client.get("/single-item/?item=flour")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"ingredients": {"4": [{"name": "flour", "section": 4}]}},
        )


if __name__ == "__main__":
    unittest.main()
