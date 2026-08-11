# FitStat — Offline Docker Deployment

This deployment is designed for the PySide6 desktop application. It does not require a remote server at runtime. The application container contains the Python application, ML components, RAG/Chroma components, and the local FastAPI process already used by `run.py`; Ollama is provided as a separate local container for the fine-tuned LLM.

## Architecture

Host OS / WSL2 + Docker Desktop

- `fitstat-app`
  - PySide6 desktop UI
  - FastAPI/Uvicorn local API
  - Math/ED calculation
  - anomaly detector / LightGBM
  - RAG + local ChromaDB
  - database and application logic
- `fitstat-ollama`
  - local Ollama runtime
  - persistent model volume
  - fine-tuned FitStat model

The repository currently contains the Ollama client integration in `transformer/recommender.py`, where the model is named `fitpulse` and the client points to `127.0.0.1:11434`. For the container deployment this must be changed to the Compose service name (`ollama`) and the final model name should be renamed to `fitstat` after the repository rename.

## Important: LLM artifact

The Git repository contains the application-side Ollama integration, but it does not provide the final Ollama model artifact itself. Before an actually air-gapped installation, import the fine-tuned model into Ollama and persist it in the `ollama_models` volume.

Recommended workflow on an internet-connected machine:

1. Install/pull the exact base model used for fine-tuning.
2. Create the final Ollama model from the fine-tuned GGUF/model artifact using a `Modelfile`.
3. Verify `ollama run fitstat` locally.
4. Export/save the Ollama model data or prepare the Docker volume for transfer to the offline machine.
5. On the offline machine, start the same Compose stack with the transferred model volume.

Do not make the first model download part of normal application startup; that would violate the offline requirement.

## Windows + Docker Desktop + PySide6

A desktop Qt application needs access to the host display. The exact display mechanism depends on the host:

- Windows 11 + WSLg: prefer running the Linux container from the WSL2 environment with the WSLg display/socket available.
- Windows with an external X server: set `DISPLAY` to the X server address and permit the container connection.

The included Compose file is a baseline for the WSL/Linux display path. If the target machine is native Windows without WSLg, the display section should be adapted to the chosen X server.

## Build

From the repository root:

    docker compose -f deployment/docker-compose.yml build

## Start

    docker compose -f deployment/docker-compose.yml up -d

## Stop

    docker compose -f deployment/docker-compose.yml down

## Persistent data

The following host directories are mounted into the application container:

- `data/` — application database/history and local RAG data
- `models/` — optional application-side ML model artifacts
- `logs/` — runtime logs

Ollama models are stored in the named volume `ollama_models`.

## Recommended final repository layout

    deployment/
      Dockerfile
      docker-compose.yml
      requirements-docker.txt
      README.md
    models/
      ... ML artifacts ...
    data/
      chroma_db/
      ... application data ...
    logs/

## Final integration change

Before the final FitStat release, update `transformer/recommender.py` from a hard-coded local host:

    ollama.Client(host="http://127.0.0.1:11434")

and model name:

    MODEL_NAME = "fitpulse"

into environment-configurable values, for example:

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    MODEL_NAME = os.getenv("OLLAMA_MODEL", "fitstat")

This lets the same code run directly on the host or inside Docker without code changes.
