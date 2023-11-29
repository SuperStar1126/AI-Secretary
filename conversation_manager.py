import psycopg2
from custom_types import ChannelType, ConversationHistory, Conversation
from config import PARAM
from fastapi import HTTPException

class ConversationManager:

    # class used to manage the conversation_history table in the SQL database
    # currently only has one function to retrieve records

    def __init__(self, bot_id):
        self._bot_id = bot_id
    
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

    def _dict_to_conv(self, jsons: list[dict]) -> list[Conversation]:
        # convert conversation jsons in the database into a list of Conversation
        convs = []
        for json in jsons:
            conv = Conversation(
                human=json["human"],
                ai=json["ai"],
                source=json["source"]
            )
            convs.append(conv)
        return convs

    def _tuple_to_history(self, history: tuple) -> ConversationHistory:
        # convert tuple records to ConversationHistory
        conv_his =  ConversationHistory(
            conversation_id=history[0],
            bot_id=history[1],
            conversation=self._dict_to_conv(history[3]),
            channel_type=ChannelType[history[4]],
            channel_id=history[5],
            last_updated_time=history[6]
        )
        return conv_his

    def view_history(self, channel_type: ChannelType | None, conversation_id: int | None) -> list[ConversationHistory]:
        # view conversation history
        conn, cur = self._pg_initialise()
        if channel_type:
            if conversation_id:
                # view specific conversation with given conversation_id
                cur.execute("SELECT * FROM conversation_history WHERE bot_id = %s AND channel_type = %s AND conversation_id = %s",
                    (self._bot_id, channel_type.value, conversation_id))
                out = cur.fetchone()
                if out is None:
                    raise HTTPException(404, detail="No matching record in the database")
                else:
                    out = [out]
            else:
                # view all conversations under the same give nchannel_type
                cur.execute("SELECT * FROM conversation_history WHERE bot_id = %s AND channel_type = %s", (self._bot_id, channel_type.value))
                out = cur.fetchall()
        else:
            if conversation_id:
                # view specific conversation with given conversation_id
                cur.execute("SELECT * FROM conversation_history WHERE bot_id = %s AND conversation_id = %s", (self._bot_id, conversation_id))
                out = cur.fetchone()
                if out is None:
                    raise HTTPException(404, detail="No matching record in the database")
                else:
                    out = [out]
            else:
                # view all history with given bot_id
                cur.execute("SELECT * FROM conversation_history WHERE bot_id = %s", (self._bot_id,))
                out = cur.fetchall()
        result = list(map(self._tuple_to_history, out))
        self._pg_close(conn, cur)
        return result

if __name__ == "__main__":
    manager = ConversationManager(12)
    print(type(manager.view_history(ChannelType.whatsapp, 1)[3][1]))