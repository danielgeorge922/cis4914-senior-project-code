FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
# CPU-only torch for the OWL-ViT crop in retrieval mode.
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY data data

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
