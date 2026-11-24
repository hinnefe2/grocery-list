import json
import unittest
from unittest.mock import Mock, patch

import requests

from service import app, simplify_ingredients


def cleanup_response(result, finish_reason="stop"):
    return Mock(json=Mock(return_value={
        "choices": [{
            "finish_reason": finish_reason,
            "message": {"content": json.dumps(result)},
        }]
    }))


@patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
class CleanupTest(unittest.TestCase):
    def test_batch_cleanup_preserves_mapping_even_if_response_keys_are_reordered(self):
        originals = [
            "1/2 white onion, trimmed, halved, and roughly chopped (4 ounces; 113g)",
            "5 guajillo chiles, stems and seeds removed",
        ]
        result = {"ingredient_1": "5 guajillo chiles", "ingredient_0": " 1/2 white   onion "}
        with patch("service.req.post", return_value=cleanup_response(result)) as post:
            self.assertEqual(simplify_ingredients(originals), ["1/2 white onion", "5 guajillo chiles"])
        self.assertEqual(post.call_count, 1)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(json.loads(payload["messages"][1]["content"]), {
            "ingredient_0": originals[0], "ingredient_1": originals[1],
        })
        schema = payload["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["required"], ["ingredient_0", "ingredient_1"])
        self.assertFalse(schema["additionalProperties"])

    def test_bad_cleanup_never_loses_original_ingredients(self):
        originals = ["1 onion, chopped", "2 ancho chiles, stems removed"]
        invalid_results = [
            {}, {"ingredient_0": "1 onion"},
            {"ingredient_0": "1 onion", "ingredient_1": "2 ancho chiles", "ingredient_2": "salt"},
            {"ingredient_0": "1 onion", "ingredient_2": "2 ancho chiles"},
            {"ingredient_0": "1 onion", "ingredient_1": " "},
            {"ingredient_0": "1 onion", "ingredient_1": None},
            ["1 onion", "2 ancho chiles"],
        ]
        for result in invalid_results:
            with self.subTest(result=result), patch("service.req.post", return_value=cleanup_response(result)):
                self.assertEqual(simplify_ingredients(originals), originals)

    def test_api_failure_or_truncation_preserves_originals(self):
        originals = ["1 onion, chopped"]
        for error in (requests.Timeout(), requests.HTTPError()):
            with self.subTest(error=error), patch("service.req.post", side_effect=error):
                self.assertEqual(simplify_ingredients(originals), originals)
        with patch("service.req.post", return_value=cleanup_response({"ingredient_0": "1 onion"}, "length")):
            self.assertEqual(simplify_ingredients(originals), originals)
        malformed = Mock(json=Mock(return_value={"choices": [{
            "finish_reason": "stop", "message": {"content": "not json"}
        }]}))
        with patch("service.req.post", return_value=malformed):
            self.assertEqual(simplify_ingredients(originals), originals)

    def test_empty_list_does_not_call_model(self):
        with patch("service.req.post") as post:
            self.assertEqual(simplify_ingredients([]), [])
        post.assert_not_called()


class CleanupRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_all_extraction_sources_clean_names_and_classify_original_lines(self):
        original = ["1/2 white onion, trimmed (113g)", "2 ancho chiles, stems removed"]
        for source in ("downloaded", "jtr", "schollz"):
            with (
                self.subTest(source=source),
                patch("service.req.get", return_value=Mock(status_code=200 if source == "downloaded" else 403)),
                patch("service.parse_response", return_value=original) as parse,
                patch("service.parse_jtr", return_value=original if source == "jtr" else None),
                patch("service.parse_schollz", return_value=original),
                patch("service.simplify_ingredients", return_value=["1/2 white onion", "2 ancho chiles"]) as cleanup,
                patch("service.classify_ingredients", return_value=[0, 6]) as classify,
            ):
                response = self.client.get("/?recipe_url=https://example.com/recipe")
            self.assertEqual(response.status_code, 200)
            cleanup.assert_called_once_with(original)
            classify.assert_called_once_with(original)
            self.assertEqual(response.get_json(), {"ingredients": {
                "0": [{"name": "1/2 white onion", "section": 0}],
                "6": [{"name": "2 ancho chiles", "section": 6}],
            }})
            if source in ("jtr", "schollz"):
                parse.assert_not_called()

    def test_manually_entered_items_are_preserved(self):
        with (
            patch("service.simplify_ingredients") as cleanup,
            patch("service.classify_ingredients", return_value=[0]),
        ):
            response = self.client.get("/single-item/?item=1/2%20onion")
        self.assertEqual(response.get_json()["ingredients"]["0"][0]["name"], "1/2 onion")
        cleanup.assert_not_called()
