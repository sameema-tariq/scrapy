from generate_reports.config import LOGIN_URL, PASSCODE
import time

# ─────────────────────────────────────────────
#  LOGIN
#  Called once before the company loop starts.
#  Uses wait_for_load_state instead of sleep.
# ─────────────────────────────────────────────

def login(page):
    print("Logging in...")
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=45000)

    for sel in ['input[type="password"]', 'input[type="text"]']:
        try:
            page.wait_for_selector(sel, timeout=5000)
            page.fill(sel, PASSCODE)
            break
        except:
            continue

    for btn in ['button:has-text("Log in")', 'button[type="submit"]', 'button']:
        try:
            page.click(btn, timeout=5000)
            break
        except:
            continue

    page.wait_for_load_state("networkidle", timeout=15000)
    print("Logged in.\n")


# ─────────────────────────────────────────────
#  CLICK VIEW BREAKDOWN
#  Waits for page to settle after click instead
#  of using a fixed time.sleep().
# ─────────────────────────────────────────────

def click_view_breakdown(page):
    print("Clicking View Breakdown...")
    for sel in [
        'button:has-text("View Breakdown")',
        'a:has-text("View Breakdown")',
        '*:has-text("View Breakdown")',
    ]:
        try:
            page.click(sel, timeout=5000)
            print(f"  → Clicked: {sel}")
            time.sleep(2)
            return True
        except:
            continue
    print("  → Could not find View Breakdown button.")
    return False
