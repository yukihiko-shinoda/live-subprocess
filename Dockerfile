FROM futureys/claude-code-python-development:20260221145500
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For testing
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /workspace/
RUN uv sync --python 3.13 \
 && uv cache clean
COPY . /workspace/
ENTRYPOINT [ "uv", "run" ]
