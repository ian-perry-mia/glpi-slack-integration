FROM python:3.12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install git -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/ian-perry-mia/glpi-slack-integration.git . && \
    rm -rf .git

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs && chmod 777 /app/logs

COPY . .

# This is being used in a docker compose context, therefore no need to specify port.

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]