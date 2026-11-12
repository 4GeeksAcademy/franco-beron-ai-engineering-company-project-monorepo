FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for production security
RUN groupadd -r nexova && useradd -r -g nexova -m -d /home/nexova -s /sbin/nologin nexova

WORKDIR /app/support-api

RUN pip install --no-cache-dir uv

COPY services/support-api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache -r requirements.txt

COPY data/pipelines/nexova_rag /app/data/pipelines/nexova_rag
COPY CONTEXT.md /app/CONTEXT.md
RUN uv pip install --system --no-cache -e /app/data/pipelines/nexova_rag

COPY services/support-api/ .
COPY packages/shared/incident_validation.py /app/packages/shared/incident_validation.py

# Restrict filesystem permissions
RUN chown -R nexova:nexova /app && \
    chmod -R 755 /app && \
    chmod 750 /app/support-api/data/raw

EXPOSE 8001

# Drop root privileges before running the application
USER nexova

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]