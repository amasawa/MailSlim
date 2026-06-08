# MailSlim

A Claude Code (CLI) driven email cleaning agent for researchers. Automatically log into multiple mailboxes, apply rule-based filtering, and batch-delete junk.

## Project Structure

```
MailSlim/
├── config.yaml           # Your credentials (git-ignored)
├── config.example.yaml   # Template
├── rules.md              # Delete / keep rules
├── cleanMailSkill.md     # Claude Code skill definition
└── src/                  # Source code
```

- **`config.yaml`** — Fill in your email credentials. Never committed.
- **`rules.md`** — Rules for what to delete and what to keep. Structured for both humans and LLMs to understand.

## TODO List

- [x] Auto-login: Gmail, Outlook, 126
- [x] LLM-driven batch deletion

## Property 1: Login & Authentication

### Supported Providers

| Provider | Protocol | Auth Method |
|----------|----------|-------------|
| Gmail | IMAP | App Password ([generate here](https://myaccount.google.com/apppasswords)) |
| Outlook / Office 365 | REST API | Persistent Chrome session (see below) |
| 126 / 163 Mail | IMAP | Authorization code (授权码) |

### Outlook: Why Chrome?

University/enterprise tenants often block IMAP basic auth, restrict OAuth2 app registrations, and issue SPA-only tokens. MailSlim works around this by launching a real Chrome browser: you log in once with MFA, cookies are saved, and subsequent runs use headless Chrome to silently extract a fresh token. Session lasts ~30 days.

### 126 Mail: Setup

1. Enable IMAP in web settings (Settings → POP3/SMTP/IMAP)
2. Generate an authorization code (授权码)
3. Enable "expose all folders to IMAP" (将所有邮件文件夹暴露给IMAP)

## Property 2: LLM-Driven Batch Deletion

### Workflow

```
fetch  →  generate candidate list (Excel)  →  manual review & approval  →  CC delete  →  CC archive (optional)
```

```bash
python3 src/main.py fetch <provider>       # Generates delete_candidates.xlsx
python3 src/main.py delete <provider>      # Deletes approved emails
python3 src/main.py archive <provider>     # Archives old emails
```

Providers: `gmail`, `outlook`, `126`

### Rules (`rules.md`)

Two sections: **Delete** and **Not Delete**. Whitelist always wins.

**Delete** — by keyword (`unsubscribe`, `promotion`...), sender pattern (`noreply@*`...), category (social notifications, verification codes...), specific senders (LinkedIn, Uber...)

**Not Delete** — `.edu` domains, academic platforms (OpenReview, Springer, arXiv, top conferences...), emails with attachments, invoices, paper submissions

To add rules: edit `rules.md` + the corresponding list in `src/rules_engine.py`.
