FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY peppol_bridge/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY peppol_bridge /app/peppol_bridge

EXPOSE 8088

CMD ["gunicorn","-w","2","-b","0.0.0.0:8088","peppol_bridge.wsgi:app"]

