# acikpoz MCP server, containerised.
#
# Runs `acikpoz-mcp` over stdio so any MCP-speaking runtime — Claude Desktop/Code,
# or Glama's inspector — can parse a catalog without a local Python install. Mount
# the catalog PDF you want parsed read-only:
#
#   docker build -t acikpoz .
#   docker run --rm -i -v "$PWD:/work:ro" -w /work acikpoz
#
# (For the CLI instead of the server, override the entrypoint:
#   docker run --rm -v "$PWD:/work" -w /work --entrypoint acikpoz acikpoz parse bf2026.pdf)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY . /app

# Install with the MCP extra; the [mcp] server is the entrypoint.
RUN pip install ".[mcp]"

# Drop privileges: the server only ever reads the PDF an agent points it at.
RUN useradd --create-home --uid 1000 acikpoz
USER acikpoz

# stdio transport — the runtime speaks MCP over stdin/stdout.
ENTRYPOINT ["acikpoz-mcp"]
