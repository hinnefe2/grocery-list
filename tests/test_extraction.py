import json
import unittest
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

from service import (
    MAX_EXTRACTION_CHARS,
    app,
    parse_jtr,
    parse_ld_json,
    parse_response,
    parse_schollz,
    parse_with_model,
)


def html_response(html):
    return Mock(status_code=200, content=html.encode())


def model_response(ingredients, finish_reason="stop"):
    return Mock(json=Mock(return_value={
        "choices": [{
            "finish_reason": finish_reason,
            "message": {"content": json.dumps({"ingredients": ingredients})},
        }]
    }))


class ExtractionTest(unittest.TestCase):
    def test_json_ld_shapes_preserve_complete_ingredient_lines(self):
        recipe = {"@type": "Recipe", "recipeIngredient": ["  250 g  flour ", "1 onion, chopped"]}
        for data in (recipe, [recipe], {"@graph": [{"@type": "WebSite"}, recipe]}):
            with self.subTest(data=data):
                soup = BeautifulSoup(
                    '<script type="application/ld+json">' + json.dumps(data) + '</script>',
                    "html.parser",
                )
                self.assertEqual(parse_ld_json(soup), ["250 g flour", "1 onion, chopped"])

    def test_skips_bad_scripts_and_unusable_ingredient_lists(self):
        html = ''.join(
            '<script type="application/ld+json">' + data + '</script>'
            for data in (
                'broken json', 'null', '{"recipeIngredient": "flour"}',
                '{"recipeIngredient": [1]}', '{"recipeIngredient": [" "]}',
                '{"@type": "Recipe", "recipeIngredient": ["2 eggs"]}',
            )
        )
        self.assertEqual(parse_ld_json(BeautifulSoup(html, "html.parser")), ["2 eggs"])

    def test_structured_data_skips_model_and_external_services(self):
        response = html_response('<script type="application/ld+json">'
                                 '{"recipeIngredient": ["2 eggs"]}</script>')
        with patch("service.req.post") as post, patch("service.req.get") as get:
            self.assertEqual(parse_response(response), ["2 eggs"])
        post.assert_not_called()
        get.assert_not_called()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_html_model_fallback_cleans_page_and_preserves_recipe_structure(self):
        html = '''<body><nav>Links</nav><script>tracking()</script><style>css</style>
        <!-- hidden comment --><h1 class="title">Soup</h1><h2>Ingredients</h2>
        <ul><li data-ads="tracking">250 ml stock</li><li>1 onion, finely chopped</li></ul>
        <footer>Ads</footer></body>'''
        with (
            patch("service.req.post", return_value=model_response(
                [" 250 ml   stock ", "1 onion, finely chopped"]
            )) as post,
            patch("service.req.get") as get,
        ):
            self.assertEqual(parse_response(html_response(html)),
                             ["250 ml stock", "1 onion, finely chopped"])
        get.assert_not_called()
        payload = post.call_args.kwargs["json"]
        cleaned = payload["messages"][1]["content"]
        self.assertIn("<h2>Ingredients</h2>", cleaned)
        self.assertIn("<li>250 ml stock</li>", cleaned)
        for clutter in ("tracking", "hidden comment", "Ads", "Links", "class="):
            self.assertNotIn(clutter, cleaned)
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["provider"]["require_parameters"])

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_invalid_or_truncated_model_output_is_rejected(self):
        responses = [model_response("flour"), model_response([None]),
                     model_response([""]), model_response(["flour"], "length"),
                     Mock(json=Mock(return_value={"choices": []})),
                     Mock(json=Mock(return_value={"choices": [{
                         "finish_reason": "stop", "message": {"content": "not json"}
                     }]}))]
        for response in responses:
            with self.subTest(response=response), patch("service.req.post", return_value=response):
                with self.assertRaises(ValueError):
                    parse_with_model(BeautifulSoup("<p>Recipe</p>", "html.parser"))

    def test_empty_or_oversize_html_never_calls_model(self):
        with patch("service.req.post") as post:
            self.assertEqual(parse_response(html_response("<script>tracking()</script>")), [])
            with self.assertRaises(ValueError):
                parse_response(html_response("<p>" + "x" * MAX_EXTRACTION_CHARS + "</p>"))
        post.assert_not_called()

    def test_external_services_encode_url_and_bound_requests(self):
        url = 'https://example.com/recipe?a=1&b="two"'
        with patch("service.req.get", return_value=Mock(json=Mock(return_value={
            "ingredients": [{"name": "2 eggs"}]
        }))) as get:
            self.assertEqual(parse_jtr(url), ["2 eggs"])
            self.assertEqual(get.call_args.kwargs["params"], {"url": url})
            self.assertEqual(get.call_args.kwargs["timeout"], 5)
        with patch("service.req.get", return_value=Mock(json=Mock(return_value={
            "ingredients": [{"measure": {"amount": 250, "name": "ml"}, "name": "stock"}]
        }))) as get:
            self.assertEqual(parse_schollz(url), ["250 ml stock"])
            self.assertEqual(get.call_args.kwargs["params"]["func"],
                             f'IngredientsFromURL({json.dumps(url)})')
            self.assertEqual(get.call_args.kwargs["timeout"], 5)

    def test_external_services_tolerate_transport_and_payload_errors(self):
        for parser in (parse_jtr, parse_schollz):
            for error in (requests.Timeout(), requests.ConnectionError(), ValueError(), KeyError()):
                with self.subTest(parser=parser, error=error), patch("service.req.get", side_effect=error):
                    self.assertIsNone(parser("https://example.com"))


class ExtractionRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_blocked_download_tries_second_service_after_first_times_out(self):
        schollz = Mock(json=Mock(return_value={
            "ingredients": [{"measure": {"amount": 250, "name": "ml"}, "name": "stock"}]
        }))
        with (
            patch("service.req.get", side_effect=[Mock(status_code=403), requests.Timeout(), schollz]),
            patch("service.parse_with_model") as model,
            patch("service.classify_ingredients", return_value=[5]),
        ):
            response = self.client.get("/?recipe_url=https://example.com/blocked")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ingredients"]["5"][0]["name"], "250 ml stock")
        model.assert_not_called()

    def test_download_timeout_uses_external_recovery(self):
        with (
            patch("service.req.get", side_effect=requests.Timeout()),
            patch("service.parse_jtr", return_value=["1 apple"]),
            patch("service.classify_ingredients", return_value=[0]),
        ):
            response = self.client.get("/?recipe_url=https://example.com/recipe")
        self.assertEqual(response.status_code, 200)

    def test_empty_extraction_returns_explicit_error_without_external_calls(self):
        with (
            patch("service.req.get", return_value=html_response("<p>No recipe</p>")),
            patch("service.parse_with_model", return_value=[]),
            patch("service.parse_jtr") as jtr,
            patch("service.parse_schollz") as schollz,
            patch("service.classify_ingredients") as classify,
        ):
            response = self.client.get("/?recipe_url=https://example.com/recipe")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json(), {"error": "No recipe ingredients found"})
        for mock in (jtr, schollz, classify):
            mock.assert_not_called()

    def test_model_failures_return_json_error(self):
        for error in (requests.Timeout(), ValueError("invalid output")):
            with (
                self.subTest(error=error),
                patch("service.req.get", return_value=html_response("<p>Recipe</p>")),
                patch("service.parse_with_model", side_effect=error),
            ):
                response = self.client.get("/?recipe_url=https://example.com/recipe")
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.get_json(), {"error": "Unable to extract recipe ingredients"})
