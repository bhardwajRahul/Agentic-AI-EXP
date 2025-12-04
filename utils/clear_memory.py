"""Clear memory for a specific thread"""

from pathlib import Path
import sys


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from config.settings import DB_PATH

thread_id = "gmail_thread_003"  # Thread to clear

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Delete messages for this thread
cursor.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
deleted = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Deleted {deleted} messages from thread: {thread_id}")
