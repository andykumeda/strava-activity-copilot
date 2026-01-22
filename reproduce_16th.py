
from dateparser.search import search_dates
import datetime

texts = [
    'what is the elapsed time for the 16th running of the angeles crest 100',
    '16th running',
    '16th'
]

print("--- Testing Ordinal Parsing ---")
for text in texts:
    found = search_dates(text, settings={'PREFER_DATES_FROM': 'past'})
    print(f"Input: '{text}' -> Found: {found}")
