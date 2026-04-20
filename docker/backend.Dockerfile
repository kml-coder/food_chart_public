FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir beautifulsoup4 requests

COPY food_server/server.py /app/server.py

EXPOSE 5050

CMD ["python", "server.py"]
