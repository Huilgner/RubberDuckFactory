FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml && pip install uvicorn
COPY server.py sovereign_proxy.py cost_tracker.py ./
COPY agents/ ./agents/
EXPOSE 8001
CMD ["python", "server.py"]
