"""List deployments visible to the configured SAP AI Core resource group."""

from __future__ import annotations

import os
import json

import httpx

from ai_core import _token


def get(url: str, headers: dict[str, str]) -> dict[str, object]:
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    base_url = os.environ["AICORE_BASE_URL"].rstrip("/")
    headers = {
        "Authorization": f"Bearer {_token()}",
        "AI-Resource-Group": os.getenv("AICORE_RESOURCE_GROUP", "default"),
    }
    payload = get(f"{base_url}/v2/lm/deployments", headers)
    deployments = payload.get("resources", payload.get("deployments", payload))
    if not deployments:
        print("No deployments found in this resource group.")
        return
    for deployment in deployments:
        if deployment.get("status") != "RUNNING":
            continue
        deployment_id = deployment["id"]
        details = get(f"{base_url}/v2/lm/deployments/{deployment_id}", headers)
        configuration_id = details.get("configurationId")
        configuration = (
            get(f"{base_url}/v2/lm/configurations/{configuration_id}", headers)
            if configuration_id
            else {}
        )
        print(
            json.dumps(
                {
                    "deploymentId": deployment_id,
                    "configurationId": configuration_id,
                    "deployment": details,
                    "configuration": configuration,
                },
                separators=(",", ":"),
            )
        )


if __name__ == "__main__":
    main()