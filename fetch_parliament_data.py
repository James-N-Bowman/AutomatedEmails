import json
import logging
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import helpers_mapping_csv
import helpers_logging

# Initialize Logger
helpers_logging.SimpleLogger('fetch_logger', 'INFO')
logger = logging.getLogger('fetch_logger')

OUTPUT_DIR = 'docs'

# --- Configuration & Constants ---
PAGE_SIZE = 30

uk_tz = ZoneInfo("Europe/London")
uk_time_now = datetime.now(uk_tz)
uk_8am_today = datetime.combine(uk_time_now.date(), time(8, 0), tzinfo=uk_tz)
uk_8am_yesterday = uk_8am_today - timedelta(days=1)
yesterday_param = uk_8am_yesterday.strftime('%Y-%m-%d')
today_param = uk_8am_today.strftime('%Y-%m-%d')

def fetch_all_pages(base_url, params, stop_condition=None):
    """
    Generic pagination handler. 
    If stop_condition(item) returns True, fetching halts (used for date-sorted feeds).
    """
    all_items = []
    skip = 0
    
    while True:
        current_params = {**params, 'Skip': str(skip)}
        logger.info(f"Fetching: {base_url} (Skip: {skip})")
        
        try:
            response = requests.get(base_url, params=current_params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {base_url}: {e}")
            break

        # Normalize data structure (handle lists or dicts with 'items')
        items = data.get('items', data) if isinstance(data, dict) else data
        
        if not items:
            break

        for item in items:
            # Check if this is a wrapped 'value' object (common in News API)
            item_content = item.get('value', item) if isinstance(item, dict) else item
            
            if stop_condition and stop_condition(item_content):
                logger.info("Stop condition met. Ending pagination.")
                return all_items
            
            all_items.append(item_content)

        if len(items) < PAGE_SIZE:
            break
            
        skip += PAGE_SIZE
        
    return all_items

def is_old_news(item):
    """Returns True if the news item is older than the date range."""
    pub_date_str = item.get('datePublished', '')
    if not pub_date_str:
        return False
    # Handle ISO format and UTC 'Z'
    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
    return pub_date < uk_8am_yesterday

def is_recent_publication(item):
    pub_start_date_str = item.get('publicationStartDate','')
    pub_start_date_naive = datetime.fromisoformat(pub_start_date_str)
    pub_start_date = pub_start_date_naive.replace(tzinfo=uk_tz)
    return pub_start_date > uk_8am_yesterday

def main():
    # --- Step 0: Load Allowed Committee IDs ---
    try:
        allowed_ids = helpers_mapping_csv.fetch_cttee_ids_from_mapping_CSV()
    except FileNotFoundError:
        logger.error("Critical Error: mapping.csv not found.")
        return

    # --- ENDPOINT 1: Events ---
    # Date logic handled via API params
    events_params = {
        'GroupChildEventsWithParent': 'false',
        'StartDateFrom': yesterday_param,
        'StartDateTo': today_param,
        'ExcludeCancelledEvents': 'true',
        'House': 'Commons',
        'IncludeEventAttendees': 'true',
        'ShowOnWebsiteOnly': 'true'
    }
    raw_events = fetch_all_pages("https://committees-api.parliament.uk/api/Events", events_params)
    
    events_data = [
        e for e in raw_events 
        if any(c.get('id') in allowed_ids for c in e.get('committees', []))
        and any(a.get('activityType') == "Oral evidence" for a in e.get('activities', []))
    ]

    # --- ENDPOINT 2: Publications (Reports) ---
    # Date logic handled via API params
    pubs_params = {
        'PublicationTypeIds': [1, 12],
        'StartDate': yesterday_param,
        'EndDate': today_param,
        'SortOrder': 'PublicationDateDescending',
        'ShowOnWebsiteOnly': 'true'
    }
    raw_pubs = fetch_all_pages("https://committees-api.parliament.uk/api/Publications", pubs_params)
    
    pubs_data = [
        p for p in raw_pubs 
        if p.get('committee', {}).get('id') in allowed_ids and is_recent_publication(p)
    ]

    # --- ENDPOINT 3: Committee News ---
    # Date logic handled via stop_condition (client-side)
    all_news_data = []
    for c_id in allowed_ids:
        news_url = f"https://www.parliament.uk/api/content/committee/{c_id}/news/"
        logger.info(f"Processing news for Committee: {c_id}")
        
        committee_news = fetch_all_pages(news_url, {}, stop_condition=is_old_news)
        
        for item in committee_news:
            item['source_committee_id'] = c_id
            all_news_data.append(item)

    # --- Step 4: Output ---
    output = {
        "metadata": {
            "extracted_at": uk_time_now.isoformat(), 
            "range": [uk_8am_yesterday.isoformat(), uk_8am_today.isoformat()]
        },
        "events": events_data,
        "publications": pubs_data,
        "news": all_news_data
    }

    today = datetime.now()
    output_filename = today.strftime("%Y-%m-%d") + ".json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # This ensures the 'docs' directory is created if it doesn't exist
    # parents=True allows creating nested folders; exist_ok=True prevents errors if it's already there
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=4)
    
    logger.info(f"Saved to {output_path}: {len(events_data)} Events, "
                f"{len(pubs_data)} Pubs, {len(all_news_data)} News.")

if __name__ == "__main__":
    main()