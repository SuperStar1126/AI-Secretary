# AI Chatbot 

Repository for the AI Chatbot Backend

## Table of Contents

- [Set-up](#setup)
- [Deployment](#deployment)
- [Known Issues](#known-issues)

### <a name="setup"></a>Set-up

#### Prerequisites

- Python **3.10 or above**
- PIP
- Git
- Supabase database with API key
- PostgreSQL database
- OpenAI API key

To set up the backend environmenet, first clone the repository with 

```
git clone https://github.com/dgxu-leadstec/ai-chatbot-backend.git
```

Then, install the PIP requirements with

```
pip3 install -r requirements.txt
```

Finally, add a `config.py` file with the following constants.

```
BOT_LIMIT: Limit of the number of bots a user can have (int)
PARAM: Parameters used by psycopg2 to connect to a PostgreSQL server with the following format (str)

"host=server.com dbname=postgres user=root password=root port=5432"

Supabase_ENV: Supabase environment used to connect to Supabase indexes (str)
OPENAI_API_KEY: API key for OpenAI (str)
Supabase_API_KEY: API key for Supabase (str)
```

#### PostgreSQL Database Set-up

The backend currently follow strictly to the schema with these following tables.
There is currently no backend code used to create new tables.

**TABLE resources**

```
resource_id [PK]: bigserial NOT NULL
bot_id [FK]: bigint NOT NULL
resource_type: media = ENUM ('url', 'pdf') NOT NULL
resource_name: varchar(255) NOT NULL
last_updated_time: timestamptz NOT NULL (timestamp with time zone)
status: status = ENUM ('processing', 'trained', 'failed') NOT NULL
visibility: bool NOT NULL
chunks: int NOT NULL
```

**TABLE bots**

```
bot_id [PK]: bigserial NOT NULL
acc_id [FK]: bigint NOT NULL
theme_id [FK]: bigint NOT NULL
creation_date: date NOT NULL
bot_name: varchar(100) NOT NULL
bot_desc: varchar(1000)
is_root: boolean NOT NULL
supabase_index: varchar(50) NOT NULL
environment: varchar(50) NOT NULL
```

**TABLE conversation_history**

```
conversation_id [PK]: bigserial NOT NULL
bot_id [FK]: bigint NOT NULL
acc_id [FK]: bigint NOT NULL
conversation: json[] NOT NULL
channel_type: channel_type = ENUM ('wechat', 'web_chat', 'whatsapp') NOT NULL
channel_id: bigint NOT NULL
last_updated_time: timestamptz NOT NULL (timestamp with time zone)
```

More details and info on the fields can be found in `custom_types.py` and also the [ER diagram](https://drive.google.com/file/d/1wDylGVhrd08hrW0oNpw8ACrY14G5JNyg/view?pli=1).

#### Supabase Specifications

Currently, Supabase is the vector database of choice to store embedded documents. Each bot is assigned to one Supabase index with all its resources embedded in the same index.

To ensure each index has a unique the name of each index is set to be `ai-chatbot-[bot_id]`.

During embedding, each text/document is split into chunks, whose number is recorded in the database. Each chunk corresponds to one embedded vector. Every ID of the vectors follow the format `[resource_id]-[chunk_number]`. For example, a URL with the resource_id 25 and 83 chunks would be embedded into vectors

```
25-0, 25-1, ..., 25-81, 25-82 (83 chunks/vectors)
```

### <a name="deployment"></a>Deployment

To run the backend server, run

```
uvicorn main:app [OPTIONS]
OR
python3 -m uvicorn main:app [OPTIONS]
```

Useful OPTIONS include

```
--reload: Reload the server whenever a change occur in the code
--host TEXT: Bind socket to this host [default: localhost]
--port INTEGER: Bind socket to this port [default: 8000]
```

The automatically genereated Swagger UI documentation can be viewed at

```
[host]:[port]/docs

Default:
localhost:8000/docs
```

### <a name="known-issues"></a>Known Issues

1. There was no OpenAI API key to perform vector embeddings, so most Supabase sections are tested without it.
2. Sometimes, the response body might be too big to be sent.
3. Chat API is not implemeted and the search_resources API only searches in the resource's name, not its contents.
4. The backend system is currently fairly irresponsive to changes of fields in the database.
5. Errors thrown by libraries are mostly uncaught. (e.g. RateLimitError for OpenAI, Supabase errors)
6. There is no SQL injection prevention for string parameters in the APIs.
7. Way more tables are required in the PostgreSQL database.
8. Hard to fully test Supabase aspects as the free version only allow one index.
9. Timezones are currently hard-coded.
10. Documentation on custom responses e.g. 404 errors is lacking.