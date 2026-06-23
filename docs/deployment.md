# Oracle Cloud Deployment Runbook

The production topology is:

```text
Browser
  |
  v
Vercel (Next.js frontend and same-origin API proxy)
  |
  v
Oracle Cloud VM (Caddy HTTPS)
  |
  +--> Django/Gunicorn container
  +--> persistent Redis container
  +--> Nominatim and OSRM
```

## 1. Create the Oracle VM

1. Sign in to Oracle Cloud and open **Compute > Instances**.
2. Select **Create instance**.
3. Use an Ubuntu 24.04 image.
4. Select the Always Free eligible `VM.Standard.A1.Flex` shape.
5. Configure **2 OCPUs and 12 GB RAM**.
6. Use a public subnet and enable **Assign a public IPv4 address**.
7. Add your SSH public key.
8. Keep the boot volume within the Always Free allowance.
9. Create the instance and record its public IPv4 address.

If Oracle reports insufficient A1 capacity, try another availability domain or
retry later. Always Free capacity is not guaranteed.

## 2. Reserve the public IP

An ephemeral address can change if the VM is recreated. In Oracle:

1. Open the instance.
2. Open **Attached VNICs**, then the primary VNIC and private IP.
3. Edit the public IP assignment.
4. Select **Reserved public IP** and create or assign one.

Record the reserved address as `<ORACLE_PUBLIC_IP>`.

## 3. Open network ports

Open the VCN security list or network security group attached to the VM.

Add stateful ingress rules:

| Source CIDR | Protocol | Destination port | Purpose |
| --- | --- | --- | --- |
| Your public IP `/32` | TCP | `22` | SSH administration |
| `0.0.0.0/0` | TCP | `80` | HTTP and certificate issuance |
| `0.0.0.0/0` | TCP | `443` | HTTPS API |
| `0.0.0.0/0` | UDP | `443` | HTTP/3, optional |

Do not expose Redis port `6379` or Django port `8000`.

## 4. Create the API hostname

Caddy needs a hostname pointing to the VM before it can issue HTTPS.

Preferred: create an `A` record such as:

```text
api.yourdomain.com -> <ORACLE_PUBLIC_IP>
```

No domain: create a free DuckDNS hostname and set its current IP to
`<ORACLE_PUBLIC_IP>`, for example:

```text
fuelup-api.duckdns.org
```

Wait until this resolves to the Oracle IP:

```bash
dig +short api.yourdomain.com
```

## 5. Connect and install Docker

```bash
chmod 600 /path/to/oracle-private-key
ssh -i /path/to/oracle-private-key ubuntu@<ORACLE_PUBLIC_IP>
```

Clone the repository:

```bash
git clone https://github.com/<YOUR_GITHUB_USER>/<YOUR_REPOSITORY>.git FuelUp
cd FuelUp
```

Install Docker from Docker's official Ubuntu repository:

```bash
chmod +x deploy/oracle/bootstrap-ubuntu.sh
./deploy/oracle/bootstrap-ubuntu.sh
exit
```

Reconnect so the Docker group membership takes effect:

```bash
ssh -i /path/to/oracle-private-key ubuntu@<ORACLE_PUBLIC_IP>
cd FuelUp
docker version
docker compose version
```

## 6. Configure production secrets

```bash
cp .env.oracle.example .env.oracle
openssl rand -base64 48
nano .env.oracle
```

Set at minimum:

```dotenv
API_DOMAIN=api.yourdomain.com
DJANGO_SECRET_KEY=<OUTPUT_FROM_OPENSSL>
EXTERNAL_API_USER_AGENT=FuelUp/1.0 (contact: your-real-email@example.com)
```

`.env.oracle` is ignored by Git. Do not commit it.

## 7. Start the backend

```bash
chmod +x deploy/oracle/deploy.sh
./deploy/oracle/deploy.sh
```

The deployment script:

1. Fast-forwards the Git checkout.
2. Builds the ARM64-compatible Django image.
3. Starts Redis, Django, and Caddy.
4. Waits for the public readiness endpoint.

Verify directly:

```bash
curl https://api.yourdomain.com/api/health/live/
curl https://api.yourdomain.com/api/health/ready/
```

Inspect failures:

```bash
docker compose --env-file .env.oracle -f compose.oracle.yaml ps
docker compose --env-file .env.oracle -f compose.oracle.yaml logs -f
```

## 8. Point Vercel to Oracle

In Vercel, open the frontend project:

1. Go to **Settings > Environment Variables**.
2. Change `DJANGO_API_BASE_URL` to:

```text
https://api.yourdomain.com
```

3. Apply it to Production and Preview.
4. Redeploy the frontend.

Do not include `/api` or a trailing slash.

## 9. Verify the migration

```bash
curl -i -X POST https://your-vercel-project.vercel.app/api/route \
  -H "Content-Type: application/json" \
  -d '{"start":"Austin, TX","finish":"Denver, CO"}'
```

Confirm:

- The first request succeeds without a Render wake-up delay.
- The response has `X-FuelUp-Cache: HIT` or `MISS`.
- Repeating the exact request returns `X-FuelUp-Cache: HIT`.
- The browser displays the blue route and fuel-stop markers.

After verification, suspend or delete the Render services to avoid maintaining
two backends.

## Updating production

After pushing changes to GitHub:

```bash
ssh -i /path/to/oracle-private-key ubuntu@<ORACLE_PUBLIC_IP>
cd FuelUp
./deploy/oracle/deploy.sh
```

Docker services use `restart: unless-stopped`, so they return automatically
after a normal VM reboot.

## Rollback

```bash
cd FuelUp
git log --oneline -10
git checkout <KNOWN_GOOD_COMMIT>
SKIP_GIT_PULL=true ORACLE_ENV_FILE=.env.oracle ./deploy/oracle/deploy.sh
```

Return to the deployment branch afterward:

```bash
git switch main
```

## Always Free limitation

Oracle does not routinely sleep the VM after a few idle minutes like Render.
However, Oracle documents that an Always Free compute instance can be reclaimed
when CPU, network, and (for A1) memory utilization all remain below its idle
thresholds over a seven-day period. Keep the Git repository as the source of
truth and treat the Redis volume as a rebuildable cache, not permanent business
data.
