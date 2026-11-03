# IDs are permanent: saved grocery lists refer to them. Give new sections a new
# ID rather than renumbering existing ones, and add their icon under images/.
GROCERY_SECTIONS = [
    {
        "id": 0,
        "label": "produce",
        "description": (
            "Fresh fruits, vegetables, peppers, corn, garlic, onions, citrus, and fresh "
            "herbs such as cilantro. Includes juice from fresh citrus used as a recipe "
            "ingredient."
        ),
        "icon": "images/0.png",
    },
    {
        "id": 1,
        "label": "meat/seafood/deli",
        "description": "Fresh meat, poultry, seafood, and deli meat.",
        "icon": "images/1.png",
    },
    {
        "id": 2,
        "label": "dairy",
        "description": "Milk, butter, cheese (including feta), yogurt, cream, and eggs.",
        "icon": "images/2.png",
    },
    {
        "id": 3,
        "label": "canned",
        "description": "Canned or jarred vegetables, beans, soup, and similar goods.",
        "icon": "images/3.png",
    },
    {
        "id": 4,
        "label": "dry goods/baking",
        "description": "Flour, sugar, grains, pasta, bread, and baking goods.",
        "icon": "images/4.png",
    },
    {
        "id": 5,
        "label": "oil/sauce/condiment",
        "description": "Cooking oils, mayonnaise, sauces, dressings, vinegar, and condiments.",
        "icon": "images/5.png",
    },
    {
        "id": 6,
        "label": "spices",
        "description": (
            "Salt, pepper, dried herbs, chili powder, and seasonings. Fresh herbs belong "
            "in produce."
        ),
        "icon": "images/6.png",
    },
    {
        "id": 7,
        "label": "frozen",
        "description": (
            "Any food explicitly sold frozen, even if it would otherwise fit another "
            "section."
        ),
        "icon": "images/7.png",
    },
    {
        "id": 8,
        "label": "drinks/beverages",
        "description": (
            "Ready-to-drink beverages: water, soda, juice, coffee, tea, sports drinks, "
            "beer, wine, and liquor. Excludes juice from fresh citrus used only as a "
            "recipe ingredient, such as juice from one lime."
        ),
        "icon": "images/8.png",
    },
    {
        "id": 9,
        "label": "other",
        "description": "Non-food items or items that truly fit no other section.",
        "icon": "images/9.png",
    },
]

if len({section["id"] for section in GROCERY_SECTIONS}) != len(GROCERY_SECTIONS):
    raise ValueError("Grocery section IDs must be unique")
