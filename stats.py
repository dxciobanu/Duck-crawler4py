import sqlite3
import re
from urllib.parse import urlparse, urldefrag
from collections import Counter
from pathlib import Path

DB_FILE = Path(__file__).resolve().with_name("crawler_stats.db")

# list of English stop words
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am",
    "an", "and", "any", "are", "aren't", "as", "at", "be",
    "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did",
    "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
    "he'd", "he'll", "he's", "her", "here", "here's", "hers",
    "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me",
    "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd",
    "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their",
    "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "very",
    "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's",
    "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves"
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
