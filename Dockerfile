FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml
COPY server.py sovereign_proxy.py agent_runner.py ./
COPY agents/ ./agents/
EXPOSE 8001
CMD ["python", "server.py"]
