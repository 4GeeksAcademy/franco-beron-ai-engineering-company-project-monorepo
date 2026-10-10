FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/support-api

RUN pip install --no-cache-dir uv

COPY services/support-api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache -r requirements.txt

COPY services/support-api/ .
COPY packages/shared/incident_validation.py /app/packages/shared/incident_validation.py

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--reload-dir", "/app/support-api", "--reload-dir", "/app/packages/shared"]