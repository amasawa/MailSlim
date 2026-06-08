"""
Email Cleaner - Main entry point.

Usage (called by Claude or manually):
    python3 src/main.py fetch gmail
    python3 src/main.py fetch outlook
    python3 src/main.py delete gmail
    python3 src/main.py delete outlook
    python3 src/main.py archive gmail
    python3 src/main.py archive outlook --before 2026-02-03
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

import yaml

BASE_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(BASE_DIR))
from src.rules_engine import apply_rules
from src.excel_utils import export_candidates, load_approved


def load_config():
    with open(BASE_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


# ============================================================
# Gmail operations
# ============================================================

def fetch_gmail(config):
    from src.gmail_client import connect, fetch_emails

    mc = config["mailboxes"]["gmail"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    emails = fetch_emails(mail)
    mail.logout()

    candidates = apply_rules(emails)
    print(f"\nTotal: {len(emails)} | Delete candidates: {len(candidates)} | Kept: {len(emails) - len(candidates)}")

    with open(BASE_DIR / "emails.json", "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

    export_candidates(candidates, BASE_DIR / config["output"]["candidates_xlsx"])


def delete_gmail(config):
    from src.gmail_client import connect, delete_emails

    approved = load_approved(BASE_DIR / config["output"]["approved_xlsx"])
    if not approved:
        print("Nothing to delete.")
        return

    # Group by folder
    folder_uids = defaultdict(list)
    for em in approved:
        folder_uids[em["folder"]].append(em["uid"])

    mc = config["mailboxes"]["gmail"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    deleted, failed = delete_emails(mail, folder_uids)
    mail.logout()

    print(f"\nDeleted: {deleted} | Failed: {failed}")


def archive_gmail(config):
    from src.gmail_client import connect, archive_inbox

    mc = config["mailboxes"]["gmail"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    count = archive_inbox(mail)
    mail.logout()

    print(f"\nArchived: {count} emails from INBOX")


# ============================================================
# 126 Mail operations (IMAP, same as Gmail)
# ============================================================

def fetch_mail126(config):
    from src.gmail_client import connect, fetch_emails

    mc = config["mailboxes"]["mail126"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    emails = fetch_emails(mail)
    mail.logout()

    candidates = apply_rules(emails)
    print(f"\nTotal: {len(emails)} | Delete candidates: {len(candidates)} | Kept: {len(emails) - len(candidates)}")

    with open(BASE_DIR / "emails_126.json", "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

    export_candidates(candidates, BASE_DIR / "delete_candidates_126.xlsx")


def delete_mail126(config):
    from src.gmail_client import connect, delete_emails

    approved = load_approved(BASE_DIR / "approved_delete_126.xlsx")
    if not approved:
        print("Nothing to delete.")
        return

    folder_uids = defaultdict(list)
    for em in approved:
        folder_uids[em["folder"]].append(em["uid"])

    mc = config["mailboxes"]["mail126"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    deleted, failed = delete_emails(mail, folder_uids)
    mail.logout()

    print(f"\nDeleted: {deleted} | Failed: {failed}")


def archive_mail126(config):
    from src.gmail_client import connect, archive_inbox

    mc = config["mailboxes"]["mail126"]
    mail = connect(mc["imap_server"], mc["imap_port"], mc["username"], mc["password"])
    count = archive_inbox(mail)
    mail.logout()

    print(f"\nArchived: {count} emails from INBOX")


# ============================================================
# Outlook operations
# ============================================================

def fetch_outlook(config):
    from src.outlook_auth import get_access_token
    from src.outlook_client import fetch_emails

    token = get_access_token()
    emails = fetch_emails(token)

    candidates = apply_rules(emails)
    print(f"\nTotal: {len(emails)} | Delete candidates: {len(candidates)} | Kept: {len(emails) - len(candidates)}")

    with open(BASE_DIR / "emails_outlook.json", "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

    export_candidates(candidates, BASE_DIR / "delete_candidates_outlook.xlsx")


def delete_outlook(config):
    from src.outlook_auth import get_access_token
    from src.outlook_client import delete_emails

    approved = load_approved(BASE_DIR / "approved_delete_outlook.xlsx")
    if not approved:
        print("Nothing to delete.")
        return

    token = get_access_token()
    ids = [em["uid"] for em in approved]
    deleted, failed = delete_emails(token, ids)

    print(f"\nDeleted: {deleted} | Failed: {failed}")


def archive_outlook(config, before_date):
    from src.outlook_auth import get_access_token
    from src.outlook_client import archive_inbox_before

    token = get_access_token()
    cutoff = f"{before_date}T00:00:00Z"
    archived, failed = archive_inbox_before(token, cutoff)

    print(f"\nArchived: {archived} | Failed: {failed}")


# ============================================================
# CLI
# ============================================================

COMMANDS = {
    ("fetch", "gmail"): fetch_gmail,
    ("fetch", "outlook"): fetch_outlook,
    ("fetch", "126"): fetch_mail126,
    ("delete", "gmail"): delete_gmail,
    ("delete", "outlook"): delete_outlook,
    ("delete", "126"): delete_mail126,
    ("archive", "gmail"): archive_gmail,
    ("archive", "126"): archive_mail126,
}


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 src/main.py <action> <provider> [options]")
        print("  Actions: fetch, delete, archive")
        print("  Providers: gmail, outlook, 126")
        print("  Options: --before YYYY-MM-DD (for archive)")
        sys.exit(1)

    action = sys.argv[1]
    provider = sys.argv[2]
    config = load_config()

    if action == "archive" and provider == "outlook":
        before_date = "2026-02-03"  # default
        if "--before" in sys.argv:
            idx = sys.argv.index("--before")
            before_date = sys.argv[idx + 1]
        archive_outlook(config, before_date)
    elif (action, provider) in COMMANDS:
        COMMANDS[(action, provider)](config)
    else:
        print(f"Unknown command: {action} {provider}")
        sys.exit(1)


if __name__ == "__main__":
    main()
