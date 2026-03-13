
from datetime import datetime, timedelta, timezone
import json
import requests

import helpersCSVMapping
import helpersLogging

helpersLogging.SimpleLogger('fetch_logger','INFO')

# 1. Setup Dates
# Use timezone.utc to make these "offset-aware"

now = datetime.now(timezone.utc)
yesterday = now - timedelta(days=1)

# Format for API: 'YYYY-MM-DD'
START_DATE = yesterday.strftime('%Y-%m-%d')
END_DATE = yesterday.strftime('%Y-%m-%d')

def fetch_all_pages(base_url, params, date_field=None):
    """Generic function to handle pagination via the 'Skip' parameter."""
    all_items = []
    skip = 0
    page_size = 30
    
    while True:
        current_params = params.copy()
        current_params['Skip'] = str(skip)
        
        print(f"Fetching: {base_url} with skip={skip}")
        response = requests.get(base_url, params=current_params)
        response.raise_for_status()
        data = response.json()
        
        # Adjust based on specific API response structure
        # Most of these APIs return a list or an object containing 'items'
        items = data.get('items', data) if isinstance(data, dict) else data
        
        if not items:
            break
            
        # For the News API (no date filter in URL), we check the date here
        if date_field:
            filtered_items = []
            stop_pagination = False
            for item in items:
                # Parse the date from the API (usually ISO format)
                item_value = item['value']
                # Use fromisoformat and ensure it handles the 'Z' correctly as UTC
                item_date = datetime.fromisoformat(item_value[date_field].replace('Z', '+00:00'))
                if item_date >= yesterday:
                    filtered_items.append(item_value)
                else:
                    stop_pagination = True
            
            all_items.extend(filtered_items)
            if stop_pagination:
                break
        else:
            all_items.extend(items)

        # If we got fewer items than the page size, we've reached the end
        if len(items) < page_size:
            break
            
        skip += page_size
        
    return all_items

def main():

    # --- Step 0: Load Allowed Committee IDs ---
    allowed_ids = set()
    try:
        allowed_ids = helpersCSVMapping.fetch_cttee_ids_from_mapping_CSV()
    except FileNotFoundError:
        print("Error: mapping.csv not found.")

    # --- ENDPOINT 1: Events ---
    events_url = "https://committees-api.parliament.uk/api/Events"
    events_params = {
        'GroupChildEventsWithParent': 'false',
        'StartDateFrom': START_DATE,
        'StartDateTo': END_DATE,
        'ExcludeCancelledEvents': 'true',
        'House': 'Commons',
        'IncludeEventAttendees': 'true',
        'ShowOnWebsiteOnly': 'true'
    }
    raw_events = fetch_all_pages(events_url, events_params)
    # Filter: Keep event if ANY committee ID in the list matches our set
    events_data_part_raw = [
        e for e in raw_events 
        if any(c.get('id') in allowed_ids for c in e.get('committees', []))
    ]
    events_data = [
        e for e in events_data_part_raw
        if any(a.get('activityType')=="Oral evidence" for a in e.get('activities',[]))
    ]
    # --- ENDPOINT 2: Publications ---
    pubs_url = "https://committees-api.parliament.uk/api/Publications"
    pubs_params = {
        'PublicationTypeIds': [1, 12],
        'StartDate': START_DATE,
        'EndDate': END_DATE,
        'SortOrder': 'PublicationDateDescending',
        'ShowOnWebsiteOnly': 'true'
    }
    raw_pubs = fetch_all_pages(pubs_url, pubs_params)
    # Filter: Keep publication if the committee ID matches our set
    pubs_data = [
        p for p in raw_pubs 
        if p.get('committee', {}).get('id') in allowed_ids
    ]

    # --- ENDPOINT 3: Committee News ---
    # Example Committee ID: 1 (You may need to loop a list of IDs if you have many)
# --- ENDPOINT 3: Committee News (Looping via CSV) ---
    all_news_data = []

    for c_id in allowed_ids:
        c_id_string = str(c_id)
        news_url = f"https://www.parliament.uk/api/content/committee/{c_id_string}/news/"
        print(f"Fetching news for Committee ID: {c_id_string}")
        
        # Fetch and filter by date
        committee_news = fetch_all_pages(news_url, {}, date_field='datePublished')
        
        # Optional: Add the committee ID to each news item so you know where it came from
        for item in committee_news:
            item['source_committee_id'] = c_id
            
        all_news_data.extend(committee_news)

    # Update the news key in your output dictionary
    output = {
        "metadata": {"extracted_at": now.isoformat(), "range": [START_DATE, END_DATE]},
        "events": events_data,
        "publications": pubs_data,
        "news": all_news_data  # Changed from news_data to all_news_data
    }

    with open('parliament_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"Successfully saved {len(events_data)} events, {len(pubs_data)} publications, and {len(all_news_data)} news items.")

if __name__ == "__main__":
    main()