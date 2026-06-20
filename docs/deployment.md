# Deployment Runbook

The intended production topology is:

```text
Browser
  |
  v
Vercel (Next.js frontend and same-origin API proxy)
  |
  v
Render (Django API container)
  |
  +--> Render Key Value (cache and rate-limit counters)
  |
  +--> Nominatim and OSRM
```

## Deploy the backend to Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and select the repository.
3. Render reads `render.yaml` and creates:
   - The `fuelup-api` Docker web service.
   - The private `fuelup-cache` Key Value instance.
4. When prompted for `EXTERNAL_API_USER_AGENT`, provide an application name
   and monitored contact email as required by Nominatim's usage policy.
5. Wait for `/api/health/ready/` to pass.
6. Record the public API URL, for example:
   `https://fuelup-api.onrender.com`.

The Blueprint uses Render's free web-service and Key Value instance types, so
no payment method is required. Free services are suitable for portfolio and
evaluation deployments, but they have availability and capacity limitations.
The web service can sleep after inactivity. The Next.js proxy waits for
readiness and retries the route request for up to 90 seconds rather than
reporting an immediate false outage.

Startup runs `warm_route_cache --best-effort` before Gunicorn. This can make a
fresh deployment take longer to become ready, but Los Angeles to New York,
Austin to Denver, and Seattle to Miami are cached when startup finishes.

Before attaching a custom domain, update `DJANGO_ALLOWED_HOSTS` to include it.
For example:

```text
.onrender.com,api.fuelup.example
```

## Deploy the frontend to Vercel

1. In Vercel, import the same Git repository.
2. Set the project Root Directory to `frontend`.
3. Keep the detected framework preset as Next.js.
4. Set the Node.js version to 20.
5. Add this environment variable for Production and Preview:

```text
DJANGO_API_BASE_URL=https://fuelup-api.onrender.com
```

6. Deploy and verify that a route request succeeds.

`frontend/vercel.json` configures the route proxy's function duration and
security headers. `DJANGO_API_BASE_URL` is server-only and is not exposed in
the browser bundle.

## Production verification

Backend:

```bash
curl https://fuelup-api.onrender.com/api/health/live/
curl https://fuelup-api.onrender.com/api/health/ready/
```

Frontend:

```bash
curl -I https://your-vercel-project.vercel.app
```

Functional API check:

```bash
curl -X POST https://your-vercel-project.vercel.app/api/route \
  -H "Content-Type: application/json" \
  -d '{"start":"Austin, TX","finish":"Dallas, TX"}'
```

Confirm the response includes:

- `X-Request-ID`
- `X-FuelUp-Cache`
- `X-FuelUp-Cache-TTL`
- `X-RateLimit-Limit`
- A blue route and numbered fuel stops in the browser

Run the same request twice. The first response may report
`X-FuelUp-Cache: MISS`; the second should report `HIT`. The default TTL is 30
days. Render's free Key Value instance has no disk persistence, so a cache
restart or eviction can still remove an entry before that TTL expires.

## Rollback

Both Render and Vercel retain previous deploys. Roll back the frontend and
backend independently to the same known-good Git commit. Cache keys include a
schema version, so application rollbacks do not require manually flushing
Redis unless the serialized response contract changed without a cache-version
bump.
