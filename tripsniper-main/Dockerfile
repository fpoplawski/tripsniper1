FROM python:3.11-slim

# Install Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY pyproject.toml poetry.lock* ./

# Install project dependencies (without development packages)
RUN poetry install --no-dev

# Copy application source
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "trip_sniper.service.app:app", "--host", "0.0.0.0", "--port", "8000"]
