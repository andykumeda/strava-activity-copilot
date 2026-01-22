
from dateparser.search import search_dates
import datetime

texts = [
    'what run was performed april 19 2024? also list the segments from that day',
    'what run was performed april 19 2024 also the segments from that day'
]

print("--- Testing search_dates ---")
for text in texts:
    # strict=False is default for search_dates
    found = search_dates(text, settings={'PREFER_DATES_FROM': 'past'})
    print(f"Input: '{text}' -> Found: {found}")
