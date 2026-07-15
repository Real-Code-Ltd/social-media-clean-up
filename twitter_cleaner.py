import time
import random
from playwright.sync_api import sync_playwright
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def log_success(msg):
    print(f"{Fore.GREEN}[SUCCESS] {msg}{Style.RESET_ALL}")

def log_info(msg):
    print(f"{Fore.BLUE}[INFO] {msg}{Style.RESET_ALL}")

def log_warn(msg):
    print(f"{Fore.YELLOW}[WARN] {msg}{Style.RESET_ALL}")

def log_error(msg):
    print(f"{Fore.RED}[ERROR] {msg}{Style.RESET_ALL}")

def check_login(page):
    """
    Checks if the user is currently logged in on Twitter/X.
    Returns True if logged in, False otherwise.
    """
    try:
        # A logged-in session should show the navigation sidebar with a Profile link,
        # or the tweet compose button (aria-label="Post" or data-testid="SideNav_NewTweet_Button")
        page.wait_for_timeout(3000)
        profile_btn = page.locator('[aria-label="Profile"]')
        compose_btn = page.locator('[data-testid="SideNav_NewTweet_Button"]')
        
        if profile_btn.count() > 0 or compose_btn.count() > 0:
            return True
        return False
    except Exception:
        return False

def wait_for_user_login(page):
    """
    Prompts the user to log in if they are not already logged in.
    """
    log_info("Navigating to https://x.com/ ...")
    page.goto("https://x.com/")
    
    if check_login(page):
        log_success("Logged in automatically via saved session!")
        return True
    
    log_warn("No active session found. Please log in manually in the browser window.")
    log_info("Once you are logged in and see your home timeline, return here and press ENTER to continue...")
    
    # Wait for the user to log in. We will check in a loop every 3 seconds,
    # or they can press Enter. We'll combine both: if they log in, we auto-proceed.
    for i in range(100): # 5 minutes max auto-check
        if check_login(page):
            log_success("Login detected! Proceeding...")
            return True
        page.wait_for_timeout(3000)
    
    input("Press Enter to verify login and continue...")
    if check_login(page):
        log_success("Login verified!")
        return True
    else:
        log_error("Could not verify login. Please try again.")
        return False

def run_twitter_cleanup(user_data_dir, headless=False):
    """
    Runs the Twitter/X cleanup automation.
    """
    log_info("Starting Twitter/X cleanup workflow...")
    
    with sync_playwright() as p:
        log_info(f"Launching browser with profile data directory: {user_data_dir}")
        args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        ignore_default_args = ["--enable-automation"]
        
        try:
            log_info("Attempting to launch system Google Chrome for maximum compatibility...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome",
                args=args,
                ignore_default_args=ignore_default_args,
                no_viewport=True
            )
        except Exception as e:
            log_warn(f"Could not launch system Google Chrome (channel='chrome'): {e}")
            log_info("Falling back to Playwright's built-in Chromium browser...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                args=args,
                ignore_default_args=ignore_default_args,
                no_viewport=True
            )
        
        # Open main page
        page = context.pages[0] if context.pages else context.new_page()
        
        # Handle login
        if not wait_for_user_login(page):
            context.close()
            return
        
        # Navigate to Profile
        log_info("Navigating to your profile page...")
        navigated = False
        profile_url = None
        
        # 1. Attempt to extract username from the sidebar Profile link's href
        for attempt in range(5):
            try:
                profile_link = page.locator('[aria-label="Profile"]').first
                if profile_link.count() > 0:
                    href = profile_link.get_attribute("href")
                    if href and href != "/profile" and href != "/":
                        profile_url = f"https://x.com{href}"
                        log_info(f"Detected profile handle from sidebar: {href}. Navigating directly...")
                        page.goto(profile_url)
                        page.wait_for_load_state("domcontentloaded")
                        navigated = True
                        break
            except Exception:
                pass
            page.wait_for_timeout(1000)
            
        # 2. Fallback: Try to click the Profile button and wait for redirect
        if not navigated:
            try:
                log_info("Clicking the Profile sidebar button...")
                profile_btn = page.locator('[aria-label="Profile"]').first
                if profile_btn.count() > 0:
                    profile_btn.click(force=True)
                    page.wait_for_load_state("domcontentloaded")
                    # Wait up to 5 seconds to see if URL updates to your handle
                    for _ in range(10):
                        if "/profile" not in page.url and "/home" not in page.url:
                            log_success(f"Successfully redirected to: {page.url}")
                            profile_url = page.url
                            navigated = True
                            break
                        page.wait_for_timeout(500)
            except Exception as e:
                log_warn(f"Could not click profile button: {e}")
                
        # 3. Last fallback: Navigate to /profile directly
        if not navigated:
            try:
                log_info("Navigating to https://x.com/profile ...")
                page.goto("https://x.com/profile")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
                # Check one last time if we can resolve the handle from here
                profile_link = page.locator('[aria-label="Profile"]').first
                if profile_link.count() > 0:
                    href = profile_link.get_attribute("href")
                    if href and href != "/profile" and href != "/":
                        profile_url = f"https://x.com{href}"
                        page.goto(profile_url)
                        page.wait_for_load_state("domcontentloaded")
                        navigated = True
            except Exception as e:
                log_error(f"Fallback navigation failed: {e}")
                
        if navigated:
            log_success("Successfully navigated to your profile!")
        else:
            log_warn("Profile page detection incomplete. Starting deletion loop anyway...")
            
        # Dismiss cookie consent banner if present
        try:
            cookie_btn = page.locator('button:has-text("Refuse non-essential cookies"), button:has-text("Refuse optional cookies"), button:has-text("Close"), [aria-label="Close"]').first
            if cookie_btn.count() > 0 and cookie_btn.is_visible():
                log_info("Dismissing cookie consent banner...")
                cookie_btn.click(force=True, timeout=3000)
        except Exception:
            pass
            
        page.wait_for_timeout(3000)
        
        deleted_count = 0
        reposts_undone_count = 0
        scroll_attempts_without_actions = 0
        max_scroll_attempts = 10
        
        log_info("Starting post deletion loop. Press Ctrl+C in terminal to stop.")
        
        while scroll_attempts_without_actions < max_scroll_attempts:
            # If we navigated away to explore or home, return back to the profile page
            if "/explore" in page.url or "/home" in page.url or page.url.endswith("x.com/") or page.url.endswith("twitter.com/"):
                if profile_url:
                    log_warn(f"Navigated away to {page.url}. Returning to profile: {profile_url}...")
                    page.goto(profile_url)
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(3000)
                    continue
                    
            # Find all tweet elements on the page, excluding already processed ones
            tweets = page.locator('article[data-testid="tweet"]:not([data-cleanup-processed="true"])').all()
            log_info(f"Found {len(tweets)} unprocessed tweets in view.")
            
            action_taken_in_this_view = False
            
            for tweet in tweets:
                # Mark tweet as processed so we don't evaluate it again
                try:
                    tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                except Exception:
                    pass
                
                try:
                    # Let's check if this is a Repost or our own Tweet.
                    social_context = tweet.locator('[data-testid="socialContext"]')
                    is_repost = False
                    if social_context.count() > 0:
                        text = social_context.first.inner_text().lower()
                        if "reposted" in text or "retweeted" in text:
                            is_repost = True
                    
                    # Check if there is an active 'unretweet' button.
                    unretweet_btn = tweet.locator('[data-testid="unretweet"]')
                    if unretweet_btn.count() > 0 or is_repost:
                        # Highlight the repost to show what we are doing
                        tweet.scroll_into_view_if_needed()
                        log_info("Found repost. Undoing repost...")
                        
                        btn_to_click = unretweet_btn.first if unretweet_btn.count() > 0 else tweet.locator('[data-testid="retweet"]').first
                        btn_to_click.click(force=True)
                        page.wait_for_timeout(300) # Fast menu wait
                        
                        # A pop-up menu appears with "Undo Repost"
                        undo_btn = page.locator('[role="menuitem"]:has-text("Undo Repost"), [role="menuitem"]:has-text("Undo repost"), span:has-text("Undo Repost"), span:has-text("Undo repost")').first
                            
                        if undo_btn.count() > 0:
                            undo_btn.click(force=True)
                            reposts_undone_count += 1
                            action_taken_in_this_view = True
                            log_success(f"Undone repost #{reposts_undone_count}!")
                            page.wait_for_timeout(random.uniform(500, 1000)) # Fast cleanup delay
                            break # Break out of inner loop to refresh tweets list and avoid stale element reference
                        else:
                            log_warn("Could not find 'Undo Repost' button in dropdown menu.")
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(200)
                            
                    # Otherwise, it's our own post. Let's delete it.
                    caret_btn = tweet.locator('[data-testid="caret"]')
                    if caret_btn.count() > 0:
                        tweet.scroll_into_view_if_needed()
                        log_info("Deleting own tweet...")
                        caret_btn.first.click(force=True)
                        page.wait_for_timeout(300) # Fast menu wait
                        
                        # Look for "Delete" menuitem
                        delete_btn = page.locator('[role="menuitem"]:has-text("Delete"), span:has-text("Delete")').first
                            
                        if delete_btn.count() > 0:
                            delete_btn.click(force=True)
                            page.wait_for_timeout(300)
                            
                            # Confirmation popup
                            confirm_btn = page.locator('[data-testid="confirmationSheetConfirm"], button:has-text("Delete")').first
                                
                            if confirm_btn.count() > 0:
                                confirm_btn.click(force=True)
                                deleted_count += 1
                                action_taken_in_this_view = True
                                log_success(f"Deleted tweet #{deleted_count}!")
                                page.wait_for_timeout(random.uniform(600, 1200)) # Fast cleanup delay
                                break # Break to refresh tweets list
                            else:
                                log_warn("Could not find 'Delete' confirmation button in modal.")
                                page.keyboard.press("Escape")
                                page.wait_for_timeout(200)
                        else:
                            log_info("Menu item 'Delete' not found (this tweet might not belong to you). Closing menu...")
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(200)
                except Exception as ex:
                    log_error(f"Error handling tweet: {ex}")
                    # Try to hit Escape to dismiss any open dropdowns or overlays
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                    continue
            
            if action_taken_in_this_view:
                # Reset scroll attempts since we successfully acted on a post
                scroll_attempts_without_actions = 0
            else:
                # Scroll down to load more tweets
                scroll_attempts_without_actions += 1
                log_info(f"No actions taken on current page. Scrolling down (attempt {scroll_attempts_without_actions}/{max_scroll_attempts})...")
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(1000) # Fast scroll wait
        
        log_success(f"Cleanup finished! Deleted: {deleted_count} tweets, Undone: {reposts_undone_count} reposts.")
        context.close()
