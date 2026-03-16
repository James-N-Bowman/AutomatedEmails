import csv
import os

MAPPING_CSV_FILEPATH = 'mapping.csv'

def check_CSV_for_duplicates(cttee_id: int, interest_id: str) -> bool:
    """
    Checks whether any of the three values already exist in their respective
    columns in an existing CSV file. Also verifies the file can be opened for
    writing.

    Returns True if the entry can safely be written (no duplicates found),
    False if a duplicate exists or the file cannot be accessed.

    Args:
        cttee_id    : Committee ID (integer).
        campaign_id : Campaign ID (string).
        interest_id : Interest ID (string).
    """

    # Check the file can be opened for writing
    try:
        with open(MAPPING_CSV_FILEPATH, "a", newline="") as f:
            pass  # just test write access
    except OSError as e:
        print(f"Error: File '{MAPPING_CSV_FILEPATH}' cannot be opened for writing: {e}")
        return False

    # Read existing rows
    try:
        with open(MAPPING_CSV_FILEPATH, "r", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except OSError as e:
        print(f"Error: Could not read file '{MAPPING_CSV_FILEPATH}': {e}")
        return False

    # Skip header row when checking for duplicates
    data_rows = rows[1:] if rows else []
    if len(data_rows)==0:
        return False

    for row in data_rows:

        if len(row) < 3:
            continue  # skip malformed rows

        try:
            if int(row[0]) == cttee_id:
                print(f"Error: cttee_id '{cttee_id}' already exists in the file.")
                return True
        except ValueError:
            pass  # non-integer in column; skip comparison

        if row[2] == interest_id:
            print(f"Error: interest_id '{interest_id}' already exists in the file.")
            return True

    return False

def create_mapping_CSV ():
    """
    If the file does not exist, creates it with a header row then writes the new
    row. 
    """

    file_exists = os.path.exists(MAPPING_CSV_FILEPATH)

    if not file_exists:
        try:
            with open(MAPPING_CSV_FILEPATH, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["cttee_id", "cttee_name", "campaign_id", "interest_id"])
            print(f"Created '{MAPPING_CSV_FILEPATH}' and wrote new row successfully.")
        except OSError as e:
            print(f"Error: Could not create file at '{MAPPING_CSV_FILEPATH}': {e}")
        return    

def write_to_mapping_CSV(cttee_id: int, cttee_name: str, interest_id: str) -> None:
    """
    Writes a new row (cttee_id, campaign_id, interest_id) to a CSV file.

    Args:
        cttee_id    : Committee ID (integer).
        campaign_id : Campaign ID (string).
        interest_id : Interest ID (string).
    """

    try:
        with open(MAPPING_CSV_FILEPATH, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([cttee_id, cttee_name, interest_id])
        print(f"Row written successfully to '{MAPPING_CSV_FILEPATH}'.")
    except OSError as e:
        print(f"Error: Could not write to file '{MAPPING_CSV_FILEPATH}': {e}")


def fetch_cttee_ids_from_mapping_CSV ():
    with open('mapping.csv', mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header row
            
        # Extract IDs from the first column
        committee_ids = {int(row[0]) for row in reader if row}
        return(committee_ids)

def update_mapping_CSV(cttee_id: int, cttee_name: str, interest_id: str) -> None:
    """
    Writes a new row (cttee_id, campaign_id, interest_id) to a CSV file.

    - If the file does not exist, creates it with a header row.
    - If the file exists but cannot be opened for writing, reports the problem and returns.
    - Before writing to an existing file, checks that none of the three values already
      exist in their respective columns; if a duplicate is found, reports and returns.
    - Otherwise, appends the new row.

    Args:
        cttee_id    : Committee ID (integer).
        campaign_id : Campaign ID (string).
        interest_id : Interest ID (string).
    """
    create_mapping_CSV()

    if check_CSV_for_duplicates(cttee_id, interest_id):
        return

    write_to_mapping_CSV(cttee_id, cttee_name, interest_id)