FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . /app
RUN pip install --no-cache-dir .

RUN chmod +x /app/scripts/render-start.sh

# Render inyecta PORT (suele ser 10000); local puede usar 8000
EXPOSE 10000
CMD ["/app/scripts/render-start.sh"]
