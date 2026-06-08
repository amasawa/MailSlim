"""
Shared rule engine for email deletion/retention decisions.
Rules are defined here in code, synced with rules.md.
"""

import re

# ============================================================
# Delete Rules
# ============================================================

DELETE_KEYWORDS = [
    "unsubscribe", "promotion", "sale", "discount", "coupon",
    "deal", "newsletter", "marketing"
]

DELETE_SENDER_PATTERNS = [
    r"^noreply@", r"^no-reply@", r"^notifications@",
    r"^marketing@", r"^promo@"
]

DELETE_SUBJECT_KEYWORDS = [
    "liked your", "started following", "new follower", "friend request",
    "commented on", "mentioned you", "tagged you",
    "verification code", "verify your", "otp", "password reset",
    "reset your password", "security code",
    "your package", "shipment", "tracking number", "out for delivery",
    "has been delivered", "shipping confirmation",
    "invitation to review", "review request", "referee request",
    "invited to review", "peer review invitation"
]

DELETE_SENDER_NAMES = [
    "alphaxiv",
    "ieee membership", "ieee enotice", "ieee-hkn",
    "ieee xplore team", "ieee spectrum",
    "starbucks",
    "intechopen",
    "slideslive",
    "trip.com",
    "linkedin",
    "afterpay",
    "uber.com",
    "world-comp.org",
    "flybuys",
    "bearabeara",
    "fun-lab.com",
    "funlab",
    "strike@email",
    "messaging.hsbc",
    "notification.hsbc",
    "aquarianpearls",
    "divcom.net.au",
    "insideapple.apple.com",
    "worlds4.co.uk",
    "iccvais.com",
    "fhysxq.top",
    "alsobro.com",
    "kuajing@service.netease.com",
    "activatefit.gym",
    "flychinaeastern",
    "ceair.com",
]

# These senders should be deleted even if they have attachments (override whitelist)
BLACKLIST_OVERRIDE_ATTACHMENT = [
    "iccvais.com",
    "fhysxq.top",
    "alsobro.com",
    "kuajing@service.netease.com",
]

# ============================================================
# Not Delete (Whitelist) Rules - takes priority over Delete
# ============================================================

WHITELIST_DOMAINS = ["sydney.edu.au", "uni.sydney.edu.au"]

WHITELIST_DOMAIN_PATTERNS = [r"\.edu(?:\.[a-z]{2,})?$"]

WHITELIST_SENDER_NAMES = ["wanchunliu", "longbingcao", "chairingtool.com", "msr-cmt.org"]

WHITELIST_PLATFORM_NAMES = [
    "openreview",
    "springer", "nature",
    "elsevier", "sciencedirect",
    "wiley",
    "ieee",
    "acm", "dl.acm.org",
    "mdpi",
    "arxiv",
    "aaai", "neurips", "nips", "icml", "iclr",
    "cvpr", "eccv", "iccv", "emnlp", "acl"
]

WHITELIST_SUBJECT_KEYWORDS = [
    "invoice", "receipt", "payment", "billing", "statement", "tax",
    "submission", "acceptance", "accepted", "rejected", "rejection",
    "camera-ready", "camera ready", "final version",
    "registration", "author notification"
]


def _is_blacklist_override(sender_email, sender_name):
    """Check if sender is in the blacklist that overrides attachment whitelist."""
    combined = sender_email.lower() + " " + sender_name.lower()
    for pattern in BLACKLIST_OVERRIDE_ATTACHMENT:
        if pattern in combined:
            return True
    return False


def check_not_delete(sender_email, sender_name, subject, has_attachment):
    """Return True if email should NOT be deleted (whitelist takes priority)."""
    sender_lower = sender_email.lower()
    sender_name_lower = sender_name.lower()
    subject_lower = subject.lower()

    # Blacklist override: these senders are never whitelisted
    if _is_blacklist_override(sender_email, sender_name):
        return False

    for domain in WHITELIST_DOMAINS:
        if domain in sender_lower:
            return True

    for pattern in WHITELIST_DOMAIN_PATTERNS:
        if re.search(pattern, sender_lower):
            return True

    for name in WHITELIST_SENDER_NAMES:
        if name in sender_lower or name in sender_name_lower:
            return True

    combined = sender_lower + " " + sender_name_lower
    for name in WHITELIST_PLATFORM_NAMES:
        if name in combined:
            return True

    if has_attachment:
        return True

    for kw in WHITELIST_SUBJECT_KEYWORDS:
        if kw in subject_lower:
            return True

    return False


def check_delete(sender_email, sender_name, subject, folder):
    """Return (should_delete, reason) tuple."""
    sender_lower = sender_email.lower()
    sender_name_lower = sender_name.lower()
    subject_lower = subject.lower()

    if any(x in folder.lower() for x in ["spam", "junk", "&v4nxppcu"]):
        return True, "Spam/Junk folder"

    for name in DELETE_SENDER_NAMES:
        if name in sender_name_lower or name in sender_lower:
            return True, f"Sender: {name}"

    for pattern in DELETE_SENDER_PATTERNS:
        if re.search(pattern, sender_lower):
            return True, f"Sender: {pattern}"

    for kw in DELETE_KEYWORDS:
        if kw in subject_lower:
            return True, f"Keyword: {kw}"

    for kw in DELETE_SUBJECT_KEYWORDS:
        if kw in subject_lower:
            return True, f"Category: {kw}"

    return False, ""


def apply_rules(emails):
    """Apply delete/not-delete rules. Returns list of deletion candidates."""
    candidates = []
    for em in emails:
        if check_not_delete(em["from"], em["from_name"], em["subject"], em["has_attachment"]):
            continue
        should_delete, reason = check_delete(em["from"], em["from_name"], em["subject"], em["folder"])
        if should_delete:
            candidates.append({**em, "reason": reason, "approve": "Y"})
    return candidates
