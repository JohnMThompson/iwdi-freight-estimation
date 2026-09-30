FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "freight_estimator.api:app", "--host", "0.0.0.0", "--port", "8000"]
