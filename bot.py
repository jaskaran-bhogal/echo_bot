# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import sys
import traceback
from datetime import datetime
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import TurnContext
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount

from opentelemetry import trace
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from config import ASSET_PATH, get_logger, DefaultConfig
from get_product_documents import get_product_documents
from azure.ai.inference.prompts import PromptTemplate
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# Initialize log file for messages (used later in the messages endpoint)
LOG_FILE = os.environ.get("LOG_FILE", "seccess_log.jsonl")

# Initialize config
CONFIG = DefaultConfig()

# Logging and tracing
logger = get_logger(__name__)

# ---------------------------
# Setup file logging for application activity
import logging
activity_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_activity.log")
file_handler = logging.FileHandler(activity_log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
logger.info("Application logging initialized. Logs will be written to %s", activity_log_file)
# ---------------------------

tracer = trace.get_tracer(__name__)

# Create Azure AI project client
project = AIProjectClient.from_connection_string(
    conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
    credential=DefaultAzureCredential()
)

# Chat client from the AI project
chat = project.inference.get_chat_completions_client()

# Prompt-based product chat handler
def chat_with_products(messages: list, context: dict = None) -> dict:
    documents = get_product_documents(messages, context)
    grounded_chat_prompt = PromptTemplate.from_prompty(os.path.join(ASSET_PATH, "grounded_chat.prompty"))
    system_message = grounded_chat_prompt.create_messages(documents=documents, context=context)

    response = chat.complete(
        model=os.environ["CHAT_MODEL"],
        messages=system_message + messages,
        **grounded_chat_prompt.parameters,
    )

    logger.info("Response: %s", response.choices[0].message)
    return response.choices[0].message





class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        logger.info("Received message activity: %s", turn_context.activity.text)
                # 👉 Send typing indicator
        typing_activity = Activity(type=ActivityTypes.typing)
        await turn_context.send_activity(typing_activity)
        messages = [{"role": "user", "content": turn_context.activity.text}]
        await turn_context.send_activity(chat_with_products(messages, {}).content)

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")


##added some context
