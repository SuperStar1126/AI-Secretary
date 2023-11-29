from config import OPENAI_API_KEY, PARAM, SUPABASE_CONNECTION, SUPABASE_URL, SUPABASE_KEY
from langchain.embeddings.openai import OpenAIEmbeddings
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import SeleniumURLLoader
from PyPDF2 import PdfReader
from fastapi import UploadFile, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta
from custom_types import ResourceStatus, ResourceType, Resource, ResourceSource, LLM
import vecs

class ResourceManager:

    # class for managing resources (urls, pdfs) in both Supabase and PostgreSQL
    # each instance of ResourceManager is bound to a bot_id

    def __init__(self, bot_id : int,
        model: LLM = "gpt-3.5-turbo",
        # model: LLM = "gpt-4",
    ):
        self._bot_id = bot_id
        self._index_name = "ai-chatbot-" + str(bot_id)
        self._environment = ''
        self._embed = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self._tokenizer = tiktoken.encoding_for_model(model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=40,
            length_function=self._tiktoken_len,
            separators=["\n\n", "\n", " ", ""]
        )
          
    def _tiktoken_len(self, text):
        # length function for calculating token length and chunking
        tokens = self._tokenizer.encode(
            text,
            disallowed_special=()
        )
        return len(tokens)
    
    def _from_url(self, url: str) -> tuple:
        # initialise supabase
        vx = vecs.Client(SUPABASE_CONNECTION)
        index = vx.get_or_create_collection(name=self._index_name, dimension=1536)

        # load urls as document
        loader = SeleniumURLLoader(urls=[url])
        page = loader.load()[0]
        
        # upsert embedded documents (vectors) into supabase database
        resource = self._add_resource((self._bot_id, "url", url, datetime.now(), "processing", True, 0))
        resource_id = resource[0]
        # split text/documents into chunks
        chunks = self.text_splitter.split_text(page.page_content)
        num_of_chunks = len(chunks)
        record_metadata = [{
            "chunk": j, "text": text, "source": page.metadata["source"]
        } for j, text in enumerate(chunks)]

        ids = [str(resource_id)+"-"+str(i) for i in range(num_of_chunks)]

        try:
            embeds = self._embed.embed_documents(chunks)
        except:
            raise HTTPException(500, "OpenAI error")
        try:
            index.upsert(records=zip(ids, embeds, record_metadata))
        except:
            result = self._update_status_chunks(resource_id, 'failed', 0)
        else:
            result = self._update_status_chunks(resource_id, 'trained', num_of_chunks)
        return result
    
    def _from_pdf(self, pdf: UploadFile) -> tuple:
        # initialise supabase
        vx = vecs.Client(SUPABASE_CONNECTION)
        index = vx.get_or_create_collection(name=self._index_name, dimension=1536)

        # load pdf
        reader = PdfReader(pdf.file)
        # extract text content
        text_content = ""
        for page in reader.pages:
            t = page.extract_text()
            text_content += t
        
        # upsert embedded documents (vectors) into supabase database
        resource = self._add_resource((self._bot_id, "pdf", pdf.filename, datetime.now(), "processing", True, 0))
        resource_id = resource[0]
        # split text/documents into chunks
        chunks = self.text_splitter.split_text(text_content)
        num_of_chunks = len(chunks)
        record_metadata = [{
            "chunk": j, "text": text, "source": pdf.filename
        } for j, text in enumerate(chunks)]
        ids = [str(resource_id)+"-"+str(i) for i in range(num_of_chunks)]
        try:
            embeds = self._embed.embed_documents(chunks)
        except:
            raise HTTPException(500, "OpenAI error")
        # vectors contain ids, embedded text chunks and metadata(source)
        try:
            index.upsert(records=zip(ids, embeds, record_metadata))
        except:
            result = self._update_status_chunks(resource_id, 'failed', 0)
        else:
            result = self._update_status_chunks(resource_id, 'trained', num_of_chunks)
        return result

    def _pg_initialise(self):
        # initialise psycopg2
        conn = psycopg2.connect(PARAM)
        cur = conn.cursor()
        return conn, cur

    def _pg_close(self, conn, cur):
        # close psycopg2
        conn.commit()
        cur.close()
        conn.close()

    def _add_resource(self, res: tuple) -> tuple:
        # add record to table, return the added record
        conn, cur = self._pg_initialise()
        cur.execute("""
            INSERT INTO Resources (bot_id, resource_type, resource_name, last_updated_time, status, visibility, chunks)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, res)
        cur.execute("SELECT MAX(resource_id) FROM resources WHERE bot_id = %s", (self._bot_id,))
        resource_id = cur.fetchone()[0]
        cur.execute("SELECT * FROM resources WHERE resource_id = %s", (resource_id,))
        result = cur.fetchone()
        self._pg_close(conn, cur)
        return result
    
    def _update_status_chunks(self, resource_id: int, status: str, chunks: int, conn = None, cur = None) -> tuple:
        # update status and chunks of record, return the updated recorded
        initialised = False
        if conn is None or cur is None:
            # establish psycopg2 connection and cursor if not available
            initialised = True
            conn, cur = self._pg_initialise()
        cur.execute("UPDATE resources SET status = %s, chunks = %s WHERE resource_id = %s", (status, chunks, resource_id))
        cur.execute("SELECT * FROM resources WHERE resource_id = %s", (resource_id,))
        result = cur.fetchone()
        if initialised:
            # close connection if initialised in this function
            self._pg_close(conn, cur)
        return result

    def _tuple_to_resource(self, values: tuple) -> Resource:
        # convert record tuples to Resource
        resource = Resource(
            resource_id=values[0],
            bot_id=values[1],
            resource_type=ResourceType[values[2]],
            resource_name=values[3],
            last_updated_time=values[4],
            status=ResourceStatus[values[5]],
            visibility=values[6],
            chunks=values[7]
        )
        return resource

    def create_text_resources(self, resources: list[ResourceSource]) -> list[Resource]:
        # create text resources (url, text)
        res = []
        for resource in resources:
            if resource.resource_type is ResourceType.url:
                result = self._from_url(resource.resource_name)
                res.append(self._tuple_to_resource(result))
        return res
    
    def create_file_resources(self, files: list[UploadFile]) -> list[Resource]:
        # create file resources (pdfs, docx, images)
        res = []
        for file in files:
            if file.content_type == "application/pdf":
                result = self._from_pdf(file)
                res.append(self._tuple_to_resource(result))
        return res

    def read_resources(self, page_size: int, page_number: int) -> list[Resource]:
        # list resources according to page_size and page_number
        conn, cur = self._pg_initialise()
        # define the range of resources to be retrieved
        end = page_size * page_number
        start = end - page_size + 1
        if page_number:
            cur.execute("SELECT COUNT(*) FROM resources WHERE bot_id = %s", (self._bot_id,))
            num = cur.fetchone()[0]
            cur.execute("""WITH rank_table AS (
                SELECT *, NTILE(%s) OVER (ORDER BY resource_id) AS rk
                FROM resources WHERE bot_id = %s)
                SELECT resource_id, bot_id, resource_type, resource_name, last_updated_time, status, visibility, chunks
                FROM rank_table WHERE rk between %s and %s""", (num, self._bot_id, start, end))
        else:
            # return all resources if page_number == 0
            cur.execute("SELECT * FROM resources WHERE bot_id = %s ORDER BY resource_id", (self._bot_id,))
        out = cur.fetchall()
        result = list(map(self._tuple_to_resource, out))
        self._pg_close(conn, cur)
        return result
    
    def search_resources(self, key_word: str) -> list[Resource]:
        # search all resources that match the given key word
        conn, cur = self._pg_initialise()
        cur.execute("SELECT * FROM resources WHERE bot_id = %s AND resource_name LIKE %s",
            (self._bot_id, "%%"+key_word+"%%"))
        out = cur.fetchall()
        result = list(map(self._tuple_to_resource, out))
        self._pg_close(conn, cur)
        return result

    def delete_resource(self, resource_id: int) -> Resource:
        # delete resource with given resource_id
        vx = vecs.Client(SUPABASE_CONNECTION)
        index = vx.get_or_create_collection(name=self._index_name, dimension=1536)
        conn, cur = self._pg_initialise()
        cur.execute("SELECT * FROM resources WHERE resource_id = %s AND bot_id = %s", (resource_id, self._bot_id))
        out = cur.fetchone()
        if out is not None:
            try:
                ids = []
                for i in range(out[7]):
                    ids.append(str(resource_id) + '-' + str(i))
                index.delete(ids=ids)# delete resource with resource_name (source)
            except:
                cur.execute("UPDATE resources SET status = 'failed' WHERE resource_id = %s", (resource_id,))
                self._pg_close(conn, cur)
                raise HTTPException(500, "Supabase vectors deletion failed")
            cur.execute("DELETE FROM resources WHERE resource_id = %s AND bot_id = %s", (resource_id, self._bot_id))
        else:
            raise HTTPException(404, detail="No matching record in the database")
        result = self._tuple_to_resource(out)
        self._pg_close(conn, cur)
        return result

    def query_status(self, resource_ids: list[int]) -> dict[int, ResourceStatus]:
        # query status of given resources
        conn, cur = self._pg_initialise()
        statuses = {}
        for id in resource_ids:
            cur.execute("SELECT status FROM resources WHERE resource_id = %s AND bot_id = %s", (id, self._bot_id))
            out = cur.fetchone()
            if out is not None:
                status = out[0]
                statuses.update({id: status})
            else:
                raise HTTPException(404, detail="""No matching record in the database. Bot Id: {bot_id}, Resource Id: {resource_id}""".format(bot_id=self._bot_id, resource_id=id))
        self._pg_close(conn, cur)
        return statuses

    def toggle_visibility(self, resource_id: int) -> bool:
        # toggle visibility of a given resource
        conn, cur = self._pg_initialise()
        cur.execute("UPDATE resources SET visibility = NOT visibility WHERE resource_id = %s AND bot_id = %s", (resource_id, self._bot_id))
        cur.execute("SELECT visibility FROM resources WHERE resource_id = %s AND bot_id = %s", (resource_id, self._bot_id))
        out = cur.fetchone()
        if out is not None: 
            result = out[0]
        else:
            raise HTTPException(404, detail="No matching record in the database")
        self._pg_close(conn, cur)
        return result
    
    def resync(self, resource_id: int) -> Resource:
        vx = vecs.Client(SUPABASE_CONNECTION)
        index = vx.get_or_create_collection(name=self._index_name, dimension=1536)
        conn, cur = self._pg_initialise()

        # retrieve url name
        cur.execute("SELECT resource_name, chunks FROM resources WHERE resource_id = %s AND resource_type = 'url' AND bot_id = %s",
            (resource_id, self._bot_id))
        out = cur.fetchone()
        if out is not None:
            url, old_num_of_chunks = out
            cur.execute("UPDATE resources SET status = 'processing' WHERE resource_id = %s", (resource_id,))
            conn.commit()
        else:
            raise HTTPException(404, detail="No matching record in the database")
        
        # load url as document
        loader = SeleniumURLLoader(urls=[url])
        page = loader.load()[0]
        chunks = self.text_splitter.split_text(page.page_content)
        num_of_chunks = len(chunks)
        record_metadata = [{
            "chunk": j, "text": text, "source": page.metadata["source"]
        } for j, text in enumerate(chunks)]
        ids = [str(resource_id)+"-"+str(i) for i in range(num_of_chunks)]
        try:
            embeds = self._embed.embed_documents(chunks)
        except:
            raise HTTPException(500, "OpenAI error")
        try:
            index.upsert(vectors=zip(ids, embeds, record_metadata))
            if num_of_chunks < old_num_of_chunks:
                index.delete([str(resource_id)+"-"+str(i) for i in range(num_of_chunks, old_num_of_chunks)])
        except:
            cur.execute("UPDATE resources SET last_updated_time = %s WHERE resource_id = %s AND bot_id = %s AND resource_type = 'url'",
            (datetime.now(timezone(timedelta(hours=8))), resource_id, self._bot_id))
            result = self._update_status_chunks(resource_id, 'failed', 0, conn, cur)
        else:
            cur.execute("UPDATE resources SET last_updated_time = %s WHERE resource_id = %s AND bot_id = %s AND resource_type = 'url'",
            (datetime.now(timezone(timedelta(hours=8))), resource_id, self._bot_id))
            result = self._update_status_chunks(resource_id, 'trained', num_of_chunks, conn, cur)
        self._pg_close(conn, cur)
        return self._tuple_to_resource(result)

if __name__ == "__main__":
    manager = ResourceManager(1)
    '''
    manager.from_url(["https://en.wikipedia.org/wiki/2014_FIFA_World_Cup",
        "https://en.wikipedia.org/wiki/2018_FIFA_World_Cup",
        "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup"])
    '''
    print(manager.resync(25))