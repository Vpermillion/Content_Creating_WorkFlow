# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --chown=1000:1000 whatif ./whatif
COPY --chown=1000:1000 profiles ./profiles
COPY --chown=1000:1000 pilots ./pilots
COPY scripts/container-start.sh /usr/local/bin/whatif-start
RUN mkdir /data && chown 1000:1000 /data && chmod 755 /usr/local/bin/whatif-start
USER 1000:1000
ENV WORKSPACE_DIR=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8090
CMD ["/usr/local/bin/whatif-start"]
