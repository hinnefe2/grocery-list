# Hosting overview

This project is hosted in Google Cloud under the `henry.hinnefeld@gmail.com` account. It has two independently deployed parts: a static frontend and a Python API.

## Architecture

```text
Browser
  ├── Static HTML, CSS, JavaScript, and images
  │     └── Google Cloud Storage bucket: makeagrocerylist.com
  │
  └── Recipe and ingredient requests
        └── Google Cloud Run service: grocery-list
              Region: us-central1
              URL: https://grocery-list-5ybpug4gia-uc.a.run.app
              ├── Extracts ingredients from recipe URLs
              └── Classifies ingredients by grocery-store section through OpenRouter
```

## Static frontend

The frontend consists primarily of:

- `index.html`: grocery-list application
- `landing.html`: marketing/landing page
- `grocerylist.js`: browser behavior and the Cloud Run API URL
- `grocerylist.css`: application styling
- `images/` and root-level image files: static assets

Pushes to `main` run `.github/workflows/main.yaml`, which syncs the static files to the `makeagrocerylist.com` Google Cloud Storage bucket. The workflow authenticates with the `google_service_account_credentials` GitHub Actions secret.

The workflow deliberately excludes backend source and deployment files. It does not deploy Cloud Run.

Shared lists store base64-encoded JSON in the URL. Unicode is escaped in the JSON
before encoding, and the base64 query value is URL-encoded. Older Latin-1 links
remain readable. Run frontend import and shared-link regression tests with
`node .github/tests/test_grocerylist.cjs` (Node.js 18 or newer; no npm dependencies).

## Backend API

The backend is a Flask service defined in `service.py` and packaged with `Dockerfile`. The browser calls it directly using the hostname configured near the top of `grocerylist.js`.

The API has these routes:

- `GET /?recipe_url=...`: downloads a recipe, extracts its ingredients, and classifies them.
- `GET /single-item/?item=...`: classifies one manually entered grocery item.
- `GET /sections`: returns section IDs, labels, and icon paths for the frontend.
- `GET /health`: reports service health.

The service returns ingredients grouped under numeric section IDs. The `GROCERY_SECTIONS` list in `config.py` defines each section’s permanent ID, label, classification description, and icon path. Add an entry and its image to introduce a section; do not renumber existing IDs because saved lists use them. The frontend loads section metadata from `/sections`. Classification uses OpenRouter’s Decisions endpoint with the existing API key.

The Docker image installs dependencies from `requirements.txt` and runs Flask behind Gunicorn. Cloud Run deployment is separate from the GitHub Actions workflow and must currently be performed manually or through GCP tooling outside this repository.

## Recipe extraction

Successfully downloaded pages are checked for JSON-LD `recipeIngredient` lists first,
including objects, arrays, nested `@graph` entries, and multiple JSON-LD scripts.
If none is usable, the backend removes scripts, styles, comments, navigation, and
other clutter from the HTML and sends it to OpenRouter Chat Completions for a
structured ingredient list. Ingredient quantities, units, and preparation wording
are preserved during extraction; only whitespace is normalized.

After any extraction source succeeds, a separate batched model call rewrites the
lines into concise shopping entries. It removes prep instructions and redundant
conversions, preserves fractional quantities without rounding
(for example, `1/2 white onion, chopped (113g)` becomes `1/2 white onion`),
and removes small spoon measures for seasonings, oils, and condiments. Useful
weights, volumes, package sizes, counts, varieties, and shopping forms such as
canned, frozen, or dried are retained. Cleanup keeps one entry per original line;
it does not combine duplicates or invent package/bunch sizes. If cleanup fails,
returns incomplete/invalid output, or times out, the original lines are used.

Grocery-section classification uses the original ingredient lines so display
cleanup does not discard classification context. Manually entered items bypass
model cleanup. All three model tasks have independent model settings.

JustTheRecipe and schollz remain recovery services for failed downloads (non-200
responses or request failures), in that order. They are not called when a downloaded
page has no ingredients or model extraction fails. Each recovery request has a
five-second timeout, and an invalid response from the first service allows the
second to run.

HTML model extraction is limited to 120,000 cleaned characters and 4,096 output
tokens. Oversize inputs and incomplete/invalid model responses fail explicitly
rather than returning a partial list. The recipe endpoint returns JSON errors:
`422` when no ingredients are found, `502` for extraction failures, and the
original upstream status when download recovery fails (`502` for network errors).
The Gunicorn worker timeout is 90 seconds to accommodate fetching, extraction,
cleanup, and classification in sequence.

Run the mocked backend checks with `python -m unittest discover -s tests -v`.
These cover parsing, model request/response handling, cleanup fallback, and download recovery;
they do not measure live model accuracy or external-service availability.

## Runtime configuration

The Cloud Run service requires:

- `OPENROUTER_API_KEY`: required; expose Google Secret Manager secret `projects/303187280065/secrets/openrouter-api-key` to the container under this name.
- `OPENROUTER_MODEL`: optional classification model; defaults to `openai/gpt-6-luna-decisions`.
- `OPENROUTER_EXTRACTION_MODEL`: optional HTML extraction model; defaults to `anthropic/claude-haiku-4.5`. Uses the same `OPENROUTER_API_KEY`; the selected provider must support JSON Schema structured outputs.
- `OPENROUTER_CLEANUP_MODEL`: optional shopping-entry cleanup model; defaults to `anthropic/claude-haiku-4.5`. Uses the same API key and requires JSON Schema structured outputs. Cleanup adds one batched call per recipe.
- `PORT`: supplied automatically by Cloud Run.

Do not put API keys in `grocerylist.js`, committed files, the Docker image, or the static storage bucket. Local `.env` files are ignored by Git.

## Operational notes

- The Cloud Run endpoint is publicly reachable and currently permits cross-origin browser requests.
- Because classification incurs OpenRouter usage, production should have request limits and abuse protection.
- Recipe URLs are fetched by the backend, so URL validation should be added before treating the service as hardened against untrusted traffic.
- Updating frontend files and updating the API are separate deployments.
