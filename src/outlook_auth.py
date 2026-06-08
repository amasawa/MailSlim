"""
Outlook OAuth2 authentication using persistent Chrome profile.

Flow:
  1. First time: browser login with MFA -> session cookies saved to persistent profile
  2. Subsequent: headless Chrome loads OWA with saved cookies -> auto-login -> extract token
  3. If session expires (~30 days), user re-authenticates once with MFA

No refresh token exchange needed - the browser handles session persistence natively.
"""

import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = Path(__file__).parent.parent
CHROME_PROFILE_DIR = str(BASE_DIR / ".chrome_profile")


def _extract_token(driver):
    """Extract Outlook-scoped access token from OWA's localStorage."""
    tokens = driver.execute_script("""
        var result = [];
        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            if (key.indexOf('accesstoken') > -1) {
                try { result.push(JSON.parse(localStorage.getItem(key))); } catch(e) {}
            }
        }
        return result;
    """)

    for t in tokens:
        target = t.get('target', '')
        if 'outlook.office.com' in target and 'Mail.ReadWrite' in target:
            return t['secret']

    for t in tokens:
        if 'outlook.office.com' in t.get('target', ''):
            return t['secret']

    return None


def _is_inbox_loaded(driver):
    """Check if Outlook inbox is actually loaded (not login page)."""
    url = driver.current_url
    if "login.microsoftonline.com" in url:
        return False
    return url.startswith("https://outlook.office.com/mail") or \
           url.startswith("https://outlook.office365.com/mail")


def get_access_token(interactive=None):
    """Get a valid Outlook access token.

    Args:
        interactive: None = auto-detect, True = force browser visible, False = force headless

    First tries headless (using saved session). If that fails, opens visible browser
    for manual login. After first login, subsequent calls are fully automatic.
    """

    # Try headless first (silent auth with saved session)
    if interactive is not True:
        token = _try_headless()
        if token:
            return token
        if interactive is False:
            raise RuntimeError(
                "Outlook session expired. Please run the following to re-authenticate:\n"
                "  ! python3 -c \"from src.outlook_auth import get_access_token; get_access_token(interactive=True)\""
            )
        print("Saved session expired or not found. Opening browser for login...")

    # Fall back to interactive login
    return _interactive_login()


def _try_headless():
    """Try to get token using headless Chrome with saved profile. Returns token or None."""
    profile_check = Path(CHROME_PROFILE_DIR)
    if not profile_check.exists():
        return None

    print("Trying silent authentication (headless)...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_script_timeout(30)

        driver.get("https://outlook.office.com/mail/")

        # Wait up to 30s for auto-login
        try:
            WebDriverWait(driver, 30, poll_frequency=2).until(_is_inbox_loaded)
        except:
            print("  Auto-login did not complete in 30s.")
            driver.quit()
            return None

        # Give OWA a moment to populate localStorage
        time.sleep(3)

        token = _extract_token(driver)
        driver.quit()

        if token:
            print("Silent auth successful!")
            return token

        return None

    except Exception as e:
        print(f"  Headless failed: {e}")
        try:
            driver.quit()
        except:
            pass
        return None


def _interactive_login():
    """Open visible browser for manual login. Saves session to persistent profile."""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_script_timeout(30)

    driver.get("https://outlook.office.com/mail/")

    # Check if already logged in
    time.sleep(5)
    if _is_inbox_loaded(driver):
        print("Already logged in from saved session!")
    else:
        input("\n>>> Login and complete MFA, press Enter when you see your inbox... ")

    token = _extract_token(driver)
    driver.quit()

    if not token:
        raise RuntimeError("Could not find Outlook access token.")

    print("Token extracted. Session saved for future automatic use.\n")
    return token
