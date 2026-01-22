# Feature Requests & Known Limitations

## Known Limitations

### Full-History Private Note Search
**Status**: Limited Support
- **Issue**: The Strava List API does not return `private_note` or `description` fields.
- **Impact**: We cannot search *all* historical notes instantly without fetching details for every single activity (thousands of API calls).
- **Current Solution**: The system allows searching notes for **specific date ranges** or **recent activities** (up to ~20 items) by dynamically fetching details on demand.
- **Future Work**: Implement a background crawler to slowly index all historical activity details into a local database for full-text search capability.

## Future Ideas

- [ ] **Background Sync**: detailed crawler to fetch full activity details for the entire history.
- [ ] **Data Export**: Allow users to export their joined/enriched data as JSON/CSV.
- [ ] **Saved Queries**: Allow saving complex comparison queries as dashboard widgets.
