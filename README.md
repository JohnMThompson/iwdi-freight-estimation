# Freight Cost Estimator

A small, explainable freight estimation application based on inverse distance weighting (IDW). It recreates the 2018 project's core workflow: choose an origin and destination, then estimate linehaul cost from nearby destinations with known observations.

All shipment observations in this project are synthetic. They are generated for this application and do not represent actual customer shipments, freight rates, or market benchmarks. The generator gives costs a plausible spatial structure so the estimator can be explored; it is not calibrated to current market data.

## Run locally

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn freight_estimator.api:app --reload
```

The API runs at `http://localhost:8000`; interactive API docs are at `/docs`.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. The development server proxies `/api` requests to the API.

## Docker Compose deployment

The production Compose setup runs two services: Nginx serves the built frontend and proxies `/api` to FastAPI over Compose's private network. Only Nginx publishes a host port. The API and frontend have health checks, and the app has no persistent state or volumes.

### Build and run locally with Compose

Docker Engine and the Docker Compose plugin must be installed ([official Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/)). From the repository root:

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
```

The example binds to `127.0.0.1`, so open `http://127.0.0.1:8080`. To reach it from other devices, change `APP_BIND_IP` in `.env` to the host's reserved LAN IPv4 address.

### Deploy on one Ubuntu Server host

Install Docker Engine and its Compose plugin using Docker's [Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/). Reserve a private LAN IPv4 address for the server in DHCP, then clone the project on Pileated:

```bash
git clone https://github.com/JohnMThompson/iwdi-freight-estimation.git
cd iwdi-freight-estimation
cp .env.example .env
nano .env
```

Set `APP_BIND_IP` in `.env` to Pileated's reserved LAN IPv4, for example `192.168.1.50`. This file is ignored by Git. Compose binds port 8080 only to that address; use `http://<PILEATED_LAN_IP>:8080` from devices on your LAN.

Build and start the services:

```bash
docker compose config
docker compose build
docker compose up -d
```

### Check status, health, and logs

```bash
docker compose ps
set -a
. ./.env
set +a
curl --fail "http://${APP_BIND_IP}:8080/healthz"
curl --fail "http://${APP_BIND_IP}:8080/api/origins"
docker compose exec backend python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/healthz', timeout=2).read().decode())"
docker compose logs --tail=100
docker compose logs -f frontend backend
```

`docker compose ps` shows both container health states. `/healthz` on the frontend checks that Nginx responds; the backend's `/healthz` only returns whether the FastAPI process is running and does not query data files or external services.

### Stop the app

```bash
docker compose down
```

This removes the containers and Compose network. There are no volumes or persistent records to remove.

### Update and redeploy

Run these commands from the cloned project directory on Pileated:

```bash
git pull --ff-only
docker compose build
docker compose up -d --remove-orphans
docker compose ps
docker compose logs --tail=100
```

The OSRM mileage table is bundled as local application data; containers make no runtime requests to OSRM. Browsers still request OpenStreetMap tiles and Google Fonts from their public services, so LAN clients need outbound internet access for those assets.

## Estimation method

For one origin, the estimator fits a linear distance baseline across that origin's known lanes: fixed charge plus a per-mile rate. It uses saved OSRM driving miles for the baseline when available, with 1.18 times great-circle distance as a fallback. For local adjustments, it filters observed destinations to a configurable maximum great-circle distance, selects up to K of the closest eligible observations, and uses inverse distance weighting to interpolate their deviations from the baseline. The estimate is the fitted baseline at the requested lane distance plus the weighted local adjustment. It never reaches beyond the configured radius to fill K. The initial working default is 600 miles; it is configurable and has not been validated as an accuracy threshold. The API returns both geographic and baseline route distances, each contributor's IDW weight, observed cost, residual from the baseline, and weighted residual adjustment, so the result can be inspected directly.

When the requested destination has an observation for the selected origin, the application returns that exact observed cost rather than calculating an interpolation. The UI labels this case as an observed rate. If no observations fall inside the selected radius, the model returns an insufficient-data result without an estimate.

Coverage is a descriptive summary of the number and proximity of observations supporting an interpolated estimate. The initial rules are Strong for at least five contributors with the furthest within 300 miles, Moderate for at least three within 450 miles, Limited for at least two within 600 miles, Sparse for a smaller or more distant set, and None when no observation qualifies. These rules are intentionally isolated and are not probability or calibrated accuracy statements; empirical validation may change them.

The map uses OpenStreetMap tiles and shows the origin, selected destination, contributing observations, and straight lines between the estimate and its neighbors. Lines visualize geographic proximity; they are not truck routes.

## Data generation

`backend/src/freight_estimator/data/synthetic.py` is intentionally separate from the estimator. A fixed random seed makes its compact dataset reproducible. Several origins receive different regional cost surfaces plus lane noise, and each origin has a sparse set of observed ZIP-like destinations. ZIPs and coordinates are representative synthetic locations, not authoritative ZIP centroid data.

The generated records are checked in at `backend/src/freight_estimator/data/shipments.csv` so the application starts with a stable, inspectable dataset. To regenerate the file after changing the generator:

```bash
cd backend
python -m freight_estimator.data.synthetic
```

`backend/src/freight_estimator/data/osrm_driving_miles.csv` contains a comparison snapshot of routed and great-circle distances for all 120 origin-destination pairs in the demo catalog. The routed distances were retrieved from the public OSRM demo service on 2026-09-30 with its `driving` profile. They follow car routing and are not truck-specific mileage. The demo service is best-effort, requests no more frequent than once per second, and does not guarantee availability ([OSRM demo guidance](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server)). OSRM routes are based on OpenStreetMap data; credit OpenStreetMap contributors and link to the [ODbL license information](https://www.openstreetmap.org/copyright).

## API

- `GET /api/origins` returns available origins.
- `GET /api/destinations?origin_id=...` returns candidate destinations and whether each has an observation for that origin.
- `POST /api/estimate` accepts an origin, destination ZIP, `k`, `p`, and `max_observation_distance_miles`; response includes estimate status, Coverage facts, and contributing observations.
- `GET /healthz` returns `{"status":"ok"}` while the FastAPI app is running; it does not check data files or other services.

Defaults are `k=5`, `p=2`, and `max_observation_distance_miles=600`. This is a small demonstration slice: there is no persistence, external market-data refresh, live ZIP geocoding, or backtesting yet.
