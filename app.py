import sys
import traceback
import logging
from datetime import datetime
import os
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bot import MyBot
from config import DefaultConfig

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

CONFIG = DefaultConfig()

# Create adapter.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD, channel_auth_tenant=CONFIG.TENANT_ID)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    logging.error(f"[on_turn_error] Unhandled error: {error}", exc_info=True)

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity("To continue to run this bot, please fix the bot source code.")

    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)

ADAPTER.on_turn_error = on_error

BOT = MyBot()

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    try:
        if "application/json" in req.headers.get("Content-Type", ""):
            body = await req.json()
        else:
            logging.warning("Unsupported media type received.")
            return Response(status=415)

        logging.info("Received activity: %s", body)

        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")

        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)

        if response:
            logging.info("Responded with status %s and body: %s", response.status, response.body)
            return json_response(data=response.body, status=response.status)

        logging.info("Message processed with no response returned.")
        return Response(status=201)

    except Exception as e:
        logging.error("Exception occurred while processing message:", exc_info=True)
        return Response(status=500, text="Internal Server Error")

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8000))
        logging.info(f"Starting app on port {port}...")
        web.run_app(APP, host="0.0.0.0", port=port)
    except Exception as error:
        logging.critical("Failed to start app:", exc_info=True)
        raise
