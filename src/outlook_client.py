"""
Outlook/Office 365 client using REST API v2.0.

Authentication:
  Uses outlook_auth module which handles two flows:
  1. Silent refresh (automatic) - uses cached refresh token from OWA's client ID
  2. Browser login (fallback) - opens Chrome for manual login + MFA

  After first browser login, the refresh token is cached and subsequent calls
  are fully automated (no user interaction needed). Refresh tokens last ~90 days.
"""

import requests
from src.outlook_auth import get_access_token

API_BASE = "https://outlook.office.com/api/v2.0/me"


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# Fetch
# ============================================================

def fetch_emails(token=None):
    """Fetch all emails from all folders. Returns list of email dicts."""
    if token is None:
        token = get_access_token()

    headers = _headers(token)

    print("Fetching mail folders...")
    r = requests.get(f"{API_BASE}/mailfolders?$top=100", headers=headers)
    if r.status_code != 200:
        print(f"Failed to get folders: {r.status_code}")
        return []

    folders = r.json().get('value', [])
    print(f"Found {len(folders)} folders")

    all_emails = []
    for folder in folders:
        folder_name = folder['DisplayName']
        folder_id = folder['Id']
        total = folder.get('TotalItemCount', 0)

        if total == 0:
            continue

        print(f"  [{folder_name}] {total} emails, fetching...")

        skip = 0
        batch_size = 50
        while skip < total:
            url = (f"{API_BASE}/mailfolders/{folder_id}/messages"
                   f"?$select=Subject,From,ReceivedDateTime,HasAttachments"
                   f"&$top={batch_size}&$skip={skip}"
                   f"&$orderby=ReceivedDateTime desc")

            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                print(f"    Error at skip={skip}: {r.status_code}")
                break

            msgs = r.json().get('value', [])
            if not msgs:
                break

            for msg in msgs:
                sender_email = ""
                sender_name = ""
                if msg.get('From') and msg['From'].get('EmailAddress'):
                    sender_email = msg['From']['EmailAddress'].get('Address', '')
                    sender_name = msg['From']['EmailAddress'].get('Name', '')

                all_emails.append({
                    "uid": msg.get('Id', ''),
                    "folder": folder_name,
                    "from": sender_email,
                    "from_name": sender_name,
                    "subject": msg.get('Subject', ''),
                    "date": msg.get('ReceivedDateTime', ''),
                    "has_attachment": msg.get('HasAttachments', False)
                })

            skip += batch_size

        print(f"    done ({min(skip, total)}/{total})")

    print(f"  Total fetched: {len(all_emails)}")
    return all_emails


# ============================================================
# Delete
# ============================================================

def delete_emails(token=None, email_ids=None):
    """Delete emails by message ID list. Returns (deleted, failed) counts."""
    if token is None:
        token = get_access_token()

    headers = _headers(token)
    deleted = 0
    failed = 0

    for i, msg_id in enumerate(email_ids):
        url = f"{API_BASE}/messages/{msg_id}"
        try:
            r = requests.delete(url, headers=headers)
            if r.status_code in (200, 204):
                deleted += 1
            else:
                failed += 1
        except:
            failed += 1

        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{len(email_ids)} (deleted: {deleted}, failed: {failed})")

    return deleted, failed


# ============================================================
# Archive
# ============================================================

def archive_inbox_before(token=None, cutoff_date=None):
    """Move inbox emails before cutoff_date to Archive folder.
    cutoff_date: ISO format string e.g. '2026-02-03T00:00:00Z'
    Returns (archived, failed) counts.
    """
    if token is None:
        token = get_access_token()

    headers = _headers(token)

    # Find Archive folder
    r = requests.get(f"{API_BASE}/mailfolders?$top=100", headers=headers)
    folders = r.json().get('value', [])
    archive_id = None
    for f in folders:
        if f['DisplayName'] in ('Archive', 'archive', '\u5b58\u6863'):
            archive_id = f['Id']
            break

    if not archive_id:
        print("ERROR: Archive folder not found!")
        return 0, 0

    # Get emails before cutoff
    print(f"Fetching inbox emails before {cutoff_date[:10]}...")
    to_archive = []
    skip = 0
    batch_size = 50

    while True:
        url = (f"{API_BASE}/mailfolders/inbox/messages"
               f"?$filter=ReceivedDateTime lt {cutoff_date}"
               f"&$select=Id,Subject,ReceivedDateTime"
               f"&$top={batch_size}&$skip={skip}"
               f"&$orderby=ReceivedDateTime desc")

        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            break

        msgs = r.json().get('value', [])
        if not msgs:
            break

        to_archive.extend(msgs)
        skip += batch_size
        print(f"  Found {len(to_archive)} emails so far...")

    print(f"Total to archive: {len(to_archive)}")

    if not to_archive:
        return 0, 0

    archived = 0
    failed = 0

    for i, msg in enumerate(to_archive):
        url = f"{API_BASE}/messages/{msg['Id']}/move"
        try:
            r = requests.post(url, headers=headers, json={"DestinationId": archive_id})
            if r.status_code in (200, 201):
                archived += 1
            else:
                failed += 1
        except:
            failed += 1

        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{len(to_archive)} (archived: {archived}, failed: {failed})")

    return archived, failed
