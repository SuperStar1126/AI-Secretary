from config import OPENAI_API_KEY
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback
from custom_types import Conversation
import openai


TEMPLATE = """
You are an AI assistant that can have conservations and answers ONLY according to provided content.
Given the following extracted parts of a long document, conversation history and a question, create a concise answer with references ("SOURCES").
If you don't know, just say you don't know the answer and DON'T make an answer up.
ALWAYS return a "SOURCES" part in your answer and they MUST be provided documents.
The "SOURCES" part MUST ONLY contain URLs or file names OF THE PROVIDED DOCUMENTS.
NEVER make a conversation up and NEVER make an answer up.
------
{summaries}
------
{history}
------
{question}
Answer:
"""

PROMPT = PromptTemplate(
    input_variables=["history", "summaries", "question"],
    template=TEMPLATE,
)
class Chatbot:
    def __init__(self, 
        bot_id : int,
        embed = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        llm = ChatOpenAI(
            model_name='gpt-3.5-turbo',
            temperature=0.0,
            openai_api_key=OPENAI_API_KEY
        ),
        memory = ConversationBufferMemory(
            memory_key="history",
            input_key="question"
        ),
        prompt = PROMPT
        ):
        self._bot_id = bot_id
        self._index_name = "ai-chatbot-" + str(bot_id)
        self._environment = ''
        self._embed = embed
        self._llm = llm
        self._prompt = prompt
        self._memory = memory
        
    def chat(self,
             q: str,
             history: list[Conversation]):
        # Initial system message
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ]
        for conv in history:
            messages.append({"role": "user", "content": conv.human})
            messages.append({"role": "assistant", "content": conv.ai})
        messages.append({"role": "user", "content": q})
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response['choices'][0]['message']['content']

if __name__ == "__main__":
    bot = Chatbot()
    bot()