import json
import csv
from datetime import datetime
import os
from lxml import html
from lxml.html import builder as E

# --- Setup ---
JSON_FILE = 'parliament_data.json'
MAPPING_FILE = 'mapping.csv'
OUTPUT_DIR = 'HTMLs'
INDEX_FILE = 'index.html'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_meeting_element (title, link, witness_blocks=None):
    """Creates a consistent HTML block for an item, now with optional witness lists."""
    elements = []
        
    # Title as a link
    elements.append(E.A(E.B(title), href=link, style="font-size: 1.1em; color: #005ea5; text-decoration: underline;"))
    
    # Add witness sections if they exist
    if witness_blocks:
        elements.extend(witness_blocks)
    
    return E.DIV(*elements, style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;")

def create_news_element(title, link, teaser_text, date_text, img_url=None):
    """Creates a consistent HTML block for an item, now with optional witness lists."""
    elements = []
    
    if img_url:
        elements.append(E.IMG(src=img_url, style="max-width:100%; height:auto; display:block; margin-bottom:10px;"))
    
    # Title as a link
    elements.append(E.A(E.B(title), href=link, style="font-size: 1.1em; color: #005ea5; text-decoration: underline;"))

    elements.append(E.P(teaser_text, style="margin-top: 5px; color: #333; font-size: 0.95em;"))

    elements.append(E.P(date_text, style="margin-top: 5px; color: #333; font-size: 0.95em;"))
    
    return E.DIV(*elements, style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;")

def create_publication_element(title, link, date_text):
    """Creates a consistent HTML block for an item, now with optional witness lists."""
    elements = []
        
    # Title as a link
    elements.append(E.A(E.B(title), href=link, style="font-size: 1.1em; color: #005ea5; text-decoration: underline;"))
        
    elements.append(E.P(date_text, style="margin-top: 5px; color: #333; font-size: 0.95em;"))
    
    return E.DIV(*elements, style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;")

def format_time(date_str):
    """Converts ISO date string to HH:MMam/pm format."""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%I:%M%p").lower().lstrip('0')
    except:
        return ""

def format_date(date_str):
    """Converts ISO date string to d mmm yyyy format."""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%-d %b %Y")
    except:
        return ""

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

    # Keep track of generated files for the index
    generated_committees = []


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
                friendly_date = format_date(item.get('publicationStartDate'))
                content_blocks.append(create_publication_element(
                    item.get('description'), 
                    item.get('additionalContentUrl'),
                    friendly_date
                ))

        # --- Meetings Section ---
        if c_events:
            content_blocks.append(E.H2("Public meetings this week", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_events:
                event_id = item.get('id')
                link = f"https://committees.parliament.uk/event/{event_id}/formal-meeting-private-meeting/"
                
                activities = item.get('activities', []) or []
                oral_evidence_activities = [a for a in activities if a.get('activityType') == "Oral evidence"]
                
                # Determine Inquiry Title
                inquiry_titles = {biz.get('title') for a in oral_evidence_activities for biz in a.get('committeeBusinesses', []) if biz.get('title')}
                
                date_string = item.get('startDate')
                friendly_date = format_date(date_string)

                if len(inquiry_titles) == 1:
                    display_title = f"{friendly_date}: {list(inquiry_titles)[0]}"
                elif len(inquiry_titles) > 1:
                    display_title = f"{friendly_date}: multiple inquiries"
                else:
                    display_title = item.get('eventType', {}).get('name', 'Meeting')

                # Build Witness Blocks
                witness_blocks = []
                for activity in oral_evidence_activities:
                    time_str = format_time(activity.get('startDate'))
                    attendee_lis = []
                    
                    for person in activity.get('attendees', []):
                        name = person.get('name')
                        orgs = person.get('organisations', [])
                        context = person.get('additionalContext')
                        
                        if orgs:
                            # Format: Name (Role at Organisation)
                            role_info = f"{orgs[0].get('role')} at {orgs[0].get('name')}"
                            attendee_lis.append(E.LI(f"{name} ({role_info})"))
                        elif context:
                            # Format: Name (AdditionalContext)
                            attendee_lis.append(E.LI(f"{name} ({context})"))
                        else:
                            attendee_lis.append(E.LI(name))
                    
                    if attendee_lis:
                        witness_blocks.append(
                            E.DIV(
                                E.DIV(
                                    E.DIV(time_str, CLASS="attendee-time", style="font-weight: bold; margin-bottom: 5px;"),
                                    E.UL(*attendee_lis, style="margin-top: 0;"),
                                    CLASS="attendee"
                                ),
                                CLASS="activity",
                                style="margin-top: 15px; font-size: 0.9em;"
                            )
                        )

                content_blocks.append(create_meeting_element(
                    display_title,
                    link,
                    witness_blocks=witness_blocks
                ))

        # --- News Section ---
        if c_news:
            content_blocks.append(E.H2("News this week", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_news:

                friendly_date = format_date(item.get('datePublished'))

                content_blocks.append(create_news_element(
                    item.get('heading'),
                    item.get('url'),
                    item.get('teaser'),
                    friendly_date,
                    item.get('imageUrl')
                ))

        # Wrap in full HTML structure
        doc = E.HTML(
            E.BODY(
                E.DIV(*content_blocks, style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.5;"),
                style="margin: 0; padding: 20px; background-color: #ffffff;"
            )
        )

        # Write to file in OUTPUT_DIR
        file_name = f"{c_id}.html"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        with open(file_path, 'wb') as f:
            f.write(html.tostring(doc, pretty_print=True, method="html", encoding='utf-8'))
        
        # Add to our list for the index page
        generated_committees.append({'id': c_id, 'name': c_name, 'filename': file_name})
        print(f"Generated: {file_path}")

    # --- 4. Generate the Index HTML File ---
    if generated_committees:
        index_items = []
        base_url = "https://htmlpreview.github.io/?https://raw.githubusercontent.com/James-N-Bowman/AutomatedEmails/refs/heads/main/HTMLs/"
        
        for item in generated_committees:
            full_url = f"{base_url}{item['filename']}"
            index_items.append(
                E.LI(
                    E.A(item['name'], href=full_url, style="color: #005ea5; text-decoration: underline;")
                )
            )

        index_doc = E.HTML(
            E.BODY(
                E.H1("Committee Email Previews", style="font-family: Helvetica, Arial, sans-serif;"),
                E.UL(*index_items, style="font-family: Helvetica, Arial, sans-serif; line-height: 1.8;"),
                style="padding: 40px; background-color: #f9f9f9;"
            )
        )

        with open(INDEX_FILE, 'wb') as f:
            f.write(html.tostring(index_doc, pretty_print=True, method="html", encoding='utf-8'))
        print(f"Generated Index: {INDEX_FILE}")

if __name__ == "__main__":
    main()