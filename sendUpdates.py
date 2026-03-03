from datetime import datetime
import os

from helpersCSVMapping import *
from helpersMailChimp import *

MAPPING_FILE = 'mapping.csv'
HTMLS_DIR = 'HTMLs'

def main():
    if not os.path.exists(MAPPING_CSV_FILEPATH):
        print(f"Error: {MAPPING_CSV_FILEPATH} not found.")
        return

    with open(MAPPING_CSV_FILEPATH, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header row
        
        for row in reader:
            # Ensure row has enough columns (Cttee ID, Name, Campaign ID)
            if not row or len(row) < 3:
                continue
            
            cttee_id = row[0].strip()
            cttee_name = row[1].strip()
            interest_id = row[2].strip()

            if check_interest_occupancy(interest_id)==0:
                logger.info(f"No contacts found for this interest so nobody to send to. Skipping.")

            date_and_time = str(datetime.today())[0:16]
            campaign_title = f"{cttee_name} {date_and_time}"
            
            # Check if an HTML file exists for this committee
            html_file_path = os.path.join(HTMLS_DIR, f"{cttee_id}.html")
            
            if os.path.exists(html_file_path):
                print(f"Found content for Committee {cttee_id}. Preparing to send...")
                
                with open(html_file_path, 'r', encoding='utf-8') as hf:
                    html_body = hf.read()
                
                try:
                    create_and_send_weekly_email(
                        interest_id, 
                        campaign_title, 
                        html_body, 
                        subject=DEFAULT_SUBJECT, 
                        from_name=DEFAULT_FROM_NAME, 
                        reply_to=DEFAULT_REPLY_TO
                    )
                except Exception as e:
                    print(f"Error sending campaign for committee {cttee_id}: {e}")
            else:
                # If no HTML file was created by the previous script (no new data), we skip
                print(f"No new updates for Committee {cttee_id} (No HTML file). Skipping.")

if __name__ == "__main__":
    main()
