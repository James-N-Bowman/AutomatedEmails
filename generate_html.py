import json
import csv
from datetime import datetime
import os

from lxml import html
from lxml.html import builder as E

# --- Setup ---
MAPPING_FILE = 'mapping.csv'
OUTPUT_DIR = 'docs'

# The CSS block provided by the user
CSS_STYLE = """
    <style>
        .email-body {
            font-family: Tahoma, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.5;
            color: #333;
        }
        h1 {
            color: #006548;
            margin-bottom: 20px;
            font-size: 24px;
        }
        h2 {
            color: #006548;
            border-bottom: 2px solid #006548;
            padding-bottom: 5px;
            font-size: 18px;
            margin-top: 25px;
        }
        p {
            margin-top: 5px;
            font-size: 14px;
        }
        a {
            color: #005ea5;
            text-decoration: underline;
        }
        ul {
            margin-top: 0;
            font-size: 14px;
        }
        hr {
            border: none;
            border-top: 4px solid #006548;
            margin: 40px 0;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin-bottom: 15px;
            border: 0;
        }
        .timestamp {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .news-block {
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
    </style>
"""

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_meeting_element(title, link, witness_blocks=None):
    elements = []
    elements.append(E.A(E.B(title), href=link))
    if witness_blocks:
        elements.extend(witness_blocks)
    return E.DIV(*elements, class_="news-block")

def sanitise_for_url(text):
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def create_news_element(title, link, teaser_text, date_text, img_url=None):
    elements = []

    # if img_url:
    #     elements.append(E.IMG(src=img_url, style="max-width:100%; height:auto; display:block; margin-bottom:10px;"))

    elements.append(E.A(E.B(title), href=link))
    elements.append(E.P(teaser_text))
    elements.append(E.P(date_text))
    return E.DIV(*elements, class_="news-block")

def create_publication_element(title, link, date_text):
    elements = []
    if link == None:
        elements.append(E.P(E.B(title)))
    else:
        elements.append(E.A(E.B(title), href=link))
    elements.append(E.P(date_text))
    return E.DIV(*elements, class_="news-block")

def format_time(date_str):
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%I:%M%p").lower().lstrip('0')
    except:
        return ""

def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%-d %b %Y")
    except:
        return ""

def main():

    today = datetime.now()
    json_file = today.strftime("%Y-%m-%d") + ".json"
    json_path = os.path.join(OUTPUT_DIR, json_file)

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_path} not found.")
        return

    committees_map = {}
    try:
        with open(MAPPING_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) 
            for row in reader:
                if row:
                    committees_map[row[0].strip()] = {
                        'name': row[1].strip(),
                        'interest_id': row[2].strip() if len(row) > 2 else ''
                    }
    except FileNotFoundError:
        print(f"Error: {MAPPING_FILE} not found.")
        return

    all_segments = []

    for c_id, c_info in committees_map.items():
        c_name = c_info['name']
        c_news = [n for n in data.get('news', []) if str(n.get('source_committee_id')) == c_id]
        c_events = [
            e for e in data.get('events', []) 
            if any(str(comm.get('id')) == c_id for comm in e.get('committees', []))
        ]
        c_pubs = [
            p for p in data.get('publications', []) 
            if str(p.get('committee', {}).get('id')) == c_id
        ]

        if not (c_news or c_events or c_pubs):
            continue

        committee_blocks = []
        committee_blocks.append(E.H1(f"{c_name}"))

        if c_pubs:
            committee_blocks.append(E.H2("Reports"))
            for item in c_pubs:
                pub_url = item.get('additionalContentUrl')
                if not pub_url:
                    documents = item.get('documents', [])
                    if not documents:
                        continue
                    pub_url = f"https://committees.parliament.uk/publications/{item.get('id')}/documents/{documents[0].get('documentId')}/default/"
                committee_blocks.append(create_publication_element(
                    item.get('description'), 
                    pub_url,
                    format_date(item.get('publicationStartDate'))
                ))

        if c_events:
            committee_blocks.append(E.H2("Public meetings"))
            for item in c_events:
                link = f"https://committees.parliament.uk/event/{item.get('id')}/formal-meeting-private-meeting/"
                activities = item.get('activities', []) or []
                oral_evidence_activities = [a for a in activities if a.get('activityType') == "Oral evidence"]
                inquiry_titles = {biz.get('title') for a in oral_evidence_activities for biz in a.get('committeeBusinesses', []) if biz.get('title')}
                
                friendly_date = format_date(item.get('startDate'))
                if len(inquiry_titles) == 1:
                    display_title = f"{friendly_date}: {list(inquiry_titles)[0]}"
                elif len(inquiry_titles) > 1:
                    display_title = f"{friendly_date}: multiple inquiries"
                else:
                    display_title = item.get('eventType', {}).get('name', 'Meeting')

                witness_blocks = []
                for activity in oral_evidence_activities:
                    time_str = format_time(activity.get('startDate'))
                    attendee_lis = []
                    for person in activity.get('attendees', []):
                        name = person.get('name')
                        orgs = person.get('organisations', [])
                        context = person.get('additionalContext')
                        if orgs:
                            attendee_lis.append(E.LI(f"{name} ({orgs[0].get('role')} at {orgs[0].get('name')})"))
                        elif context:
                            attendee_lis.append(E.LI(f"{name} ({context})"))
                        else:
                            attendee_lis.append(E.LI(name))
                    
                    if attendee_lis:
                        witness_blocks.append(
                            E.DIV(
                                E.DIV(time_str, class_="timestamp"),
                                E.UL(*attendee_lis),
                                style="margin-top: 15px; font-size: 0.9em;" # Keep specific activity sizing
                            )
                        )

                committee_blocks.append(create_meeting_element(display_title, link, witness_blocks))

        if c_news:
            committee_blocks.append(E.H2("News"))
            for item in c_news:
                url = item.get('url')
                if not url or not url.startswith('http'):
                    sanitised_name = sanitise_for_url(c_name)
                    sanitised_heading = sanitise_for_url(item.get('heading', ''))
                    url = f"https://committees.parliament.uk/committee/{item.get('source_committee_id')}/{sanitised_name}/news/{item.get('id')}/{sanitised_heading}/"
                committee_blocks.append(create_news_element(
                    item.get('heading'),
                    url,
                    item.get('teaser'),
                    format_date(item.get('datePublished'))
                ))

        committee_blocks.append(E.HR())


        committee_html = ''.join(
            html.tostring(block, pretty_print=True, method="html", encoding='unicode')
            for block in committee_blocks
        )

        all_segments.append(
            f'*|INTERESTED:Select Committees:{c_name}|*<div>\n{committee_html}\n</div>*|END:INTERESTED|*'
        )

    if all_segments:

        today = datetime.now()
        output_filename = today.strftime("%Y-%m-%d") + ".html"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        inner_content = '\n'.join(all_segments)

        logo_html = html.tostring(E.IMG(src="https://mcusercontent.com/80716ad2ad80186c9ad93a2a8/_thumbs/0fc811f6-71ce-a08b-4bee-21030083c8a5.png", alt="House of Commons Committees"), pretty_print=True, method="html", encoding='unicode')
        intro_html = html.tostring(E.P("Committee e-alerts contain information about committee news, publications and meetings from the previous day. They are sent out daily at 8am if there is new information."), pretty_print=True, method="html", encoding='unicode')

        full_html = (
            f'{CSS_STYLE}\n'
            '<div class="email-body">\n'
            f'{logo_html}'
            f'{intro_html}'
            f'{inner_content}'
            '</div>'
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    main()
