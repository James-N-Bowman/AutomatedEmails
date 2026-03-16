import json
import logging
import urllib.request
from urllib.error import URLError

CTTEE_API_BASE_URL = "https://committees-api.parliament.uk/api/"
PAGE_SIZE = 30

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def fetch_committees_dict(committeeCategory:str = None, allowed_cttee_types:list = None, allow_subs:bool = False) -> dict:
    """
    Fetch committee data from the Parliament API.

    Returns:
        Dictionary with committee IDs as keys and committee data as values,
        filtered to Commons committees only.
    """
    base_url = f"{CTTEE_API_BASE_URL}Committees?ShowOnWebsiteOnly=true&Take={PAGE_SIZE}"
    if committeeCategory == None:
        pass 
    elif committeeCategory in ['Select', 'General', 'Other']:
        base_url += f'&CommitteeCategory={committeeCategory}'
    else:
        logging.error('Committee category not recognised.')
    committees = {}
    skip = 0
    total_results = 1

    while skip < total_results:
        url = f"{base_url}&Skip={skip}"
        logger.debug("Fetching: %s", url)

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
        except URLError as e:
            raise RuntimeError(f"Failed to fetch committees from API: {e}") from e

        total_results = data["totalResults"]
        items = data["items"]

        if not items:
            logger.warning("Received empty page at skip=%d, stopping early.", skip)
            break  # Safeguard against empty pages causing infinite loops

        for item in items:
            skip += 1

            cttee_types = item.get('committeeTypes')
            if not any(ct.get('name') in allowed_cttee_types for ct in cttee_types):
                continue

            if item.get("house") != "Commons":
                continue

            if allow_subs == False and item.get('parentCommittee') != None:
                continue

            item_id = item.pop("id")
            committees[item_id] = item


    logger.info("Fetched %d Commons committees (total results reported: %d).", len(committees), total_results)
    return committees

def list_committees(allowed_committee_category:str=None, allowed_cttee_types:list = None, allow_subs:bool = False) -> dict:
    cttees = fetch_committees_dict(allowed_committee_category, allowed_cttee_types, allow_subs)
    for cttee_id, cttee_value in cttees.items():
        print(cttee_id, cttee_value.get('name'), sep="   ")



    