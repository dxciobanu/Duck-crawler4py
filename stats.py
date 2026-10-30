import sqlite3
import re
from urllib.parse import urlparse, urldefrag
from collections import Counter

DB_FILE = "crawler_stats.db"

# list of English stop words
STOP_WORDS = {"a", "an", "the", "and", "or", "but", "if", "then", "is", "are", "was",
              "were", "be", "been", "being", "to", "of", "in", "on", "at", "for",
              "with", "by", "from", "as", "it", "this", "that", "these", "those",
              "i", "you", "he", "she", "we", "they", "them", "his", "her", "their",
              "our", "your", "its", "not", "no", "do", "does", "did", "have", "has",
              "had", "will", "would", "can", "could", "should"
              }


def initialize_db():
    # create tables
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
            url TEXT PRIMARY KEY,
            hostname TEXT,
            word_count INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                frequency INTEGER
            )
        """)


def record_page(url, text):
    # remove url fragments to receive the unique url
    url, fragment = urldefrag(url)

    try:
        hostname = urlparse(url).hostname
    except (TypeError, ValueError):
        return

    if not hostname:
        return

    # extract words from visible text, no # tho
    tokens = re.findall(r"[a-zA-Z]+", text.lower())

    # count all the words for the longest page stat
    word_count = len(tokens)

    # remove stop words for frequency stat
    frequencies = Counter(
        word for word in tokens
        if word not in STOP_WORDS
    )

    with sqlite3.connect(DB_FILE) as conn:
        # only record url once
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO pages
            (url, hostname, word_count)
            VALUES (?, ?, ?)
            """,
            (url, hostname, word_count)
        )

        # don't count words for duplicate pages
        if cursor.rowcount == 0:
            return

        # update global word frequencies
        for word, count in frequencies.items():
            conn.execute(
                """
                INSERT INTO words (word, frequency)
                VALUES (?, ?)
                ON CONFLICT(word)
                DO UPDATE SET frequency = frequency + excluded.frequency
                """,
                (word, count)
            )


def print_report():
    with sqlite3.connect(DB_FILE) as conn:

        # unique pages by url
        total = conn.execute(
            "SELECT COUNT(*) FROM pages"
        ).fetchone()[0]

        print(f"\nTotal unique pages: {total}")

        # longest page
        longest = conn.execute(
            """
            SELECT url, word_count
            FROM pages
            ORDER BY word_count DESC
            LIMIT 1
            """
        ).fetchone()

        print("\nLongest page:")
        print(longest)

        # most common words
        print("\nTop 50 words:")

        words = conn.execute(
            """
            SELECT word, frequency
            FROM words
            ORDER BY frequency DESC, word ASC
            LIMIT 50
            """
        ).fetchall()

        for word, frequency in words:
            print(f"{word}: {frequency}")

        # ICS subdomains
        print("\nCrawled domains and subdomains:")

        subdomains = conn.execute(
            """
            SELECT hostname, COUNT(*)
            FROM pages
            WHERE hostname = 'ics.uci.edu'
               OR hostname LIKE '%.ics.uci.edu'
               OR hostname = 'cs.uci.edu'
               OR hostname LIKE '%.cs.uci.edu'
               OR hostname = 'informatics.uci.edu'
               OR hostname LIKE '%.informatics.uci.edu'
               OR hostname = 'stat.uci.edu'
               OR hostname LIKE '%.stat.uci.edu'
            GROUP BY hostname
            ORDER BY hostname
            """
        ).fetchall()

        for hostname, count in subdomains:
            print(f"{hostname}, {count}")


initialize_db()
