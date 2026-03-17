from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from loguru import logger
from bs4 import BeautifulSoup
import tomllib
import httpx
import json

logger.add("app.log", rotation="500 MB", retention="30 days", level="INFO")

app = FastAPI()

with open("config.toml", "rb") as f:
    config = tomllib.load(f)


async def send_to_slack_webhook(data: dict, slack_url: str) -> None:
    """Sends data to the Slack webhook (async)."""
    if not slack_url:
        logger.error("Slack webhook not configured.")
        raise HTTPException(
            status_code=500, detail="Slack webhook not configured.")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                slack_url, json=data, headers={
                    "Content-Type": "application/json"}
            )
            resp.raise_for_status()
        logger.info("Message sent to Slack successfully.")
    except httpx.HTTPError as e:
        logger.error(f"Error sending to Slack: {e}")


async def process_post(body: bytes, slack_url: str) -> None:
    """Process GLPI notifications and send them to the per-route Slack URL."""
    priority_lookup = [
        "",  # Indexed at 1
        "🔵 Very Low",
        "🟢 Low",
        "🟡 Medium",
        "🟠 High",
        "🔴 Very High",
        "⚠️ Major",
    ]

    status_lookup = {
        "Pending": "🟡 Pending",
        "New": "🟢 New",
        "Approval": "❓ Approval",
        "Closed": "⚫ Closed",
        "Solved": "✅ Solved",
        "Processing (assigned)": "⭐ Assigned",
        "Processing (planned)": "📅 Scheduled",
    }

    try:
        post_data_text = body.decode("utf-8", errors="replace")
        data = json.loads(post_data_text)
        item = data.get("item", {})

        # Initialize payload
        payload = {"blocks": []}

        # Context header
        priority = item.get("priority", 1)
        priority_text = priority_lookup[priority] if 1 <= priority <= 6 else "❓ Unknown"

        status_text = status_lookup.get(
            item.get("status", {}).get("name", "N/A"), "❌ Unknown"
        )

        payload["blocks"].append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*Status:* {status_text}"},
                    {"type": "mrkdwn", "text": f"*Priority:* {priority_text}"},
                ],
            }
        )

        # Title (ticket updated/etc)
        item_id = item.get("id", "0")
        ticket_url_text = f"<https://support.avionics411.com/front/ticket.form.php?id={item_id}|#{item_id}>"

        event_type = data.get("event", "new")
        if event_type == "update":
            text = "Ticket updated"
        else:
            text = "New ticket"

        payload["blocks"].append(
            {"type": "header", "text": {"type": "plain_text", "text": text}}
        )
        payload["blocks"].append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{ticket_url_text}*"},
            }
        )

        # Title
        item_name = item.get("name") or "_No title provided._"
        payload["blocks"].append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Title:* {item_name}",
                },
            }
        )

        # Description if it's a new ticket
        if event_type != "update":
            item_content = item.get("content", "")
            text = BeautifulSoup(item_content, "html.parser").get_text().strip() if item_content else ""
            if not text:
                text = "_No description provided._"
            text = text if len(text) <= 700 else text[:700] + "..."
            payload["blocks"].append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{text}",
                    },
                }
            )
        # Otherwise add list of changes.
        else:
            payload["blocks"].append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Changes:*"
                    }
                }
            )

            changes = data.get("changes", [])
            if len(changes) == 0:
                logger.info("Update event received with no changes, skipping.")
                return

            change_bullet = "=>"
            for change in changes:
                previous = change.get("previous")
                new = change.get("new")

                if isinstance(new, list):
                    old_ids = [i['value'] for i in previous]
                    new_ids = [i['value'] for i in new]
                    added = [i['label'] for i in new if i['value'] not in old_ids]
                    removed = [i['label'] for i in previous if i['value'] not in new_ids]

                    spacer = "\n\t\t"
                    add_symbol = "*+*"
                    remove_symbol = "*-*"
                    add_pre = f"{spacer}{add_symbol} "
                    rem_pre = f"{spacer}{remove_symbol} "

                    str_rep = f"{add_pre if added else ''}{add_pre.join(added)}{rem_pre if removed else ''}{rem_pre.join(removed)}"

                    payload["blocks"].append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{change_bullet} *{change['field_label']}:* {str_rep}"
                            }
                        }
                    )
                else:
                    payload["blocks"].append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{change_bullet} *{change['field_label']}:* {previous['label']} *->* {new['label']}"
                            }
                        }
                    )

        # Divider
        payload["blocks"].append({"type": "divider"})

        await send_to_slack_webhook(payload, slack_url)

    except Exception as e:
        logger.exception(f"Error processing POST request: {e}")


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
            logger.error(
                f"Invalid endpoint for webhook.{name}: {endpoint!r} (must start with '/')"
            )
            continue
        if not slack_url:
            logger.error(f"Missing url for webhook.{name}")
            continue

        async def handler(request: Request, background_tasks: BackgroundTasks, _slack_url=slack_url):
            body = await request.body()
            background_tasks.add_task(process_post, body, _slack_url)
            return {"status": "accepted"}

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
