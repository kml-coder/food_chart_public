# base image
FROM python:3.10-slim

# work dir
WORKDIR /server

# copy everything
COPY . .

# pakage install
RUN pip install --no-cache-dir -r requirements.txt

# server run
CMD ["python3", "server.py"]