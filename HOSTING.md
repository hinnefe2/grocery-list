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

## Backend API

The backend is a Flask service defined in `service.py` and packaged with `Dockerfile`. The browser calls it directly using the hostname configured near the top of `grocerylist.js`.

The API has these routes:

- `GET /?recipe_url=...`: downloads a recipe, extracts its ingredients, and classifies them.
- `GET /single-item/?item=...`: classifies one manually entered grocery item.
- `GET /sections`: returns section IDs, labels, and icon paths for the frontend.
- `GET /health`: reports service health.

The service returns ingredients grouped under numeric section IDs. The `GROCERY_SECTIONS` list in `config.py` defines each section’s permanent ID, label, classification description, and icon path. Add an entry and its image to introduce a section; do not renumber existing IDs because saved lists use them. The frontend loads section metadata from `/sections`. Classification uses OpenRouter’s Decisions endpoint with the existing API key.

The Docker image installs dependencies from `requirements.txt` and runs Flask behind Gunicorn. Cloud Run deployment is separate from the GitHub Actions workflow and must currently be performed manually or through GCP tooling outside this repository.

## Runtime configuration

The Cloud Run service requires:

- `OPENROUTER_API_KEY`: required; expose Google Secret Manager secret `projects/303187280065/secrets/openrouter-api-key` to the container under this name.
- `OPENROUTER_MODEL`: optional; defaults to `openai/gpt-6-luna-decisions`.
- `PORT`: supplied automatically by Cloud Run.

Do not put API keys in `grocerylist.js`, committed files, the Docker image, or the static storage bucket. Local `.env` files are ignored by Git.

## Operational notes

- The Cloud Run endpoint is publicly reachable and currently permits cross-origin browser requests.
- Because classification incurs OpenRouter usage, production should have request limits and abuse protection.
- Recipe URLs are fetched by the backend, so URL validation should be added before treating the service as hardened against untrusted traffic.
- Updating frontend files and updating the API are separate deployments.
