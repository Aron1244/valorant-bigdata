FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY voting_api.py .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "voting_api:app", "--host", "0.0.0.0", "--port", "8080"]
