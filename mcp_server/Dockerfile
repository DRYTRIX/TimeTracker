FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8090

COPY mcp_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mcp_server /app/mcp_server

RUN useradd -m -u 1000 mcp \
    && chown -R mcp:mcp /app
USER mcp

EXPOSE 8090

CMD ["python", "-m", "mcp_server", "--transport", "streamable-http"]
