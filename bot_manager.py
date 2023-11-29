from custom_types import Bot, ChannelType
import psycopg2
from config import PARAM, BOT_LIMIT, SUPABASE_CONNECTION
from datetime import date
from fastapi import HTTPException
import vecs

class BotManager():

    # class for managing bots details and information in the PostgreSQL database
    # each instance of BotManager is bound to an acc_id (subject to change)

    def __init__(self, acc_id: int):
        self._acc_id = acc_id

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
    
    def _insert_retrieve(self, conn, cur, new: tuple) -> tuple:
        # insert into TABLE bots and retrieve the same record
        cur.execute("INSERT INTO bots VALUES (DEFAULT, " + "%s, "*(len(new)-1) + "%s)", new)
        cur.execute("SELECT MAX(bot_id) FROM bots WHERE acc_id = %s", (self._acc_id,))
        bot_id = cur.fetchone()[0]
        cur.execute("UPDATE bots SET supabase_index = %s WHERE bot_id = %s", ("ai-chatbot-"+str(bot_id), bot_id))
        cur.execute("SELECT * FROM bots WHERE bot_id = %s", (bot_id,))
        result = cur.fetchone()
        self._pg_close(conn, cur)
        return result

    def _tuple_to_bot(self, values: tuple) -> Bot:
        # convert value tuples into Bot object
        bot = Bot(bot_id=values[0],
            theme_id=values[2],
            creation_date=values[3],
            bot_name=values[4],
            bot_desc=values[5],
            is_root=values[6],
            supabase_index=values[7],
            environment=values[8]
            )
        return bot

    def _create_supabase_index(self, index_name: str):
        vx = vecs.Client(SUPABASE_CONNECTION)
        vx.create_collection(name=index_name, dimension=1536)

    def _delete_supabase_index(self, index_name: str):
        vx = vecs.Client(SUPABASE_CONNECTION)
        vx.delete_collection(index_name)

    def create_bot(self, bot: int | Bot):
        # create new bot
        conn, cur = self._pg_initialise()
        if type(bot) is int:
            # duplicate bot with given bot_id
            cur.execute("SELECT * FROM bots WHERE bot_id = %s AND acc_id = %s", (bot, self._acc_id))
            out = cur.fetchone()
            if out is not None:
                new = (self._acc_id, out[2], date.today(), out[4] + " copy", out[5], False, "temp", '')
                result = self._insert_retrieve(conn, cur, new)
                result = self._tuple_to_bot(result)
                self._create_supabase_index(result.supabase_index)
                return result
            else:
                raise HTTPException(404, detail="No matching record in the database")
        if type(bot) is Bot:
            # create new bot with given bot information
            new = (self._acc_id, bot.theme_id, date.today(), bot.bot_name, bot.bot_desc, bot.is_root, "temp", '')
            result = self._insert_retrieve(conn, cur, new)
            result = self._tuple_to_bot(result)
            self._create_supabase_index(result.supabase_index)
            return result
    
    def modify_bot(self, bot_id: int, bot: Bot):
        # modify bot with given bot_id and new information
        conn, cur = self._pg_initialise()
        temp = (bot.theme_id, bot.bot_name, bot.bot_desc, bot_id, self._acc_id)
        cur.execute("""UPDATE bots
            SET theme_id = %s, bot_name = %s, bot_desc = %s
            WHERE bot_id = %s AND acc_id = %s""", temp)
        cur.execute("SELECT * FROM bots WHERE bot_id = %s", (bot_id,))
        out = cur.fetchone()
        self._pg_close(conn, cur)
        if out is not None:
            return self._tuple_to_bot(out)
        else:
            raise HTTPException(404, detail="No matching record in the database")
    
    def read_bot(self, page_size: int, page_number: int | None):
        # list bots according to page_size and page_number
        conn, cur = self._pg_initialise()
        # define the range of bots to be retrieved
        end = page_size * page_number
        start = end - page_size + 1
        if page_number:
            cur.execute("""WITH rank_table AS (
                SELECT *, NTILE(%s) OVER (ORDER BY bot_id) AS rk
                FROM bots WHERE acc_id = %s)
                SELECT bot_id, acc_id, theme_id, creation_date, bot_name, bot_desc, is_root, supabase_index, environment
                FROM rank_table WHERE rk between %s and %s""", (BOT_LIMIT, self._acc_id, start, end))
        else:
            # return all bots if page_number == 0
            cur.execute("SELECT * FROM bots WHERE acc_id = %s ORDER BY bot_id", (self._acc_id,))
        out = cur.fetchall()
        result = list(map(self._tuple_to_bot, out))
        self._pg_close(conn, cur)
        return result
    
    def delete_bot(self, bot_id: int):
        # delete bot with given bot_id
        conn, cur = self._pg_initialise()
        cur.execute("SELECT * FROM bots WHERE bot_id = %s AND acc_id = %s", (bot_id, self._acc_id))
        out = cur.fetchone()
        if out is not None:
            cur.execute("DELETE FROM bots WHERE bot_id = %s AND acc_id = %s", (bot_id, self._acc_id))
        else:
            raise HTTPException(404, detail="No matching record in the database")
        self._pg_close(conn, cur)
        result = self._tuple_to_bot(out)
        self._delete_supabase_index(result.supabase_index)
        return result
    
if __name__ == "__main__":
    manager = BotManager(1)
    