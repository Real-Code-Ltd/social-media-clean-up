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
    Checks if the user is currently logged in on Facebook.
    Returns True if logged in, False otherwise.
    """
    try:
        page.wait_for_timeout(3000)
        # Logged in Facebook has search input or notifications button or profile avatar.
        search_input = page.locator('input[placeholder*="Search Facebook"], [aria-label*="Search Facebook"]')
        profile_link = page.locator('a[href*="facebook.com/me"], a[href="/me/"]')
        navigation = page.locator('[role="navigation"]')
        
        if search_input.count() > 0 or profile_link.count() > 0 or navigation.count() > 0:
            return True
        return False
    except Exception:
        return False

def wait_for_user_login(page):
    """
    Prompts the user to log in if they are not already logged in.
    """
    log_info("Navigating to https://www.facebook.com/ ...")
    page.goto("https://www.facebook.com/")
    
    if check_login(page):
        log_success("Logged in automatically via saved session!")
        return True
    
    log_warn("No active session found. Please log in manually in the browser window.")
    log_info("Once you are logged in and see your home feed, return here and press ENTER to continue...")
    
    for i in range(100): # Auto-detect login in a loop
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

def run_facebook_cleanup(user_data_dir, headless=False):
    """
    Runs the Facebook cleanup automation.
    """
    log_info("Starting Facebook cleanup workflow...")
    
    with sync_playwright() as p:
        log_info(f"Launching browser with profile data directory: {user_data_dir}")
        args = ["--start-maximized", "--disable-notifications", "--disable-blink-features=AutomationControlled"]
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
            
        # Navigate to Activity Log
        log_info("Navigating to Facebook Activity Log (Comments and Reactions)...")
        activity_url = "https://www.facebook.com/me/allactivity/?activity_history=false&category_key=YOURACTIVITYCOMMENTSANDREACTIONSSCHEMA&manage_mode=false&should_load_landing_page=false"
        page.goto(activity_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)
        
        deleted_count = 0
        scroll_attempts_without_actions = 0
        max_scroll_attempts = 15
        
        log_info("Starting post/reaction cleanup loop. Press Ctrl+C in terminal to stop.")
        
        # Selector for the first unprocessed activity actions button
        selector = (
            'div[role="main"] div[role="button"][aria-haspopup="menu"]:not([data-cleanup-processed="true"]), '
            'div[role="main"] div[role="button"][aria-label*="Action"]:not([data-cleanup-processed="true"]), '
            'div[role="main"] div[role="button"][aria-label*="More"]:not([data-cleanup-processed="true"])'
        )
        
        while scroll_attempts_without_actions < max_scroll_attempts:
            # Query the live first unprocessed actions button
            btn = page.locator(selector).first
            
            if btn.count() == 0:
                # No more unprocessed buttons visible. Scroll down to load more.
                scroll_attempts_without_actions += 1
                log_info(f"No unprocessed items visible. Scrolling down (attempt {scroll_attempts_without_actions}/{max_scroll_attempts})...")
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(2000)
                continue
                
            # Reset scroll attempts since we found a live element
            scroll_attempts_without_actions = 0
            
            # Immediately mark it as processed in DOM so that we never scan it again,
            # even if the action fails or we choose to skip it.
            try:
                btn.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
            except Exception as e:
                log_warn(f"Failed to tag row element: {e}. Scrolling slightly to skip...")
                page.evaluate("window.scrollBy(0, 100)")
                page.wait_for_timeout(500)
                continue
                
            try:
                # Scroll it into view and wait for it to be stable
                btn.scroll_into_view_if_needed()
                page.wait_for_timeout(300) # Settling delay
                
                if not btn.is_visible():
                    continue
                    
                log_info("Opening options menu for the current row...")
                btn.click() # Standard click (waits for scroll stability)
                
                # Wait dynamically for the actual menu to appear
                menu_container = page.locator('div[role="menu"]').first
                try:
                    menu_container.wait_for(state="visible", timeout=2000)
                except Exception:
                    log_warn("Menu overlay (div[role='menu']) did not appear. Moving on...")
                    page.keyboard.press("Escape")
                    continue
                
                # Wait 500ms for React event listeners to bind
                page.wait_for_timeout(500)
                
                # Search for Unlike, Delete, Remove reaction, Remove tag, or Remove
                menu_items = [
                    "Unlike", 
                    "Delete", 
                    "Remove reaction", 
                    "Remove tag", 
                    "Remove"
                ]
                
                option_clicked = False
                clicked_text = ""
                for item_text in menu_items:
                    # Find the option ONLY inside the menu container
                    option = menu_container.locator(f'[role="menuitem"]:has-text("{item_text}"), [role="button"]:has-text("{item_text}"), div[role="menuitem"] :has-text("{item_text}")').first
                    if option.count() == 0:
                        option = menu_container.locator(f'span:has-text("{item_text}"), div:has-text("{item_text}")').first
                        
                    if option.count() > 0 and option.is_visible():
                        log_info(f"Found menu option: '{item_text}'. Clicking it...")
                        option.click() # Standard click (waits for stability)
                        option_clicked = True
                        clicked_text = item_text
                        break
                        
                if option_clicked:
                    # Handle confirmation dialog if it's a delete action
                    if clicked_text in ["Delete", "Remove", "Remove tag"]:
                        try:
                            dialog = page.locator('div[role="dialog"]').first
                            if dialog.wait_for(state="visible", timeout=2000):
                                page.wait_for_timeout(500) # Wait for dialog buttons to bind
                                confirm_btn = dialog.locator('div[role="button"]:has-text("Delete"), div[role="button"]:has-text("Remove"), div[role="button"]:has-text("Confirm"), button:has-text("Delete"), button:has-text("Move")').first
                                if confirm_btn.count() > 0 and confirm_btn.is_visible():
                                    log_info("Clicking confirmation button in dialog...")
                                    confirm_btn.click() # Standard click
                        except Exception:
                            pass # No dialog, maybe instant delete
                    
                    # Wait for the row actions button (btn) to disappear from the page
                    try:
                        # Wait up to 8 seconds for the row to disappear (DOM updates can be slow)
                        btn.wait_for(state="hidden", timeout=8000)
                        deleted_count += 1
                        log_success(f"Action '{clicked_text}' completed: row disappeared! (Item #{deleted_count})")
                        page.wait_for_timeout(1000) # Brief pause before next item
                    except Exception:
                        log_warn(f"Row did not disappear after '{clicked_text}' action. Moving on...")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                else:
                    # Close menu if no action option was found
                    log_info("No actionable option (Unlike/Delete/Remove) in menu. Skipping row...")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                    
            except Exception as ex:
                log_error(f"Error handling activity item: {ex}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                continue
                
        log_success(f"Cleanup finished! Processed {deleted_count} activity items.")
        context.close()
