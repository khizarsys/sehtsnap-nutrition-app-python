# Build from the repository root:
# docker build -f backend/Dockerfile -t sehtsnap-api .
FROM python:3.13-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/srv:/srv/src

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/app backend/app
COPY src/sehtsnap/__init__.py src/sehtsnap/__init__.py
COPY src/sehtsnap/core/__init__.py src/sehtsnap/core/__init__.py
COPY src/sehtsnap/core/config.py src/sehtsnap/core/config.py
COPY src/sehtsnap/models src/sehtsnap/models
COPY src/sehtsnap/services/__init__.py src/sehtsnap/services/__init__.py
COPY src/sehtsnap/services/ai_vision_service.py src/sehtsnap/services/ai_vision_service.py

USER nobody
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn --factory backend.app.main:create_app --host 0.0.0.0 --port ${PORT:-8080}"]
