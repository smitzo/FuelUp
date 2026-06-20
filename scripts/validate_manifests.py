import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


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
    print("Deployment manifests are structurally valid.")


if __name__ == "__main__":
    main()

