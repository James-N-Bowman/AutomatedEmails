import logging
from helpersMailChimp import *
from helpersCtteesAPI import *
import helpersCSVMapping

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main():
    # cttee_id = input("Committee id?").strip()
    # try:
    #     cttee_id = int(cttee_id)
    # except ValueError as e:
    #     logger.debug(f"Error: must enter integer value: {e}")
    #     return
    
    cttees = fetch_committees_dict('Select', '(HC) Public Standing Orders - Departmental', False)

    # if cttee_id in cttees:
    #     cttee_name = cttees[cttee_id]['name']
    #     logger.info(f"{cttee_name} found on committees API.")
    # else:
    #     logger.warning(f"{cttee_name} found on committees API.")
    #     return
    
    for cttee_id, cttee_value in cttees.items():
        cttee_name = cttee_value['name']
        interest = create_group_interest(cttee_name)
        interest_id = interest.get("id")
        helpersCSVMapping.update_mapping_CSV(cttee_id, cttee_name, interest_id) #campaign_id, interest_id)

if __name__ == "__main__":
    main()


