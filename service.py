import json
import logging
import re


import requests as req

from itertools import groupby
from operator import itemgetter
from typing import List, Optional

from bs4 import BeautifulSoup
from flask import Flask, request
from flask_cors import CORS
from transformers import pipeline, Pipeline

from config import LABEL2ID


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
            return ingredient.split(split_token)[0].rstrip(", ")

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


def classify_ingredient(pipe: Pipeline, ingredient: str) -> int:
    label = pipe(ingredient).pop(0)["label"]
    print(f"\t{label:<16} {ingredient}")
    return LABEL2ID[label]


app = Flask(__name__)
CORS(app)


logging.basicConfig(level=logging.INFO)
pipe = pipeline("text-classification", model="model-files/")


@app.route("/")
def main():

    response = req.get(request.args["recipe_url"])
    if response.status_code != 200:
        return response.status_code

    ingredients = parse_response(response)

    # strip tsp/tbsp separate from classifying because the classifier was trained on ingredient
    # strings which include tsp / tbsp units
    labeled = [
        {
            "name": strip_parentheses_grams(strip_tsp_tbsp(ing)),
            "section": classify_ingredient(pipe, ing),
        }
        for ing in ingredients
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
