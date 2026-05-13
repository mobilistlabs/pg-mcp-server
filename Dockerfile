# Dockerfile
FROM python:3.13-slim

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tzdata \
    && ln -snf /usr/share/zoneinfo/Europe/Istanbul /etc/localtime \
    && echo "Europe/Istanbul" > /etc/timezone

# Download the latest uv installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Move uv to a global path accessible by all users
RUN mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv lock && uv sync --frozen

# Create non-root user and set ownership
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app

USER appuser

# Run the application
CMD ["uv", "run", "-m", "server.app"]
