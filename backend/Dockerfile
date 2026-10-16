FROM python:3.12-slim AS deps
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY --from=deps /install /usr/local
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini entrypoint.sh ./
RUN addgroup --system --gid 10001 api && adduser --system --uid 10001 --ingroup api api \
 && chmod +x entrypoint.sh
USER 10001
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
CMD ["./entrypoint.sh"]
