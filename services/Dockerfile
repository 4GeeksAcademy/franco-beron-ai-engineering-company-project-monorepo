FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/support-api

RUN pip install --no-cache-dir uv

COPY support-api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache -r requirements.txt

COPY support-api .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]