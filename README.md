# GLPI to Slack Integration

This project enables sending notifications of new GLPI tickets to a Slack channel using a webhook. It's built with FastAPI and Docker for easy and scalable deployment. This integration relies on the **Webhook plugin for GLPI** developed by Eric Feron ([https://github.com/ericferon/glpi-webhook/wiki/Webhook](https://github.com/ericferon/glpi-webhook/wiki/Webhook)).

## Prerequisites

1.  **GLPI**: Ensure your GLPI instance (version 9.5 or later is recommended for the Webhook plugin) is set up and running correctly.
2.  **Slack**: Create an Incoming Webhook for your desired Slack channel.
3.  **Docker**: This project uses Docker containers for simplified deployment.
4.  **Make**: This project includes a `Makefile` to simplify common development and deployment tasks.
5.  **GLPI Webhook Plugin**: Please ensure the **Webhook plugin** by Eric Feron is installed and activated in your GLPI instance (available in the GLPI Marketplace under **Setup > Plugins**). Refer to the plugin's documentation for detailed information on its features and configuration.

## Deployment Steps

### 1. Set Up the Slack Webhook

1.  Go to your [Slack workspace](https://slack.com/).
2.  Create an **Incoming Webhook**:
    * Visit the [Slack API site for Incoming Webhooks](https://api.slack.com/messaging/webhooks).
    * Click **Create New App** and choose **From Scratch**.
    * Select **Incoming Webhooks** and toggle it **On**.
    * Click **Add New Webhook to Workspace**.
    * Choose the Slack channel where you want to receive notifications.
    * Click **Authorize**.
    * **Copy the generated Webhook URL**.

### 2. Configure GLPI to Send Notifications via the Webhook Plugin

This step involves configuring the GLPI Webhook plugin to send notifications to your application's `/webhook` endpoint when new tickets are created. Refer to the **GLPI Webhook plugin documentation** ([https://github.com/ericferon/glpi-webhook/wiki/Webhook](https://github.com/ericferon/glpi-webhook/wiki/Webhook)) for comprehensive instructions.

1.  **Install the Webhook Plugin in GLPI**:
    * In your GLPI instance, navigate to **Setup > Plugins > Webhook**.
    * If not installed, install and activate the plugin.

2.  **Add a New Webhook**:
    * Click on the **"+"** button to add a new webhook.

3.  **Configure the Webhook**:
    * **Name**: Give your webhook a descriptive name (e.g., "Slack Notifications").
    * **Status**: Set to **Active**.
    * **URL**: Enter the URL where your application will be running, followed by the `/webhook` endpoint. For local development, this might be `http://your_local_ip:8000/webhook`. If deployed on a server, use your server's IP address or domain name.
    * **HTTP Method**: Select **POST**.
    * **Content Type**: Choose **application/json**.
    * **Trigger**: Select **Ticket creation**. This will trigger the webhook whenever a new ticket is created in GLPI.
    * **Notification Model and Notification Template**:
        * Refer to the `workflow.png` file (located in this repository) for a visual guide on how to configure the **Notification** and the **Notification Template** within the GLPI Webhook plugin.
        * In the GLPI Webhook plugin configuration, you will define a **Notification** that specifies when the webhook should be triggered (e.g., on new ticket creation).
        * The **Notification Template** defines the content that will be sent in the POST request to your application. When configuring the Notification Template, ensure the content includes the ticket information you want to send to Slack. The current application expects the ticket details within the POST request body. Consult the **GLPI Webhook plugin documentation** for details on available tags (e.g., `##ticket.id##`, `##ticket.description##`) and how to structure your notification content within the template to be sent as JSON.

4.  **Test the Connection (Optional but Recommended)**:
    * The GLPI Webhook plugin might offer a test functionality to send a sample request to your configured URL. Use this to verify that GLPI can reach your application.

### 3. Configure the Environment

Create a `.env` file in the root of this project with the following environment variables:

```ini
SLACK_WEBHOOK_URL=your_slack_webhook_url
GLPI_BASE_URL=http://your_glpi_url