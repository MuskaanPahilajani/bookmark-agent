# BookmarkAI Synchronizer

A Manifest V3 Chrome/Edge extension backed by FastAPI, LangGraph, and a stdio MCP subprocess. Bookmark lists are stored in `bookmarks.json` and supplied directly to GPT-4.1 for semantic operations.

## Run locally

1. Create a virtual environment and install `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`, populate the SAP AI Core AI Proxy URL, token, and deployment ID, then load those variables in your shell.
3. Run `python fastapi_bookmarks.py`. The API listens on port 8080.
4. Load the `extension` directory as an unpacked extension in Chrome or Edge. Enter `http://localhost:8080` as its backend URL.

## Deploy to Render

Create a Render Blueprint from this repository, then enter `AICORE_BASE_URL`, `AICORE_AUTH_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, and `AICORE_DEPLOYMENT_ID` as environment variables in the Render dashboard. Set `AICORE_RESOURCE_GROUP` to `default` unless your deployment uses another group. The included disk mounts at `/var/data`, so bookmark data persists across deploys and restarts. After deployment, copy the service URL into the extension's Backend URL field.
