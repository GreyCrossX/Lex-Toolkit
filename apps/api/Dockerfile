FROM python:3.12-slim

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

# Install deps via uv using the root pyproject/uv.lock.
COPY pyproject.toml uv.lock /workspace/
RUN pip install --no-cache-dir uv \
  && uv export --frozen --no-dev --no-hashes --format requirements.txt > /tmp/requirements.txt \
  && pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the API source
WORKDIR /workspace/apps/api
COPY apps/api /workspace/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
