from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, date

# Currently all acc_id fields and variables in the database and backend code is of integer type
# It is very likely to change to other types once an authentication system is established

class ResourceType(Enum):
    url = "url"
    pdf = "pdf"

class ResourceStatus(Enum):
    processing = "processing"
    trained = "trained"
    failed = "failed"

class LLM(Enum):
    gpt_3_5_turbo = "gpt-3.5-turbo"
    gpt_4 = "gpt-4"

class ResourceSource(BaseModel):
    # used to send text resources (txt, url) from the frontend
    resource_type: ResourceType
    resource_name: str
    content: str | None = Field(default=None, description="Unnecessary for urls, where only resource_name (the url name) is sufficient")

class Resource(BaseModel):
    resource_id : int | None = Field(default=None, gt=0,
        description="Optional when creating new resource, where id is unavailable")
    bot_id : int = Field(gt=0)
    resource_type : ResourceType
    resource_name : str
    last_updated_time : datetime
    status: ResourceStatus
    visibility: bool = Field(description="whether the chatbot would include the source for this resource or not")
    chunks : int = Field(ge=0, description="number of chunks the resource is split into")

class Bot(BaseModel):
    bot_id : int | None = Field(default=None, ge=0,
        description="Optional when creating new bot, where id is unavailable")
    # acc_id omitted for authentication purposes
    theme_id : int = Field(ge=0)
    creation_date : date
    bot_name : str
    bot_desc : str | None = None
    is_root : bool = Field(description="whether the bot is a root bot")
    supabase_index : str | None = Field(default=None, description="""All supabase_index follows the format of ai-chatbot-[bot_id] 
        currently, also optional for new resources where id is unknown""")
    environment : str = Field(description="Currently assumes all resources are in the same supabase environment, set by the SUPABASE_ENV constant")

class ChannelType(Enum):
    web_chat = "web_chat"
    wechat = "wechat"
    whatsapp = "whatsapp"

class Conversation(BaseModel):
    human: str
    ai: str
    source: str

class ConversationHistory(BaseModel):
    conversation_id : int | None = Field(default=None, gt=0,
        description="Optional for new conversations, where id is unavailable")
    bot_id : int = Field(gt=0)
    # acc_id omitted for authentication purposes
    conversation : list[Conversation]
    channel_type : ChannelType
    channel_id : int = Field(gt=0, description="= web_chat_id or wechat_id or whatsapp_id")
    last_updated_time : datetime