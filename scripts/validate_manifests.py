import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE_REQUIRED_FIELDS = {
    "slug",
    "owner",
    "purpose",
    "terms_url",
    "permission_status",
    "permission_evidence",
    "permitted_use",
    "attribution",
    "automated_access_allowed",
    "enabled",
    "refresh_budget_per_day",
    "retention_policy",
}


def main():
    render = yaml.safe_load((ROOT / "render.yaml").read_text())
    services = {service["name"]: service for service in render["services"]}
    assert services["fuelup-api"]["healthCheckPath"] == "/api/health/ready/"
    assert services["fuelup-api"]["runtime"] == "docker"
    assert services["fuelup-cache"]["type"] == "keyvalue"

    vercel = json.loads((ROOT / "frontend" / "vercel.json").read_text())
    assert vercel["framework"] == "nextjs"
    assert "app/api/route/route.ts" in vercel["functions"]

    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    assert {"backend", "frontend", "redis"} <= set(compose["services"])

    openapi = yaml.safe_load((ROOT / "openapi.yaml").read_text())
    assert openapi["openapi"] == "3.1.0"
    assert "/api/v2/route/" in openapi["paths"]
    assert openapi["paths"]["/api/v2/route/"]["post"]["operationId"] == "planRouteV2"
    assert (
        openapi["paths"]["/api/v2/stations/"]["get"]["operationId"] == "listStationsV2"
    )
    assert (
        openapi["paths"]["/api/v2/stations/{station_id}/"]["get"]["operationId"]
        == "getStationV2"
    )

    source_registry = json.loads((ROOT / "data" / "source-registry.json").read_text())
    assert source_registry["schema_version"] == 1
    sources = source_registry["sources"]
    assert sources
    assert len({source["slug"] for source in sources}) == len(sources)
    for source in sources:
        assert SOURCE_REQUIRED_FIELDS <= source.keys()
        assert source["terms_url"].startswith("https://")
        assert source["refresh_budget_per_day"] >= 0
        if source["enabled"]:
            assert source["automated_access_allowed"]
            assert source["permission_status"].startswith("approved")

    attribution = json.loads(
        (ROOT / "data" / "generated-data-attribution.json").read_text()
    )
    assert attribution["schema_version"] == 1
    assert attribution["artifacts"]
    for artifact in attribution["artifacts"]:
        assert {"path", "runtime_scope", "source", "licence", "attribution_url"} <= (
            artifact.keys()
        )
        assert artifact["attribution_url"].startswith("https://")

    postman = json.loads(
        (
            ROOT / "docs" / "postman" / "FuelUp-Route-API.postman_collection.json"
        ).read_text()
    )
    assert postman["item"]
    for item in postman["item"]:
        assert item["request"]["url"]["raw"].endswith("/api/v2/route/")

    print("Deployment, API, and data-source manifests are structurally valid.")


if __name__ == "__main__":
    main()
