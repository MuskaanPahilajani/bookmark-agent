# BookmarkAI Synchronizer

A Manifest V3 Chrome/Edge extension backed by FastAPI, LangGraph, and a stdio MCP subprocess. Bookmark lists are stored in `bookmarks.json` and supplied directly to OpenAI for semantic operations.

## Run locally

1. Create a virtual environment and install `pip install -r requirements.txt`.
2. Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in your shell. The default model is `gpt-4o-mini`.
3. Run `python fastapi_bookmarks.py`. The API listens on port 8080.
4. Load the `extension` directory as an unpacked extension in Chrome or Edge. Enter `http://localhost:8080` as its backend URL.

## Deploy to Render

Create a Render Blueprint from this repository, then add `OPENAI_API_KEY` as a secret environment variable in the Render dashboard. Set `OPENAI_MODEL` to an available model such as `gpt-4o-mini`. The included disk mounts at `/var/data`, so bookmark data persists across deploys and restarts. After deployment, copy the service URL into the extension's Backend URL field.
