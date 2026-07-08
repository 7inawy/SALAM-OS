FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY services/evidence-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared kernel and infrastructure (dependency direction enforced)
COPY shared/ ./shared/

# Copy service code
COPY services/evidence-engine/ ./services/evidence-engine/

ENV PYTHONPATH=/app
ENV SERVICE_NAME=evidence-engine

EXPOSE 8000

CMD ["uvicorn", "services.evidence-engine.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
