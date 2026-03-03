import json
import csv
import os
from lxml import html
from lxml.html import builder as E

# --- Setup ---
JSON_FILE = 'parliament_data.json'
MAPPING_FILE = 'mapping.csv'
OUTPUT_DIR = 'HTMLs'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_item_element(title, text, link, date=None, img_url=None):
    """Creates a consistent HTML block for an item."""
    elements = []
    
    if img_url:
        elements.append(E.IMG(src=img_url, style="max-width:100%; height:auto; display:block; margin-bottom:10px;"))
    
    # Title as a link
    elements.append(E.A(E.B(title), href=link, style="font-size: 1.1em; color: #005ea5; text-decoration: underline;"))
    
    # Text and Date
    display_text = f"{text}"
    if date:
        # Simple cleanup of ISO date strings for the email
        clean_date = date.split('T')[0]
        display_text += f" ({clean_date})"
        
    elements.append(E.P(display_text, style="margin-top: 5px; color: #333; font-size: 0.95em;"))
    
    return E.DIV(*elements, style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;")

def main():
    # 1. Load Data
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {JSON_FILE} not found.")
        return

    # 2. Load Mapping (ID -> Name)
    committees_map = {}
    try:
        with open(MAPPING_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row:
                    committees_map[row[0].strip()] = row[1].strip()
    except FileNotFoundError:
        print(f"Error: {MAPPING_FILE} not found.")
        return

    # 3. Process each Committee from the mapping
    for c_id, c_name in committees_map.items():
        # --- News Filtering ---
        c_news = [n for n in data.get('news', []) if str(n.get('source_committee_id')) == c_id]
        
        # --- Events Filtering ---
        # Checks if the committee ID is in the list of committee dictionaries for the event
        c_events = [
            e for e in data.get('events', []) 
            if any(str(comm.get('id')) == c_id for comm in e.get('committees', []))
        ]
        
        # --- Publications Filtering ---
        c_pubs = [
            p for p in data.get('publications', []) 
            if str(p.get('committee', {}).get('id')) == c_id
        ]

        # Only create a file if there is relevant content
        if not (c_news or c_events or c_pubs):
            print(f"Skipping Committee {c_id}: No new content.")
            continue

        # Build HTML Content
        content_blocks = [
            E.H1(f"{c_name}", style="font-family: Helvetica, Arial, sans-serif; color: #000; margin-bottom: 20px;")
        ]

        # --- Publications Section ---
        if c_pubs:
            content_blocks.append(E.H2("Reports this week", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_pubs:
                content_blocks.append(create_item_element(
                    item.get('description'),
                    "New Publication",
                    item.get('additionalContentUrl'),
                    item.get('publicationStartDate')
                ))

        # --- Meetings Section ---
        if c_events:
            content_blocks.append(E.H2("Public meetings this week", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_events:
                event_id = item.get('id')
                # Formatted link as requested
                link = f"https://committees.parliament.uk/event/{event_id}/formal-meeting-private-meeting/"
                event_type_name = item.get('eventType', {}).get('name', 'Meeting')
                content_blocks.append(create_item_element(
                    event_type_name,
                    "Committee Meeting",
                    link,
                    item.get('startDate')
                ))

        # --- News Section ---
        if c_news:
            content_blocks.append(E.H2("News this week", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_news:
                content_blocks.append(create_item_element(
                    item.get('heading'),
                    item.get('teaser'),
                    item.get('url'),
                    item.get('datePublished'), # Matched to your JSON key
                    item.get('imageUrl')
                ))

        # Wrap in full HTML structure
        doc = E.HTML(
            E.BODY(
                E.DIV(*content_blocks, style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.5;"),
                style="margin: 0; padding: 20px; background-color: #ffffff;"
            )
        )

        # Write to file
        file_path = os.path.join(OUTPUT_DIR, f"{c_id}.html")
        with open(file_path, 'wb') as f:
            f.write(html.tostring(doc, pretty_print=True, method="html", encoding='utf-8'))
        
        print(f"Generated: {file_path}")

if __name__ == "__main__":
    main()