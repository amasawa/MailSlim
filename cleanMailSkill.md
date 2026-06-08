---
name: email_cleaner
summary: Clean multiple mailboxes by identifying safe-to-delete emails, exporting a review list, and deleting only approved emails.
description: Use this skill when the user wants to clean accumulated emails from Gmail, Outlook/University mailbox, or 126 Mail. Supports two authentication flows depending on provider.
---

# Email Cleaner Skill

## Goal

Help the user clean multiple mailboxes by applying rule-based filtering, generating a reviewable Excel list, and executing deletion only after approval.

Supported mailboxes:
- **Gmail** - via IMAP with App Password (fully automated)
- **Outlook / Office 365** - via browser login + REST API (semi-automated, see below)
- **126 Mail** - via IMAP with authorization code (fully automated)

## Safety Rules

- Do NOT archive emails unless explicitly asked.
- Do NOT reply to or send emails.
- Do NOT delete anything without manual approval.
- Not Delete (whitelist) rules always take priority over Delete rules.

---

## Architecture

```
mail/
├── config.yaml              # Mailbox credentials & settings
├── rules.md                 # Human-readable deletion rules
├── cleanMailSkill.md        # This skill file
├── src/
│   ├── rules_engine.py      # Shared rule matching logic (whitelist > delete)
│   ├── excel_utils.py       # Excel import/export for candidate lists
│   ├── gmail_client.py      # Gmail IMAP: connect, fetch, delete, archive
│   ├── outlook_auth.py      # Outlook auth: persistent Chrome session + headless refresh
│   ├── outlook_client.py    # Outlook REST API operations (fetch, delete, archive)
│   └── main.py              # CLI entry point for all operations
└── output files/
    ├── emails.json                   # All fetched emails (Gmail)
    ├── emails_outlook.json           # All fetched emails (Outlook)
    ├── delete_candidates.xlsx        # Generated candidates for review
    ├── approved_delete.xlsx          # User-approved deletion list
    ├── delete_candidates_outlook.xlsx
    └── approved_delete_outlook.xlsx
```

---

## Provider Authentication

### Gmail (IMAP)
- Uses App Password for IMAP authentication
- Fully automated - no user interaction needed during execution
- Config: `imap_server`, `imap_port`, `username`, `password` (App Password)

### Outlook / Office 365 (Persistent Chrome Session + REST API)
- **Cannot use standard IMAP** - university tenants block basic auth
- **Cannot use standard OAuth2** - tenants restrict app registrations and public client IDs
- **Cannot use refresh token exchange** - OWA tokens are SPA-type, only redeemable via browser CORS flow
- **Solution**: Persistent Chrome profile with headless auto-refresh
  1. First time: user logs in via visible Chrome (with MFA), session cookies saved to `.chrome_profile/`
  2. Subsequent: headless Chrome loads OWA with saved cookies -> auto-login -> extract token from localStorage
  3. Session lasts ~30 days. If expired, auto-falls back to visible browser for re-auth
- **Claude Code can call Outlook operations directly** - no user interaction needed after initial login
- API base: `https://outlook.office.com/api/v2.0/me`
- Key API notes:
  - Use `ReceivedDateTime` (NOT `DateTimeReceived`)
  - Well-known folder names work: `inbox`, `drafts`, etc.
  - `$filter`, `$select`, `$orderby`, `$top`, `$skip` supported
  - `$filter`, `$select`, `$orderby`, `$top`, `$skip` supported

---

## Workflow

### Step 1: Fetch & Identify

Claude runs the appropriate fetch command:

```bash
# Gmail
python3 src/main.py fetch gmail

# Outlook (opens browser, user logs in manually)
python3 src/main.py fetch outlook
```

This produces `delete_candidates[_outlook].xlsx` with columns:
`Approve (Y/N) | Folder | From | From Name | Subject | Date | Reason | UID`

### Step 2: Review

Claude reads the Excel file and helps the user spot false positives. Key checks:
- Job offers / employment emails containing "offer" keyword -> KEEP
- Conference notifications (not review invitations) from noreply addresses -> KEEP
- Session chair / PC invitations -> KEEP
- Paper submission results from exordo/CMT -> KEEP
- Archive folder emails -> KEEP (do not delete)

Claude removes false positives and saves as `approved_delete[_outlook].xlsx`.
If new patterns emerge, update `rules.md` and `src/rules_engine.py` accordingly.

### Step 3: Delete

```bash
# Gmail
python3 src/main.py delete gmail

# Outlook (opens browser again for fresh token)
python3 src/main.py delete outlook
```

### Step 4: Archive (optional)

```bash
# Gmail - archive all inbox
python3 src/main.py archive gmail

# Outlook - archive inbox emails before a date
python3 src/main.py archive outlook --before 2026-02-03
```

---

## Outlook: Automatic After First Login

After the user completes one-time browser login (with MFA), Claude Code can directly run
all Outlook operations without user interaction:

```bash
# These all work automatically via headless Chrome session
python3 src/main.py fetch outlook
python3 src/main.py delete outlook
python3 src/main.py archive outlook --before 2026-02-03
```

If the session expires (~30 days), the script auto-falls back to a visible browser.
In that case, tell the user to run the command with `!` prefix for interactive login.

---

## Lessons Learned

1. University Office 365 tenants heavily restrict OAuth - don't waste time trying different client IDs
2. OWA's refresh tokens are SPA-type and cannot be exchanged via MSAL `acquire_token_by_refresh_token`
3. Persistent Chrome profile (`--user-data-dir`) preserves session cookies, enabling headless auto-login
4. Outlook REST API v2.0 property names differ from Graph API (e.g., `ReceivedDateTime` vs `receivedDateTime`)
5. Gmail IMAP: fetch headers only (not RFC822) for speed - batch with comma-separated message numbers
6. Login detection: check URL with `startswith()` not `in`, because OAuth redirect URLs contain the target URL as a parameter
7. Rule engine: whitelist (Not Delete) must always be checked BEFORE delete rules
