import asyncio
import aiosqlite
from pathlib import Path
import sys
import re

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from config.settings import MEMORY_DB
from utils.helper import setup_logger

logger = setup_logger(__name__)


class EpisodicRAG:
    def __init__(self, db_path=MEMORY_DB, past_summery_date=None):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.past_summery_date = past_summery_date

    def clean_messages(self, text: str):

        PREFIX_PATTERN = re.compile(
            r"^(TALK TO USER:|FINAL ANSWER:|CLARIFICATION NEEDED:)\s*", re.IGNORECASE
        )

        # Removes decorative lines like "---", "===", "|---|", or "___"
        DECORATOR_PATTERN = re.compile(r"[-=_*|]{3,}")

        LOG_HEADER_PATTERN = re.compile(
            r"^\[.*?\] \[.*?\]\s*"
        )  # for old logs this is need but new logs wont have this

        if not text:
            return None

        # 1. Drop Tool Failures / Internal Thought Leakage
        if "<|channel|>" in text:
            return None

        # 2. Drop Routing Logs
        if text.startswith("Routing to:"):
            return None

        # # 3. Drop Generic Tool Usage Logs  # need to confirm
        # if text.startswith("Using tools:"):
        #     return None

        # 4. Drop Tool Call Confirmations
        if text == "Tool calls made":
            return None

        # --- STEP 2: CONTENT CLEANING (Regex) ---

        # 1. Remove Log Headers (if any exist in the body)
        text = LOG_HEADER_PATTERN.sub("", text)

        # 2. Remove Agent Prefixes ("TALK TO USER:")
        text = PREFIX_PATTERN.sub("", text)

        # 3. Remove Table Borders / Separators (The "---" and "|---|")
        text = DECORATOR_PATTERN.sub(" ", text)

        # --- STEP 3: WHITESPACE FLATTENING ---

        # Replace Newlines and Tabs with a single space (As you requested)
        text = text.replace("\n", " ").replace("\t", " ")

        # Collapse multiple spaces into one (The "strip" effect)
        # logic: split() splits by ANY whitespace, join puts them back with 1 space
        cleaned_text = " ".join(text.split())

        # Final check: If cleaning left us with nothing, drop it
        if not cleaned_text:
            return None

        return cleaned_text

    async def custom_text_splitters(self):
        if not self.past_summery_date:
            logger.warning("Past summery date is not set. No data will be retrieved.")
            return

        past_summery_date = self.past_summery_date
        query = "SELECT timestamp, actor, message from human_logs where timestamp > ?"
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, (past_summery_date,)) as cursor:
                rows = await cursor.fetchall()
                logger.info(f"length of rows: {len(rows)}")
                logger.info(f"first 5 rows: {[row[2] for row in rows]}")

                # # chunking logic starts from here
                # buffer= ""

                # for i in range(len(rows)):
                #     metadata={}
                #     timestamp, actor, message = rows[i]
                #     metadata["timestamp"] = timestamp
                #     metadata["actor"] = actor
                #     if len(buffer)+len(message)<748:
                #         logger.info(f"buffer: {buffer}")
                #         buffer=""


if __name__ == "__main__":
    past_summery_date = "2024-01-01 00:00:00"
    rag = EpisodicRAG(past_summery_date=past_summery_date)
    asyncio.run(rag.custom_text_splitters())
