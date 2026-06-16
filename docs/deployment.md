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

The Blueprint intentionally uses paid `starter` resources. Render documents
free services as non-production resources with availability limitations.

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
- `X-RateLimit-Limit`
- A blue route and numbered fuel stops in the browser

## Rollback

Both Render and Vercel retain previous deploys. Roll back the frontend and
backend independently to the same known-good Git commit. Cache keys include a
schema version, so application rollbacks do not require manually flushing
Redis unless the serialized response contract changed without a cache-version
bump.
