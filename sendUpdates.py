import csv
from datetime import datetime, timedelta
import os

from helpersMailChimp import *

MAPPING_FILE = 'mapping.csv'
HTML_DIR = 'docs'

def main():
    if not os.path.exists(MAPPING_FILE):
        print(f"Error: {MAPPING_FILE} not found.")
        return

    # 1. Read all interest IDs from the mapping CSV
    all_interest_ids = dict()
    with open(MAPPING_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header row
        for row in reader:
            # Ensure row has enough columns (Cttee ID, Name, interest_id)
            if not row or len(row) < 3:
                continue
            committee_name = row[1].strip()
            interest_id = row[2].strip()
            if committee_name and interest_id:
                all_interest_ids[interest_id] = committee_name

    if not all_interest_ids:
        print("No interest IDs found in mapping CSV. Aborting.")
        return

    # 2. Check that at least one interest has subscribers — no point sending
    #    a campaign if nobody in the audience is signed up to any committee.
    total_subscribers = sum(check_interest_occupancy(iid) for iid in all_interest_ids)
    if total_subscribers == 0:
        print("No subscribers found across all interests. Aborting.")
        return

    # 3. Locate yesterday's HTML file (produced by the HTML-generation script)
    yesterday = datetime.now() - timedelta(days=3)
    html_filename = yesterday.strftime("%Y-%m-%d") + ".html"
    html_file_path = os.path.join(HTML_DIR, html_filename)

    if not os.path.exists(html_file_path):
        print(f"No HTML file found at {html_file_path}. Nothing to send.")
        return

    with open(html_file_path, 'r', encoding='utf-8') as hf:
        html_body = hf.read()

    # 3b. Narrow the interest ID list to only those actually referenced in the
    #     HTML — committees with no content that day won't have an
    #     *|IF:INTERESTS:id|* block, so there's no reason to target their subscribers.
    active_interest_ids = [iid for iid, cn in all_interest_ids.items() if f'*|INTERESTED:Select Committees:{cn}|*' in html_body]

    if not active_interest_ids:
        print("No active interest IDs found in today's HTML. Nothing to send.")
        return

    # 4. Build a single campaign title using today's date/time
    date_and_time = str(datetime.today()-timedelta(2))[0:16]
    campaign_title = f"E-alert {date_and_time}"

    # 5. Create and send one campaign targeted at anyone subscribed to
    #    at least one of the committee interest groups
    try:
        create_and_send_campaign(
            interest_ids=active_interest_ids,
            campaign_title=campaign_title,
            html_content=html_body,
            subject=DEFAULT_SUBJECT,
            from_name=DEFAULT_FROM_NAME,
            reply_to=DEFAULT_REPLY_TO
        )
    except Exception as e:
        print(f"Error sending campaign: {e}")

if __name__ == "__main__":
    main()