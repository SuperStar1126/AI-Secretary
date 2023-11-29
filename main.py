from fastapi import FastAPI, Body, Path, Query, File, UploadFile
from pydantic import BaseModel, HttpUrl
from datetime import date
from custom_types import Resource, ResourceStatus, ResourceType, ResourceSource, Bot, ChannelType, Conversation, ConversationHistory
from typing import Annotated, Union
from url_fetcher import UrlFetcher
from resource_manager import ResourceManager
from bot_manager import BotManager
from conversation_manager import ConversationManager
from chatbot import Chatbot
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    ssl_keyfile="/home/ubuntu/ssl-cert/private.key",
    ssl_certfile="/home/ubuntu/ssl-cert/certificate.crt"
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/resource/fetch_url", responses={200: {
    "content": {
        "application/json": {
            "example": ["https://www.aia.com.hk", "https://www.aia.com.hk", "https://www.aia.com.hk"]
        }
    }
}})
async def fetch_urls(url: Annotated[HttpUrl, Query(example="https://www.aia.com.hk", description="Pass a single URL or XML sitemap.")]) -> list[HttpUrl]:
    fetcher = UrlFetcher()
    return fetcher(url)

@app.post("/resource/create/{bot_id}/text", responses={200: {
    "content": {
        "application/json": {
            "example": [Resource(
                resource_id = 123,
                bot_id = 456,
                resource_type = ResourceType.url,
                resource_name = "https://www.aia.com.hk",
                last_updated_time = "2023-07-05T08:55:02.155Z",
                status = ResourceStatus.processing,
                visibility = True,
                chunks = 123
            )]
        }
    }
}})
async def create_text_resources(bot_id: Annotated[int, Path()], res: Annotated[list[ResourceSource], Body(
    example=[ResourceSource(resource_type=ResourceType.url, resource_name="https://www.aia.com.hk")]
)]) -> list[Resource]:
    manager = ResourceManager(bot_id)
    return manager.create_text_resources(res)

@app.post("/resource/create/{bot_id}/file", responses={200: {
    "content": {
        "application/json": {
            "example": [Resource(
                resource_id = 123,
                bot_id = 456,
                resource_type = ResourceType.pdf,
                resource_name = "pdf_name.pdf",
                last_updated_time = "2023-07-05T08:55:02.155Z",
                status = ResourceStatus.processing,
                visibility = True,
                chunks = 123
            )]
        }
    }
}})
async def create_file_resources(bot_id: Annotated[int, Path()], files: Annotated[list[UploadFile], File(
    description="List of files e.g. .pdf to be uploaded and trained"
)]) -> list[Resource]:
    manager = ResourceManager(bot_id)
    return manager.create_file_resources(files)

@app.get("/resource/read/{bot_id}")
async def read_resources(bot_id: Annotated[int, Path(gt=0)], page_size: Annotated[int, Query(
    gt=0, description="Size of record batch (page) received"
)] = ..., page_number: Annotated[int, Query(
    gt=-1, description="Page number, set to 0 to return all pages"
)] = 1) -> list[Resource]:
    manager = ResourceManager(bot_id)
    return manager.read_resources(page_size, page_number)

@app.get("/resource/search/{bot_id}") # need to watch for SQL injection
async def search_resources(bot_id: Annotated[int, Path(gt=0)], key_word: Annotated[str, Query(
    description="Key word input by user for searching"
)]) -> list[Resource]:
    manager = ResourceManager(bot_id)
    return manager.search_resources(key_word)

@app.delete("/resource/delete/{bot_id}/{resource_id}")
async def delete_resource(bot_id: Annotated[int, Path(gt=0)], resource_id: Annotated[int, Path(gt=0)]) -> Resource:
    manager = ResourceManager(bot_id)
    return manager.delete_resource(resource_id)

@app.get("/resource/status/{bot_id}")
async def query_status(bot_id: Annotated[int, Path(gt=0)], resource_ids: Annotated[list[int], Query(
    gt=0, description="List of resources to be queried"
)]) -> dict[int, ResourceStatus]:
    manager = ResourceManager(bot_id)
    return manager.query_status(resource_ids)

@app.post("/resource/visibility/{bot_id}/{resource_id}", responses={200: {
    "description": "Successful Response; Responded boolean value represents to value after toggling"
}})
async def toggle_visibility(bot_id: Annotated[int, Path(gt=0)], resource_id: Annotated[int, Path(gt=0)]) -> bool:
    manager = ResourceManager(bot_id)
    return manager.toggle_visibility(resource_id)

@app.put("/resource/resync/{bot_id}/{resource_id}")
async def resync(bot_id: Annotated[int, Path(gt=0)], resource_id: Annotated[int, Path(
    gt=0, description="This API is only intended for URL resources"
)]) -> Resource:
    manager = ResourceManager(bot_id)
    return manager.resync(resource_id)

@app.post("/bot/create")
async def create_bot(bot_or_bot_id: Annotated[int | Bot, Body(example=Bot(
    theme_id = 3,
    creation_date = date(2023, 7, 3),
    bot_name = "chatbot",
    bot_desc = "a smart ai assistant",
    is_root = False,
    supabase_index = "ai-chatbot-1234",
    environment = "us-west4-gcp-free"),
    description="Include a bot_id (int) or a bot record (Bot) in the request body"
)]) -> Bot:
    manager = BotManager(1)
    return manager.create_bot(bot_or_bot_id)

@app.put("/bot/modify/{bot_id}")
async def modify_bot(bot_id: Annotated[int, Path(gt=0)], bot: Bot) -> Bot:
    manager = BotManager(1)
    return manager.modify_bot(bot_id, bot)

@app.get("/bot/read")
async def read_bot(page_size: Annotated[int, Query(
    gt=0, description="Size of record batch (page) received"
)] = ..., page_number: Annotated[int, Query(
    gt=-1, description="Page number, set to 0 to return all pages"
)] = 1) -> list[Bot]:
    manager = BotManager(1)
    return manager.read_bot(page_size, page_number)

@app.delete("/bot/delete/{bot_id}")
async def delete_bot(bot_id: Annotated[int, Path(gt=0)]) -> Bot:
    manager = BotManager(1)
    return manager.delete_bot(bot_id)

@app.post("/bot/chat/{bot_id}")
async def chat(bot_id: Annotated[int, Path(gt=0)], q: Annotated[str, Body(example="What does your company do?")],
    history: Annotated[list[Conversation], Body(example=[Conversation(human="human", ai="ai", source="source")])]):
    return Chatbot.chat(bot_id, q, history)

@app.post("/bot/conversation_history/{bot_id}")
async def view_history(bot_id: Annotated[int, Path(gt=0)], channel_type: Annotated[ChannelType | None, Query(
    description="Channels such as WhatsApp and WeChat, exclude this parameter to view all channels"
)] = None, conversation_id: Annotated[int | None, Query(
    gt=0, description="Include single ID to view specific conversation, exclude to view all"
)] = None) -> list[ConversationHistory]:
    manager = ConversationManager(bot_id)
    return manager.view_history(channel_type, conversation_id)
