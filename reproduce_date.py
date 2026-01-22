
import dateparser
from datetime import datetime

texts = [
    'what run was performed april 19 2024? also list the segments from that day',
    'what run was performed april 19 2024 also the segments from that day',
    'april 19 2024'
]

print("--- Testing DateParser ---")
for text in texts:
    parsed = dateparser.parse(text, settings={
        'PREFER_DATES_FROM': 'past',
        'RELATIVE_BASE': datetime(2026, 1, 21),
        'STRICT_PARSING': False
    })
    print(f"Input: '{text}' -> Parsed: {parsed}")
