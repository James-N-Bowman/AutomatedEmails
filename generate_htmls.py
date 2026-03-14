import json
import csv
from datetime import datetime, timedelta
import os
from lxml import html
from lxml.html import builder as E

# --- Setup ---
JSON_FILE = 'parliament_data.json'
MAPPING_FILE = 'mapping.csv'
OUTPUT_DIR = 'docs'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_meeting_element(title, link, witness_blocks=None):
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
    
    # if img_url:
    #     elements.append(E.IMG(src=img_url, style="max-width:100%; height:auto; display:block; margin-bottom:10px;"))
    
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

    # 2. Load Mapping (ID -> Name, interest_id)
    committees_map = {}
    try:
        with open(MAPPING_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row:
                    committees_map[row[0].strip()] = {
                        'name': row[1].strip(),
                        'interest_id': row[2].strip() if len(row) > 2 else ''
                    }
    except FileNotFoundError:
        print(f"Error: {MAPPING_FILE} not found.")
        return

    # All committee content segments go into a single list.
    # Each entry is a raw string (MailChimp merge tags + rendered HTML),
    # because lxml would escape *|...|* syntax if passed through the element tree.
    all_segments = []

    # 3. Process each Committee from the mapping
    for c_id, c_info in committees_map.items():
        c_name = c_info['name']
        c_interest_id = c_info['interest_id']
        # --- News Filtering ---
        c_news = [n for n in data.get('news', []) if str(n.get('source_committee_id')) == c_id]
        
        # --- Events Filtering ---
        c_events = [
            e for e in data.get('events', []) 
            if any(str(comm.get('id')) == c_id for comm in e.get('committees', []))
        ]
        
        # --- Publications Filtering ---
        c_pubs = [
            p for p in data.get('publications', []) 
            if str(p.get('committee', {}).get('id')) == c_id
        ]

        # Only include content if there is something relevant
        if not (c_news or c_events or c_pubs):
            print(f"Skipping Committee {c_id}: No new content.")
            continue

        # Collect lxml elements for this committee's content
        committee_blocks = []

        # Committee heading
        committee_blocks.append(
            E.H1(f"{c_name}", style="font-family: Helvetica, Arial, sans-serif; color: #000; margin-bottom: 20px;")
        )

        # --- Publications Section ---
        if c_pubs:
            committee_blocks.append(E.H2("Reports yesterday", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_pubs:
                friendly_date = format_date(item.get('publicationStartDate'))
                committee_blocks.append(create_publication_element(
                    item.get('description'), 
                    item.get('additionalContentUrl'),
                    friendly_date
                ))

        # --- Meetings Section ---
        if c_events:
            committee_blocks.append(E.H2("Public meetings yesterday", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
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
                            role_info = f"{orgs[0].get('role')} at {orgs[0].get('name')}"
                            attendee_lis.append(E.LI(f"{name} ({role_info})"))
                        elif context:
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

                committee_blocks.append(create_meeting_element(
                    display_title,
                    link,
                    witness_blocks=witness_blocks
                ))

        # --- News Section ---
        if c_news:
            committee_blocks.append(E.H2("News yesterday", style="border-bottom: 2px solid #005ea5; padding-bottom: 5px;"))
            for item in c_news:
                friendly_date = format_date(item.get('datePublished'))
                committee_blocks.append(create_news_element(
                    item.get('heading'),
                    item.get('url'),
                    item.get('teaser'),
                    friendly_date,
                    item.get('imageUrl')
                ))

        # Spacer between committees
        committee_blocks.append(
            E.HR(style="border: none; border-top: 4px solid #005ea5; margin: 40px 0;")
        )

        # Render this committee's lxml elements to an HTML string
        committee_html = ''.join(
            html.tostring(block, pretty_print=True, method="html", encoding='unicode')
            for block in committee_blocks
        )

        # Wrap in MailChimp conditional merge tags so only subscribers
        # signed up to this committee's interest_id see the block.
        # The merge tags are placed inside a <div> so they sit within a valid
        # HTML element — MailChimp's HTML sanitiser strips bare text nodes
        # (including merge tags) that are direct children of the outer div.
        all_segments.append(
            f'*|INTERESTED:Select Committees:{c_name}|*<div>\n{committee_html}\n</div>*|END:INTERESTED|*'
        )

        print(f"Processed committee: {c_name}")

    # 4. Write everything to a single file named after yesterday's date
    if all_segments:
        yesterday = datetime.now() - timedelta(days=3)
        output_filename = yesterday.strftime("%Y-%m-%d") + ".html"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Write only the inner content div — no <html> or <body> wrapper.
        # MailChimp wraps the HTML in its own shell when sending; supplying
        # your own <html>/<body> tags can cause MailChimp to rewrite the
        # structure before evaluating merge tags, which prevents
        # *|INTERESTED:...|* blocks from being processed correctly.
        inner_content = '\n'.join(all_segments)
        full_html = (
            '<div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.5;">\n'
            f'{inner_content}'
            '</div>'
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Generated: {output_path}")
    else:
        print("No content found for any committee. No file generated.")

if __name__ == "__main__":
    main()