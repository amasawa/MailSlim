"""
Gmail client using IMAP with App Password authentication.
Supports: fetch headers, delete, archive.
"""

import imaplib
import email
from email.header import decode_header
import re


def decode_mime_header(raw):
    if raw is None:
        return ""
    parts = decode_header(raw)
    result = []
    for content, charset in parts:
        if isinstance(content, bytes):
            try:
                result.append(content.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                result.append(content.decode("utf-8", errors="replace"))
        else:
            result.append(content)
    return "".join(result)


def connect(imap_server, imap_port, username, password):
    """Connect and login via IMAP. Handles 126/Netease ID requirement."""
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(username, password)

    # 126/Netease requires ID command after login, otherwise SELECT is rejected
    if "126.com" in imap_server or "163.com" in imap_server or "yeah.net" in imap_server:
        tag = mail._new_tag()
        mail.send(tag + b' ID ("name" "IMAPClient" "version" "1.0")\r\n')
        while True:
            line = mail.readline()
            if line.startswith(tag):
                break

    return mail


def fetch_emails(mail):
    """Fetch all email headers from all folders. Returns list of email dicts."""
    status, folder_list = mail.list()
    folders_to_scan = []
    for f in folder_list:
        match = re.search(r'"[/.]" "?(.+?)"?\r?$', f.decode())
        if match:
            folder_name = match.group(1).strip('"')
            if "all mail" in folder_name.lower() or "allmail" in folder_name.lower():
                continue
            folders_to_scan.append(folder_name)

    all_emails = []
    for folder in folders_to_scan:
        try:
            status, _ = mail.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue
        except:
            continue

        status, messages = mail.search(None, "ALL")
        if status != "OK":
            continue

        msg_nums = messages[0].split()
        if not msg_nums:
            continue

        print(f"  [{folder}] {len(msg_nums)} emails, fetching headers...")

        chunk_size = 200
        for ci in range(0, len(msg_nums), chunk_size):
            chunk = msg_nums[ci:ci+chunk_size]
            nums_str = ",".join(n.decode() for n in chunk)
            try:
                status, response = mail.fetch(
                    nums_str,
                    "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE CONTENT-TYPE CONTENT-DISPOSITION)])"
                )
                if status != "OK":
                    continue
            except:
                continue

            i = 0
            while i < len(response):
                item = response[i]
                if isinstance(item, tuple) and len(item) == 2:
                    meta = item[0].decode() if isinstance(item[0], bytes) else str(item[0])
                    uid_match = re.match(r"(\d+)", meta)
                    uid = uid_match.group(1) if uid_match else "?"

                    header_bytes = item[1] if isinstance(item[1], bytes) else b""
                    try:
                        msg = email.message_from_bytes(header_bytes)
                    except:
                        i += 1
                        continue

                    subject = decode_mime_header(msg["Subject"])
                    from_raw = decode_mime_header(msg["From"])
                    date_str = msg["Date"] or ""

                    sender_match = re.search(r"<(.+?)>", from_raw)
                    sender_email = sender_match.group(1) if sender_match else from_raw
                    sender_name = from_raw.split("<")[0].strip().strip('"')

                    content_disp = msg.get("Content-Disposition") or ""
                    content_type = msg.get("Content-Type") or ""
                    has_attach = "attachment" in content_disp or "multipart/mixed" in content_type

                    all_emails.append({
                        "uid": uid,
                        "folder": folder,
                        "from": sender_email,
                        "from_name": sender_name,
                        "subject": subject,
                        "date": date_str,
                        "has_attachment": has_attach
                    })
                i += 1

    print(f"  Total fetched: {len(all_emails)}")
    return all_emails


def delete_emails(mail, folder_uids):
    """Delete emails by folder -> [uid] mapping. Returns (deleted, failed) counts."""
    deleted = 0
    failed = 0

    for folder, uids in folder_uids.items():
        print(f"  [{folder}] Deleting {len(uids)} emails...")
        try:
            status, _ = mail.select(f'"{folder}"')
            if status != "OK":
                failed += len(uids)
                continue
        except:
            failed += len(uids)
            continue

        batch_size = 100
        for i in range(0, len(uids), batch_size):
            batch = uids[i:i+batch_size]
            uid_set = ",".join(str(u) for u in batch)
            try:
                status, _ = mail.store(uid_set, "+FLAGS", "(\\Deleted)")
                if status == "OK":
                    deleted += len(batch)
                else:
                    failed += len(batch)
            except:
                failed += len(batch)
        mail.expunge()

    return deleted, failed


def archive_inbox(mail, before_date=None):
    """Archive all emails in INBOX (remove from inbox).
    before_date: optional, format 'DD-Mon-YYYY' e.g. '01-May-2026'. Only archive emails before this date.
    Returns count."""
    status, _ = mail.select("INBOX")
    if status != "OK":
        return 0

    if before_date:
        status, messages = mail.search(None, f'BEFORE {before_date}')
    else:
        status, messages = mail.search(None, "ALL")
    msg_nums = messages[0].split()
    total = len(msg_nums)

    if total == 0:
        return 0

    archived = 0
    batch_size = 200
    for i in range(0, total, batch_size):
        batch = msg_nums[i:i+batch_size]
        msg_set = b",".join(batch).decode()
        try:
            status, _ = mail.store(msg_set, "+FLAGS", "(\\Deleted)")
            if status == "OK":
                archived += len(batch)
        except:
            for num in batch:
                try:
                    mail.store(num.decode(), "+FLAGS", "(\\Deleted)")
                    archived += 1
                except:
                    pass

    mail.expunge()
    return archived
