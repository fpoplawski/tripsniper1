# Trip Sniper

This project provides the skeleton for the `trip_sniper` service managed with [Poetry](https://python-poetry.org/). It fetches flight offers using the Amadeus Self-Service API.

## Installation

1. Install Poetry if it is not already installed:
   ```bash
   pip install poetry
   ```
2. Install the project dependencies:
   ```bash
   poetry install
   ```

## Running

To start the FastAPI application defined in `src/trip_sniper/service/app.py`:

```bash
poetry run python -m trip_sniper.service.app
```

This command runs the service's main FastAPI app.


## Getting Amadeus credentials

Create a free account on the [Amadeus for Developers Self-Service portal](https://developers.amadeus.com/self-service). After registering and verifying your email, open **My Self-Service Workspace** to create an application. The portal will display your `API key` and `API secret` which are required to call the API.

## Environment Variables

The service relies on several environment variables for external API access and
configuration. Create a `.env` file or export the variables in your shell. Key
settings include:

```ini
AMADEUS_HOST=https://api.amadeus.com     # or https://test.api.amadeus.com
AMADEUS_API_KEY=xxxxxxxxxxxxxxxx
AMADEUS_API_SECRET=yyyyyyyyyyyyyyyy
ORIGIN_IATA=WAW                          # default departure airport
DATABASE_URL=postgresql+psycopg2://user:pass@localhost/tripsniper
CELERY_BROKER_URL=redis://localhost:6379/0
BOOKING_CLIENT_ID=your_booking_client_id
BOOKING_CLIENT_SECRET=your_booking_client_secret
```

### Sample request

With the service running locally you can query flight offers:

```bash
curl "http://localhost:8000/offers?account_type=premium&limit=5"
```

## Scoring Configuration

The `steal_score` algorithm combines several feature scores using a weight table.
Default weights are:

```json
{
    "discount_pct": 0.25,
    "absolute_price_score": 0.2,
    "hotel_quality": 0.2,
    "flight_comfort": 0.15,
    "urgency_score": 0.05,
    "novelty_score": 0.05,
    "category_match": 0.1
}
```

Weights can be overridden via the environment. Provide a JSON string in
`STEAL_SCORE_WEIGHTS` or a path to a JSON file in `STEAL_SCORE_WEIGHTS_FILE`.
Missing keys fall back to the defaults.

Example using an environment variable:

```bash
export STEAL_SCORE_WEIGHTS='{"discount_pct": 0.3, "absolute_price_score": 0.15}'
```

Example JSON file (`weights.json`):

```json
{
    "discount_pct": 0.3,
    "absolute_price_score": 0.15
}
```

```bash
export STEAL_SCORE_WEIGHTS_FILE=weights.json
```

## Scheduler

`src/trip_sniper/scheduler.py` starts a Celery beat process that triggers the
data pipeline once per hour by default. To change the schedule, provide a
standard five-field cron expression in the `RUN_PIPELINE_CRON` environment
variable. The value is parsed using `celery.schedules.crontab`.

```bash
export RUN_PIPELINE_CRON="0 */6 * * *"  # run every six hours
```

