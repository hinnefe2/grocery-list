import json
import logging
import os
import re


import requests as req

from itertools import groupby
from operator import itemgetter
from typing import List, Optional

from bs4 import BeautifulSoup
from flask import Flask, request
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

from config import ID2LABEL


load_dotenv()

OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b"
)


def strip_prep_instructions(ingredient: str) -> str:

    prep_words = [
        "very",
        "roughly",
        "finely",
        "chopped",
        "minced",
        "diced",
        "drained",
        "rinsed",
        "divided",
    ]

    for split_token in prep_words:
        if split_token in ingredient:
            result = ingredient.split(split_token)[0].strip(", ")
            if len(result) > 0:
                return result

    return ingredient


def strip_tsp_tbsp(ingredint: str) -> str:
    """Remove teaspoon / tablespoon quantities"""
    regex = "(\d/\d|\d+\s+\d/\d|\d+)\s+(tsp|teaspoon|tbsp|tablespoon)s?"
    return re.sub(regex, "", ingredint)


def strip_parentheses_grams(ingredient: str) -> str:
    """Remove (X  g) quantities"""
    regex = "\(\d+\s?(g|grams)\)"
    return re.sub(regex, "", ingredient)


def parse_ld_json(soup: BeautifulSoup) -> Optional[List[str]]:

    try:
        ldjson = soup.find("script", {"type": "application/ld+json"})
        ingredients = json.loads(ldjson.string).pop()["recipeIngredient"]
    except (TypeError, AttributeError):
        return None

    return list(map(strip_prep_instructions, ingredients))


def parse_itemprops(soup: BeautifulSoup) -> Optional[List[str]]:
    return None


def parse_jtr(recipe_url: str) -> Optional[List[str]]:

    try:
        response = req.get(
            f"https://www.justtherecipe.com/extractRecipeAtUrl?url={recipe_url}",
            timeout=5,
        )
    except req.exceptions.ReadTimeout:
        return None

    if response.status_code != 200:
        logging.warning(f"Call to JTR returned status code {response.status_code}")
        return None

    ingredients = [i["name"] for i in response.json()["ingredients"]]

    return list(map(strip_prep_instructions, ingredients))


def parse_schollz(recipe_url: str) -> Optional[List[str]]:

    response = req.get(
        f"https://faas.schollz.com/?import=github.com/schollz/ingredients&func=IngredientsFromURL(%22{recipe_url}%22)"
    )

    return [
        f"{i['measure']['amount']} {i['measure']['name']} {i['name']}"
        for i in response.json()["ingredients"]
    ]


def parse_response(response: req.Response) -> List[str]:

    soup = BeautifulSoup(response.content)

    ingredients = parse_ld_json(soup)
    if ingredients:
        logging.info("parsed from ld+json")
        return ingredients

    ingredients = parse_itemprops(soup)
    if ingredients:
        logging.info("parsed from itemprops")
        return ingredients

    ingredients = parse_jtr(request.args["recipe_url"])
    if ingredients:
        logging.info("parsed from JTR")
        return ingredients

    ingredients = parse_schollz(request.args["recipe_url"])
    if ingredients:
        logging.info("parsed from schollz")
        return ingredients

    return []


def classify_ingredients(ingredients: List[str]) -> List[int]:
    """Classify ingredients in one API request, preserving their input order."""
    if not ingredients:
        return []

    client = OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify every grocery ingredient into exactly one store section. "
                    "Return one section ID per input item, in the same order. "
                    "Use other only when none of the specific sections fit.\n\n"
                    + "\n".join(
                        f"{section_id}: {label}"
                        for section_id, label in ID2LABEL.items()
                    )
                ),
            },
            {"role": "user", "content": json.dumps(ingredients)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "grocery_sections",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "sections": {
                            "type": "array",
                            "items": {"type": "integer", "enum": list(ID2LABEL)},
                            "minItems": len(ingredients),
                            "maxItems": len(ingredients),
                        }
                    },
                    "required": ["sections"],
                    "additionalProperties": False,
                },
            },
        },
        extra_body={"reasoning": {"effort": "none"}},
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("OpenRouter returned no classification content")
    sections = json.loads(content)["sections"]
    if len(sections) != len(ingredients):
        raise ValueError(
            f"Expected {len(ingredients)} classifications, received {len(sections)}"
        )
    return sections


app = Flask(__name__)
CORS(app)


logging.basicConfig(level=logging.INFO)


@app.route("/")
def main():

    recipe_url = request.args["recipe_url"]
    response = req.get(
        recipe_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; MakeAGroceryList/1.0; "
                "+https://makeagrocerylist.com/)"
            )
        },
        timeout=10,
    )
    if response.status_code == 200:
        ingredients = parse_response(response)
    else:
        logging.warning(
            "Recipe URL returned %s; trying extraction fallbacks",
            response.status_code,
        )
        ingredients = parse_jtr(recipe_url) or parse_schollz(recipe_url)
        if not ingredients:
            return {"error": "Unable to download recipe"}, response.status_code

    # Preserve quantities for classification, then remove small cooking measures for display.
    labeled = [
        {
            "name": strip_parentheses_grams(strip_tsp_tbsp(ing)),
            "section": section,
        }
        for ing, section in zip(ingredients, classify_ingredients(ingredients))
    ]

    return {
        "ingredients": {
            section: list(items)
            for section, items in groupby(
                sorted(labeled, key=itemgetter("section")),
                key=itemgetter("section"),
            )
        }
    }


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/single-item/")
def single_item():

    item = request.args["item"]

    # Preserve quantities for classification, then remove small cooking measures for display.
    labeled = [
        {
            "name": strip_parentheses_grams(strip_tsp_tbsp(item)),
            "section": classify_ingredients([item])[0],
        }
    ]

    return {
        "ingredients": {
            section: list(items)
            for section, items in groupby(
                sorted(labeled, key=itemgetter("section")),
                key=itemgetter("section"),
            )
        }
    }
