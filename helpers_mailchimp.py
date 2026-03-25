import logging
import os
import sys

import requests

API_KEY = os.environ['API_KEY']
DATA_CENTRE = os.environ['DATA_CENTRE']
AUDIENCE_ID = os.environ['AUDIENCE_ID']
CAMPAIGN_FOLDER_ID = "5ed5be8d9a"

GROUP_ID = "2012540f09"
BASE_URL = f"https://{DATA_CENTRE}.api.mailchimp.com/3.0"
AUTH = ("jbanystring", API_KEY)  # Mailchimp uses HTTP Basic Auth

TIMEOUT  = 30
PAGE_SIZE = 1000  # use large pages to minimize round-trips

DEFAULT_FROM_NAME = "Committee e-alerts"
DEFAULT_REPLY_TO = "committeecorridor@email.parliament.uk"
DEFAULT_SUBJECT = "Committee e-alerts"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

# =========================
# GET, PUSH, PUT HELPERS
# =========================

def mailchimp_request(method, path, payload=None, params=None):
    url = BASE_URL + path
    logger.info("Fetching: %s", url)
    logger.debug(method, url, AUTH, payload, params or {}, TIMEOUT, sep="\n")
    response = requests.request(
        method,
        url,
        auth=AUTH,
        json=payload,
        params=params or {},
        timeout=TIMEOUT,
    )
    if not response.ok:
        logger.debug(f"{method.upper()} {path} failed:")
        logger.error(f"Status: {response.status_code} - Error: {response.text}")
        sys.exit(1)
    return response.json() if response.content else None

def mailchimp_get(path, params=None):
    return mailchimp_request("GET", path, params=params)

def mailchimp_post(path, payload=None):
    return mailchimp_request("POST", path, payload=payload)

def mailchimp_put(path, payload):
    return mailchimp_request("PUT", path, payload=payload)

# =========================
# FETCH HELPERS
# =========================

def fetch_all_tags(list_id):
    """GET /lists/{list_id}/tag-search with pagination (count/offset)."""
    tags = []
    offset = 0
    while True:
        data = mailchimp_get(f"/lists/{list_id}/tag-search", params={"count": PAGE_SIZE, "offset": offset})
        batch = data.get("tags", [])
        tags.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return tags

def fetch_all_campaigns():
    """GET /campaigns with pagination (count/offset)."""
    items = []
    offset = 0
    while True:
        data = mailchimp_get("/campaigns", params={"count": PAGE_SIZE, "offset": offset})
        batch = data.get("campaigns", [])
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return items


def fetch_interest_categories(list_id):
    """GET /lists/{list_id}/interest-categories (groups)."""
    cats = []
    offset = 0
    while True:
        data = mailchimp_get(f"/lists/{list_id}/interest-categories", params={"count": PAGE_SIZE, "offset": offset})
        batch = data.get("categories", [])
        cats.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return cats

def fetch_interests(list_id, interest_category_id):
    """GET /lists/{list_id}/interest-categories/{category_id}/interests."""
    interests = []
    offset = 0
    while True:
        data = mailchimp_get(
            f"/lists/{list_id}/interest-categories/{interest_category_id}/interests",
            params={"count": PAGE_SIZE, "offset": offset},
        )
        batch = data.get("interests", [])
        interests.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return interests


def fetch_all_campaign_folders():
    """GET /campaign-folders with pagination (count/offset)."""
    items = []
    offset = 0
    while True:
        # Mailchimp uses 'count' and 'offset' for pagination across most endpoints
        data = mailchimp_get("/campaign-folders", params={"count": PAGE_SIZE, "offset": offset})
        
        # The root key for this endpoint is 'folders'
        batch = data.get("folders", [])
        items.extend(batch)
        
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return items


def fetch_all_segments(list_id):
    """GET /lists/{list_id}/segments with pagination."""
    segs = []
    offset = 0
    while True:
        data = mailchimp_get(f"/lists/{list_id}/segments", params={"count": PAGE_SIZE, "offset": offset})
        batch = data.get("segments", [])
        segs.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return segs

# =========================
# LIST FOR ME HELPERS
# =========================

def list_all_tags():
    tags = fetch_all_tags(AUDIENCE_ID)
    print("# TAGS (id,name)")
    print("id,name")
    for t in tags:
        tag_id = t.get("id")
        name = (t.get("name") or "").replace('"', '""')
        print(f"{tag_id},\"{name}\"")
    print()


def list_all_campaigns():
    campaigns = fetch_all_campaigns()
    print("# CAMPAIGNS (id,title,subject_line,status)")
    print("id,title,subject_line,status")
    for c in campaigns:
        cid = c.get("id")
        settings = c.get("settings", {}) or {}
        title = (settings.get("title") or "").replace('"', '""')
        subj  = (settings.get("subject_line") or "").replace('"', '""')
        status = c.get("status") or ""
        print(f"{cid},\"{title}\",\"{subj}\",{status}")
    print()

def list_all_groups_and_interests():
    print("# GROUPS (category_id,category_title,interest_id,interest_name)")
    print("category_id,category_title,interest_id,interest_name")
    cats = fetch_interest_categories(AUDIENCE_ID)
    for cat in cats:
        cat_id = cat.get("id")
        cat_title = (cat.get("title") or "").replace('"', '""')
        interests = fetch_interests(AUDIENCE_ID, cat_id)
        if not interests:
            # still output category row with blanks for interests
            print(f"{cat_id},\"{cat_title}\",,")
        else:
            for i in interests:
                iid = i.get("id")
                iname = (i.get("name") or "").replace('"', '""')
                print(f"{cat_id},\"{cat_title}\",{iid},\"{iname}\"")
    print()

def list_all_segments():
    segs = fetch_all_segments(AUDIENCE_ID)
    print("# SEGMENTS (id,name,type)")
    print("id,name,type")
    for s in segs:
        sid = s.get("id")
        name = (s.get("name") or "").replace('"', '""')
        stype = s.get("type") or ""  # 'saved', 'static', 'fuzzy', etc. depends on account
        print(f"{sid},\"{name}\",{stype}")


def list_campaign_folders():
    folders = fetch_all_campaign_folders()
    
    if not folders:
        print("No campaign folders found.")
        return

    print(f"{'ID':<12} | {'NAME':<30}")
    print("-" * 45)
    for folder in folders:
        # Each folder object contains 'id' and 'name'
        print(f"{folder['id']:<12} | {folder['name']:<30}")

# =========================
# CHECK HELPERS
# =========================

def check_interest_occupancy(interest_id):
    """
    Checks if a specific interest has any contacts attached to it.
    Returns the count of subscribers.
    """

    path = f"/lists/{AUDIENCE_ID}/interest-categories/{GROUP_ID}/interests/{interest_id}"
    
    # Fetch the interest details
    interest_data = mailchimp_get(path)
    
    if interest_data:
        count = int(interest_data.get("subscriber_count", 0))
        name = interest_data.get("name", "Unknown Interest")
        
        if count > 0:
            logger.info(f"Success: The interest '{name}' has {count} contact(s).")
        else:
            logger.info(f"Notice: The interest '{name}' exists but has 0 contacts.")
            
        return count
    return 0

# =========================
# CREATION HELPERS
# =========================

def create_group_interest(name):
    """
    Adds an individual interest (option) inside a Group Category.
    
    :param audience_id: The ID of the audience/list
    :param group_id: The ID of the interest category (group) returned from create_group()
    :param name: The name of the interest option (e.g. "Football", "Basketball")
    """
    interest = mailchimp_post(
        f"/lists/{AUDIENCE_ID}/interest-categories/{GROUP_ID}/interests",
        {
            "name": name
        }
    )
    return interest

def create_template(html_content):
    """
    Creates a MailChimp template containing the HTML content.

    Using a template rather than the campaign content 'html' field is necessary
    because the content endpoint runs the HTML through a sanitiser that strips
    *|IF:INTERESTS:id|* merge tags before they can be evaluated. The templates
    endpoint does not apply this sanitiser, so merge tags are preserved intact.

    :param html_content: Full HTML string including *|IF:INTERESTS:id|* blocks.
    :returns: The created template's ID.
    """
    # The template HTML must be a complete document with a single mc:edit region.
    # MailChimp injects the content of that region verbatim, preserving merge tags.
    template_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<div mc:edit="body">
{html_content}
</div>
</body>
</html>"""

    payload = {
        "name": "e-alert template",
        "html": template_html
    }
    response = mailchimp_post("/templates", payload)
    template_id = response["id"]
    logger.info(f"Created template: {template_id}")
    return template_id


def delete_template(template_id):
    """Deletes a MailChimp template by ID. Used to clean up after sending."""
    mailchimp_request("DELETE", f"/templates/{template_id}")
    logger.info(f"Deleted template: {template_id}")


def create_and_send_campaign(
    interest_ids,
    campaign_title,
    html_content,
    subject=DEFAULT_SUBJECT,
    from_name=DEFAULT_FROM_NAME,
    reply_to=DEFAULT_REPLY_TO
):
    """
    Creates a single campaign targeted at any subscriber who belongs to at least
    one of the supplied interest IDs, sets the HTML content via a template
    (to preserve *|IF:INTERESTS:id|* merge tags), and sends immediately.

    The segment uses 'interestcontains' with all interest IDs so that the campaign
    is only delivered to subscribers with at least one matching interest, preventing
    blank emails being sent to unmatched subscribers.

    :param interest_ids: List of MailChimp interest IDs to target (match any one).
    :param campaign_title: Title shown in the MailChimp UI.
    :param html_content: Full HTML body string containing per-committee
                         *|IF:INTERESTS:id|* conditional blocks.
    :param subject: Email subject line.
    :param from_name: Sender display name.
    :param reply_to: Email reply-to address.
    """

    # 1. Create a temporary template to carry the HTML content.
    #    This bypasses the campaign content sanitiser that strips merge tags.
    template_id = create_template(html_content)

    # 2. Setup campaign settings
    settings = {
        "title": campaign_title,
        "subject_line": subject,
        "from_name": from_name,
        "reply_to": reply_to
    }
    if CAMPAIGN_FOLDER_ID:
        settings["folder_id"] = CAMPAIGN_FOLDER_ID

    # 3. CREATE the campaign, referencing the template.
    #    The segment uses 'interestcontains' with all interest IDs so only
    #    subscribers matched to at least one committee receive the email.
    payload = {
        "type": "regular",
        "recipients": {
            "list_id": AUDIENCE_ID,
            "segment_opts": {
                "match": "any",
                "conditions": [
                    {
                        "condition_type": "Interests",
                        "field": f"interests-{GROUP_ID}",
                        "op": "interestcontains",
                        "value": interest_ids
                    }
                ]
            }
        },
        "settings": settings
    }

    campaign = mailchimp_post("/campaigns", payload)
    campaign_id = campaign["id"]
    logger.info(f"Created campaign: {campaign_id}")

    # 4. SET THE CONTENT from the template
    mailchimp_put(
        f"/campaigns/{campaign_id}/content",
        {"template": {"id": template_id}}
    )
    logger.info(f"Template {template_id} applied to campaign {campaign_id}")

    # 5. SEND the campaign
    mailchimp_post(f"/campaigns/{campaign_id}/actions/send")
    print(f"Success: '{campaign_title}' sent to {len(interest_ids)} interest group(s)!")

    # 6. Clean up the temporary template
    delete_template(template_id)

    return campaign_id

# =========================
# RECALC HELPERS
# =========================

def recalculate_campaign_recipients (campaign_id):

    # 1. Fetch the current campaign configuration
    campaign = mailchimp_request("GET", f"/campaigns/{campaign_id}")

    # 2. Extract the recipient settings
    # This contains the 'segment_opts' which holds your Interest targeting
    recipient_settings = campaign.get("recipients", {})

    # 3. PATCH the campaign with its own recipient settings
    # This mimics clicking "Review Segment" in the UI
    payload = {
        "recipients": recipient_settings
    }

    refreshed_campaign = mailchimp_request(
        method="PATCH",
        path=f"/campaigns/{campaign_id}",
        payload=payload
    )

    print("Campaign recipients refreshed.")
