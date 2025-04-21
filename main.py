from fastapi import FastAPI, Request, HTTPException
from loguru import logger
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote
from dotenv import load_dotenv
import os
import re

load_dotenv()
logger.add("app.log", rotation="500 MB", retention="30 days", level="INFO")

app = FastAPI()

def send_to_slack_webhook(data: dict) -> None:
    """Sends data to the Slack webhook."""
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        logger.error("Slack webhook not configured.")
        raise HTTPException(status_code=500, detail="Slack webhook not configured.")

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(slack_webhook_url, json=data, headers=headers)
        response.raise_for_status()
        logger.info("Message sent to Slack successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending to Slack: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending to Slack: {e}")

@app.post("/webhook")
async def process_post(request: Request):
    """Endpoint to process GLPI notifications and send them to Slack."""
    try:
        post_data = await request.body()
        post_data_text = post_data.decode("utf-8")

        logger.info("Received POST request content.")

        soup = BeautifulSoup(post_data_text, "html.parser")
        description_text = soup.get_text(strip=True)

        ticket_id_match = re.search(r'Ticket #(\d+)', post_data_text)
        ticket_id = ticket_id_match.group(1) if ticket_id_match else None

        if ticket_id:
            ticket_info = f"Ticket ID: {ticket_id}\n"
        else:
            ticket_info = ""

        payload = {
            "text": f"New ticket received:\n{ticket_info}{description_text}",
        }

        send_to_slack_webhook(payload)


        return {"description_text": description_text}

    except Exception as e:
        logger.error(f"Error processing POST request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """API health check endpoint."""
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)