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
            
        # Navigate to Profile
        log_info("Navigating to your Facebook profile page...")
        page.goto("https://www.facebook.com/me")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        deleted_count = 0
        scroll_attempts_without_actions = 0
        max_scroll_attempts = 10
        
        log_info("Starting post deletion loop. Press Ctrl+C in terminal to stop.")
        
        while scroll_attempts_without_actions < max_scroll_attempts:
            # Find the 'actions' or 'three dots' buttons for the posts.
            # Facebook usually marks this button with aria-label containing "Actions for this post" or "More options"
            actions_buttons = page.locator('div[role="button"][aria-label*="Action"], div[role="button"][aria-label*="More"], div[role="button"][aria-label*="options"]').all()
            
            log_info(f"Found {len(actions_buttons)} actions buttons in view.")
            action_taken_in_this_view = False
            
            for btn in actions_buttons:
                try:
                    # Scroll button into view and click
                    btn.scroll_into_view_if_needed()
                    
                    # Make sure the button is actually visible and clickable
                    if not btn.is_visible():
                        continue
                        
                    btn.click()
                    page.wait_for_timeout(1500)
                    
                    # Now search for "Move to trash", "Delete post", "Move to Archive", or "Delete" menu item
                    # Facebook's menu items typically are div[role="menuitem"] or contain text
                    menu_items = [
                        "Move to trash", 
                        "Delete post", 
                        "Move to Archive", 
                        "Delete", 
                        "Remove tag"
                    ]
                    
                    option_clicked = False
                    for item_text in menu_items:
                        # Case insensitive or exact match check
                        option = page.locator(f'div[role="menuitem"]:has-text("{item_text}"), span:has-text("{item_text}")').first
                        if option.count() > 0 and option.is_visible():
                            log_info(f"Found option: '{item_text}'. Clicking it...")
                            option.click()
                            option_clicked = True
                            page.wait_for_timeout(2000)
                            break
                            
                    if option_clicked:
                        # Now handle the confirmation dialog if it appears.
                        # Look for buttons in role="dialog" with text containing Move, Delete, Confirm, or Archive
                        confirm_btn = page.locator('div[role="dialog"] div[role="button"]:has-text("Move"), div[role="dialog"] div[role="button"]:has-text("Delete"), div[role="dialog"] div[role="button"]:has-text("Confirm"), div[role="dialog"] button:has-text("Delete"), div[role="dialog"] button:has-text("Move")').first
                        
                        if confirm_btn.count() > 0 and confirm_btn.is_visible():
                            confirm_btn.click()
                            deleted_count += 1
                            action_taken_in_this_view = True
                            log_success(f"Moved post #{deleted_count} to trash/deleted!")
                            page.wait_for_timeout(random.uniform(3000, 5000))
                            break # Break to re-evaluate visible posts
                        else:
                            log_warn("No confirmation button detected, or the action did not trigger a modal. Continuing...")
                            action_taken_in_this_view = True
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(1000)
                            break
                    else:
                        # Close menu if no deletion option was found
                        log_info("No deletion option found in dropdown. Closing menu...")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                        
                except Exception as ex:
                    log_error(f"Error handling Facebook post actions: {ex}")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                    continue
                    
            if action_taken_in_this_view:
                scroll_attempts_without_actions = 0
            else:
                scroll_attempts_without_actions += 1
                log_info(f"No actions taken on current page. Scrolling down (attempt {scroll_attempts_without_actions}/{max_scroll_attempts})...")
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(3000)
                
        log_success(f"Cleanup finished! Moved {deleted_count} posts to trash/deleted.")
        context.close()
