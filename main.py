from fastapi import FastAPI, Request, HTTPException
from loguru import logger
from bs4 import BeautifulSoup
import re
import tomllib
import httpx

logger.add("app.log", rotation="500 MB", retention="30 days", level="INFO")

app = FastAPI()

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

async def send_to_slack_webhook(data: dict, slack_url: str) -> None:
    """Sends data to the Slack webhook (async)."""
    if not slack_url:
        logger.error("Slack webhook not configured.")
        raise HTTPException(status_code=500, detail="Slack webhook not configured.")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(slack_url, json=data, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
        logger.info("Message sent to Slack successfully.")
    except httpx.HTTPError as e:
        logger.error(f"Error sending to Slack: {e}")
        raise HTTPException(status_code=500, detail="Error sending to Slack")

async def process_post(request: Request, slack_url: str):
    """Process GLPI notifications and send them to the per-route Slack URL."""
    try:
        post_data = await request.body()
        post_data_text = post_data.decode("utf-8", errors="replace")

        logger.info("Received POST request content.")

        soup = BeautifulSoup(post_data_text, "html.parser")
        description_text = soup.get_text(strip=True)

        ticket_id_match = re.search(r"Ticket #(\d+)", post_data_text)
        ticket_id = ticket_id_match.group(1) if ticket_id_match else None

        ticket_info = f"Ticket ID: {ticket_id}\n" if ticket_id else ""

        payload = description_text

        await send_to_slack_webhook(payload, slack_url)

        return {"description_text": description_text}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing POST request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def register_webhook_routes(app: FastAPI, cfg: dict) -> None:
    """
    Reads:
      [webhook.one]
      url = "..."
      endpoint = "/one"
    and creates a POST endpoint at /one that posts to the given Slack URL.
    """
    webhooks = cfg.get("webhook", {})
    if not isinstance(webhooks, dict) or not webhooks:
        logger.warning("No [webhook.*] entries found in config.toml")
        return

    for name, entry in webhooks.items():
        endpoint = entry.get("endpoint")
        slack_url = entry.get("url")

        if not endpoint or not endpoint.startswith("/"):
            logger.error(f"Invalid endpoint for webhook.{name}: {endpoint!r} (must start with '/')")
            continue
        if not slack_url:
            logger.error(f"Missing url for webhook.{name}")
            continue

        # Bind per-route slack_url using default arg to avoid closure issues
        async def handler(request: Request, _slack_url=slack_url):
            return await process_post(request, _slack_url)

        route_name = f"webhook_{name}"
        app.add_api_route(endpoint, handler, methods=["POST"], name=route_name)
        logger.info(f"Registered POST {endpoint} -> {route_name}")

register_webhook_routes(app, config)

@app.get("/health")
async def health_check():
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)