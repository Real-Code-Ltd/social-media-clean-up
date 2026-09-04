import time
import random
from playwright.sync_api import sync_playwright
from colorama import Fore, Style, init
from config import DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY, PAGE_REFRESH_INTERVAL

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

def reload_twitter_page(page, context_label=""):
    """
    Reloads the current Twitter page, waits for hydration, and handles cookie consent.
    Returns True if refreshed successfully, False if browser was closed.
    """
    log_info(f"Pacing/Sticking safeguard: 2 minutes elapsed. Refreshing page to reload fresh state...")
    try:
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3500)
        # Dismiss cookie banner if reappeared
        try:
            cookie_btn = page.locator('button:has-text("Refuse non-essential cookies"), button:has-text("Refuse optional cookies"), button:has-text("Close"), [aria-label="Close"]').first
            if cookie_btn.count() > 0 and cookie_btn.is_visible():
                cookie_btn.click(force=True, timeout=2000)
        except Exception:
            pass
        log_success(f"Page refreshed successfully! Resuming {context_label}...")
        return True
    except Exception as ref_err:
        if "closed" in str(ref_err).lower() or page.is_closed():
            return False
        log_warn(f"Page reload encountered an issue: {ref_err}")
        return True

def get_user_post_info(tweet, user_handle):
    """
    Analyzes a tweet or conversation thread element.
    Returns (has_user_post, user_post_index, detected_author)
    where:
      - has_user_post: True if this element contains a post authored by user_handle
      - user_post_index: The 0-based index of the user's post in this thread
      - detected_author: The handle of the first author found (for logging)
    """
    if not user_handle:
        return True, 0, "you"
    try:
        user_name_boxes = tweet.locator('[data-testid="User-Name"]').all()
        if not user_name_boxes:
            return True, 0, "unknown"
            
        first_author = ""
        for idx, box in enumerate(user_name_boxes):
            links = box.locator('a[href]').all()
            for link in links:
                href = (link.get_attribute("href") or "").strip("/").lower()
                clean_handle = href.split("/")[0]
                if clean_handle and clean_handle not in ("home", "explore", "notifications", "messages"):
                    if not first_author:
                        first_author = clean_handle
                    if clean_handle == user_handle:
                        return True, idx, user_handle
                        
            text = box.inner_text().lower()
            if f"@{user_handle}" in text:
                return True, idx, user_handle
                
        return False, -1, first_author or "another user"
    except Exception:
        return True, 0, "unknown"

def check_login(page):
    """
    Checks if the user is currently logged in on Twitter/X.
    """
    try:
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
    
    for i in range(100): # 5 minutes max auto-check
        if page.is_closed():
            return False
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

def cleanup_posts_timeline(page, my_handle, target_url, tab_label, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    """
    Cleans up user's posts, replies in threads, and undoes reposts from a specific timeline URL.
    Handles both main profile posts (https://x.com/{my_handle}) and thread replies (https://x.com/{my_handle}/with_replies).
    """
    log_info(f"Navigating to {tab_label}: {target_url} ...")
    try:
        page.goto(target_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        if "closed" in str(e).lower():
            log_warn(f"Browser closed during navigation to {tab_label}.")
            return 0, 0
        log_error(f"Error navigating to {tab_label}: {e}")
        return 0, 0

    expected_path = target_url.split("x.com/")[-1].split("twitter.com/")[-1].split("?")[0].split("#")[0].rstrip("/").lower()

    def is_on_target_tab(url):
        curr_path = (url or "").split("x.com/")[-1].split("twitter.com/")[-1].split("?")[0].split("#")[0].rstrip("/").lower()
        return curr_path == expected_path

    deleted_count = 0
    reposts_undone_count = 0
    scroll_attempts_without_actions = 0
    max_scroll_attempts = 10
    failed_attempts = {}
    last_refresh_time = time.time()

    log_info(f"Starting {tab_label} deletion loop. Press Ctrl+C in terminal to stop.")

    while scroll_attempts_without_actions < max_scroll_attempts:
        if page.is_closed():
            log_warn("Browser closed. Stopping deletion loop...")
            break

        # Check if 2 minutes elapsed since last refresh to prevent sticking
        if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
            if not reload_twitter_page(page, tab_label):
                break
            last_refresh_time = time.time()
            scroll_attempts_without_actions = 0
            continue

        # If navigated away from target URL, return back
        if not is_on_target_tab(page.url):
            log_warn(f"Navigated away to {page.url}. Returning to {tab_label}: {target_url}...")
            try:
                page.goto(target_url)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception:
                break
            continue

        tweets = page.locator('article[data-testid="tweet"]:not([data-cleanup-processed="true"])').all()
        log_info(f"Found {len(tweets)} unprocessed tweets in {tab_label} view.")

        action_taken_in_this_view = False

        for tweet in tweets:
            if page.is_closed():
                break
            if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
                break
            if not is_on_target_tab(page.url):
                log_warn(f"Redirect detected ({page.url}). Breaking to return to {tab_label}...")
                break

            tweet_key = None
            try:
                status_links = tweet.locator('a[href*="/status/"]').all()
                if status_links:
                    link_elem = status_links[-1] if len(status_links) > 1 else status_links[0]
                    href = link_elem.get_attribute("href") or ""
                    if "/status/" in href:
                        tweet_key = href.split("/status/")[-1].split("?")[0].split("/")[0]
            except Exception:
                pass
            if not tweet_key:
                try:
                    tweet_key = tweet.evaluate("el => el.innerText.slice(0, 30)")
                except Exception:
                    tweet_key = str(random.random())

            try:
                tweet.evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
            except Exception:
                try:
                    tweet.scroll_into_view_if_needed()
                except Exception:
                    pass
            page.wait_for_timeout(300)

            try:
                # 1. Check if this is a Repost
                social_context = tweet.locator('[data-testid="socialContext"]')
                is_repost = False
                if social_context.count() > 0:
                    text = social_context.first.inner_text().lower()
                    if "reposted" in text or "retweeted" in text:
                        is_repost = True

                unretweet_btn = tweet.locator('[data-testid="unretweet"]')
                if unretweet_btn.count() > 0 or is_repost:
                    log_info("Found repost. Undoing repost...")
                    btn_to_click = unretweet_btn.first if unretweet_btn.count() > 0 else tweet.locator('[data-testid="retweet"]').first
                    try:
                        btn_to_click.click(timeout=3000)
                    except Exception:
                        btn_to_click.click(force=True, timeout=3000)

                    undo_btn = page.locator(
                        '[data-testid="unretweetConfirm"], '
                        '[role="menu"] [role="menuitem"]:has-text("Undo Repost"), '
                        '[role="menu"] [role="menuitem"]:has-text("Undo repost"), '
                        '[data-testid="Dropdown"] [role="menuitem"]:has-text("Undo")'
                    ).first

                    try:
                        undo_btn.wait_for(state="visible", timeout=3000)
                        page.wait_for_timeout(250)
                        try:
                            undo_btn.click(timeout=3000)
                        except Exception:
                            undo_btn.click(force=True, timeout=3000)

                        try:
                            undo_btn.wait_for(state="hidden", timeout=3000)
                        except Exception:
                            pass

                        reposts_undone_count += 1
                        action_taken_in_this_view = True
                        log_success(f"Undone repost #{reposts_undone_count}!")

                        try:
                            tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass

                        delay = random.uniform(min_delay, max_delay)
                        log_info(f"Pacing: waiting {delay:.1f}s before next post...")
                        page.wait_for_timeout(int(delay * 1000))
                        break
                    except Exception as undo_err:
                        log_warn(f"Could not confirm 'Undo Repost': {undo_err}")
                        try:
                            page.keyboard.press("Escape")
                        except Exception:
                            pass
                        failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                        if failed_attempts[tweet_key] >= 2:
                            try:
                                tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                            except Exception:
                                pass
                        continue

                # 2. Check author across all posts in this thread card
                has_own_post, post_idx, author_name = get_user_post_info(tweet, my_handle)
                if not has_own_post:
                    log_info(f"Skipping thread by @{author_name} (no posts/replies by you)...")
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

                # 3. Otherwise, it's our own post or our reply in this thread. Delete it.
                user_name_boxes = tweet.locator('[data-testid="User-Name"]').all()
                carets = tweet.locator('[data-testid="caret"]').all()
                if not carets:
                    carets = tweet.locator('[aria-label="More"], [aria-label="More actions"]').all()

                if not carets:
                    log_warn("No caret menu button found on post/reply. Skipping...")
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

                if post_idx > 0:
                    log_info(f"Found your reply in thread (reply #{post_idx + 1}). Deleting reply...")
                    if post_idx < len(user_name_boxes):
                        try:
                            user_name_boxes[post_idx].evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
                            page.wait_for_timeout(300)
                        except Exception:
                            pass
                else:
                    log_info("Deleting own tweet...")

                if post_idx < len(carets):
                    caret_btn = carets[post_idx]
                else:
                    caret_btn = carets[-1]

                try:
                    caret_btn.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    caret_btn.click(timeout=3000)
                except Exception:
                    caret_btn.click(force=True, timeout=3000)

                dropdown = page.locator('[data-testid="Dropdown"], div[role="menu"]').first
                menu_appeared = False
                try:
                    dropdown.wait_for(state="visible", timeout=2500)
                    menu_appeared = True
                except Exception:
                    try:
                        caret_btn.click(force=True, timeout=2000)
                        dropdown.wait_for(state="visible", timeout=2000)
                        menu_appeared = True
                    except Exception:
                        menu_appeared = False

                if not menu_appeared:
                    log_warn("Dropdown menu did not appear after clicking caret.")
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass
                    failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                    if failed_attempts[tweet_key] >= 2:
                        try:
                            tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass
                    continue

                delete_btn = dropdown.locator('[role="menuitem"]').filter(has_text="Delete").first
                if delete_btn.count() == 0:
                    delete_btn = dropdown.locator('[data-testid="delete"], [role="menuitem"]:has-text("Delete")').first

                has_delete = False
                try:
                    if delete_btn.count() > 0 and delete_btn.is_visible():
                        has_delete = True
                    else:
                        delete_btn.wait_for(state="visible", timeout=2000)
                        has_delete = True
                except Exception:
                    has_delete = False

                if has_delete:
                    try:
                        delete_btn.scroll_into_view_if_needed()
                        delete_btn.click(timeout=3000)
                    except Exception:
                        delete_btn.click(force=True, timeout=3000)

                    confirm_btn = page.locator(
                        '[data-testid="confirmationSheetConfirm"], '
                        '[data-testid="confirmationSheetDialog"] button:has-text("Delete"), '
                        '[data-testid="confirmationSheetDialog"] [role="button"]:has-text("Delete"), '
                        '[role="dialog"] button:has-text("Delete"), '
                        '[role="dialog"] [role="button"]:has-text("Delete"), '
                        '[role="alertdialog"] button:has-text("Delete"), '
                        '[role="alertdialog"] [role="button"]:has-text("Delete")'
                    ).first

                    try:
                        confirm_btn.wait_for(state="visible", timeout=6000)
                        page.wait_for_timeout(350)
                        try:
                            confirm_btn.click(timeout=3000)
                        except Exception:
                            confirm_btn.click(force=True, timeout=3000)

                        try:
                            confirm_btn.wait_for(state="hidden", timeout=3500)
                        except Exception:
                            pass

                        deleted_count += 1
                        action_taken_in_this_view = True
                        if post_idx > 0:
                            log_success(f"Deleted reply #{deleted_count}!")
                        else:
                            log_success(f"Deleted tweet #{deleted_count}!")

                        try:
                            tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass

                        delay = random.uniform(min_delay, max_delay)
                        log_info(f"Pacing: waiting {delay:.1f}s before next post...")
                        page.wait_for_timeout(int(delay * 1000))
                        break
                    except Exception as conf_err:
                        log_warn(f"Could not confirm deletion in modal: {conf_err}")
                        try:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            page.keyboard.press("Escape")
                        except Exception:
                            pass
                        failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                        if failed_attempts[tweet_key] >= 2:
                            log_warn("Post failed confirmation twice. Skipping...")
                            try:
                                tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                            except Exception:
                                pass
                        continue
                else:
                    log_info("Menu item 'Delete' not found in dropdown. Closing menu...")
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

            except Exception as ex:
                err_str = str(ex).lower()
                if "closed" in err_str or page.is_closed():
                    log_warn("Browser was closed. Exiting...")
                    return deleted_count, reposts_undone_count
                log_error(f"Error handling tweet: {ex}")
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                if failed_attempts[tweet_key] >= 2:
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                continue

        if action_taken_in_this_view:
            scroll_attempts_without_actions = 0
        else:
            scroll_attempts_without_actions += 1
            # If user has already deleted all their tweets on this tab, stop after 5 scrolls without actions
            max_allowed_scrolls = 5 if (deleted_count == 0 and reposts_undone_count == 0) else max_scroll_attempts
            if scroll_attempts_without_actions >= max_allowed_scrolls:
                log_info(f"No more posts found in {tab_label} after {scroll_attempts_without_actions} scroll attempts.")
                break

            log_info(f"No actions taken on current page. Scrolling down (attempt {scroll_attempts_without_actions}/{max_allowed_scrolls})...")
            try:
                page.evaluate("window.scrollBy(0, 1200)")
                page.wait_for_timeout(2500)
            except Exception as e:
                if "closed" in str(e).lower():
                    break

    log_success(f"{tab_label} cleanup finished: {deleted_count} deleted, {reposts_undone_count} reposts undone.")
    return deleted_count, reposts_undone_count

def cleanup_likes(page, my_handle, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    """
    Cleans up all liked posts (hearts) on Twitter/X by navigating to the user's /likes tab
    and systematically un-hearting all posts.
    """
    target_likes_url = f"https://x.com/{my_handle}/likes"
    log_info(f"Navigating to Likes (hearts) page: {target_likes_url} ...")
    try:
        page.goto(target_likes_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        if "closed" in str(e).lower():
            log_warn("Browser closed during navigation to likes.")
            return 0
        log_error(f"Error navigating to likes: {e}")
        return 0

    def is_on_likes_page(url):
        u = (url or "").lower()
        return "/likes" in u or "/i/history/likes" in u

    # Twitter redirects /handle/likes to /i/history/likes for private likes
    active_likes_url = page.url if is_on_likes_page(page.url) else target_likes_url
    log_info(f"Active Likes page: {active_likes_url}")

    unheart_count = 0
    scroll_attempts_without_actions = 0
    max_scroll_attempts = 10
    failed_attempts = {}
    last_refresh_time = time.time()

    log_info("Starting Likes (hearts) cleanup loop. Press Ctrl+C in terminal to stop.")

    while scroll_attempts_without_actions < max_scroll_attempts:
        if page.is_closed():
            log_warn("Browser closed. Stopping likes cleanup loop...")
            break

        # Check if 2 minutes elapsed since last refresh to prevent sticking
        if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
            if not reload_twitter_page(page, "likes cleanup"):
                break
            last_refresh_time = time.time()
            scroll_attempts_without_actions = 0
            continue

        # If navigated away from likes entirely, return back
        if not is_on_likes_page(page.url):
            log_warn(f"Navigated away to {page.url}. Returning to likes: {active_likes_url}...")
            try:
                page.goto(active_likes_url)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2500)
            except Exception:
                break
            continue

        # Check for empty likes state
        try:
            empty_state = page.locator(
                'text="You don’t have any likes yet", '
                'text="hasn\'t liked any posts", '
                'text="No Likes yet", '
                'text="Tap the heart on any post"'
            ).first
            if empty_state.count() > 0 and empty_state.is_visible():
                log_success("All likes have been cleared! Empty likes page detected.")
                break
        except Exception:
            pass

        # Query all unprocessed tweets in view
        tweets = page.locator('article[data-testid="tweet"]:not([data-cleanup-processed="true"])').all()
        log_info(f"Found {len(tweets)} unprocessed posts in Likes view.")

        action_taken_in_this_view = False

        for tweet in tweets:
            if page.is_closed():
                break
            if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
                break
            if not is_on_likes_page(page.url):
                break

            tweet_key = None
            try:
                status_links = tweet.locator('a[href*="/status/"]').all()
                if status_links:
                    link_elem = status_links[-1] if len(status_links) > 1 else status_links[0]
                    href = link_elem.get_attribute("href") or ""
                    if "/status/" in href:
                        tweet_key = href.split("/status/")[-1].split("?")[0].split("/")[0]
            except Exception:
                pass
            if not tweet_key:
                try:
                    tweet_key = tweet.evaluate("el => el.innerText.slice(0, 30)")
                except Exception:
                    tweet_key = str(random.random())

            try:
                tweet.evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
            except Exception:
                try:
                    tweet.scroll_into_view_if_needed()
                except Exception:
                    pass
            page.wait_for_timeout(250)

            try:
                # Find unlike button (red/filled heart)
                unlike_btn = tweet.locator('[data-testid="unlike"]').first
                if unlike_btn.count() == 0:
                    unlike_btn = tweet.locator('[aria-label*="Liked"], [aria-label*="Unlike"]').first

                if unlike_btn.count() > 0 and unlike_btn.is_visible():
                    log_info("Found liked post. Un-hearting...")
                    try:
                        unlike_btn.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    try:
                        unlike_btn.click(timeout=2500)
                    except Exception:
                        unlike_btn.click(force=True, timeout=2500)

                    # Wait for like icon to change to outline or wait brief moment
                    page.wait_for_timeout(350)

                    # If click accidentally navigated into status page, return to likes
                    if "/status/" in page.url:
                        log_warn("Accidental navigation into tweet detected. Returning to likes...")
                        page.goto(active_likes_url)
                        page.wait_for_load_state("domcontentloaded")
                        page.wait_for_timeout(2000)

                    unheart_count += 1
                    action_taken_in_this_view = True
                    log_success(f"Un-hearted post #{unheart_count}!")

                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass

                    delay = random.uniform(min_delay, max_delay)
                    log_info(f"Pacing: waiting {delay:.1f}s before next un-heart...")
                    page.wait_for_timeout(int(delay * 1000))
                    break # Break to re-evaluate tweets in fresh state
                else:
                    # Tweet does not have an active like (e.g. already unliked or promoted post)
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

            except Exception as ex:
                err_str = str(ex).lower()
                if "closed" in err_str or page.is_closed():
                    log_warn("Browser was closed. Exiting...")
                    return unheart_count
                log_warn(f"Could not un-heart post: {ex}")
                failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                if failed_attempts[tweet_key] >= 2:
                    try:
                        tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                continue

        if action_taken_in_this_view:
            scroll_attempts_without_actions = 0
        else:
            scroll_attempts_without_actions += 1
            log_info(f"No liked posts in current view. Scrolling down (attempt {scroll_attempts_without_actions}/{max_scroll_attempts})...")
            try:
                page.evaluate("window.scrollBy(0, 1200)")
                page.wait_for_timeout(2500)
            except Exception as e:
                if "closed" in str(e).lower():
                    break

    log_success(f"Likes cleanup completed! Total un-hearted: {unheart_count}")
    return unheart_count

def run_twitter_cleanup(user_data_dir, headless=False, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY, mode="all"):
    """
    Runs the Twitter/X cleanup automation.
    Mode:
      - 'all': Clean posts, replies, reposts, and then likes/hearts.
      - 'posts': Clean posts, replies, and reposts only.
      - 'likes': Clean likes/hearts only.
    """
    log_info("Starting Twitter/X cleanup workflow...")
    mode_label = "All Activity (Posts, Replies, Reposts & Likes)" if mode == "all" else ("Likes / Hearts only" if mode == "likes" else "Posts & Replies only")
    log_info(f"Cleanup Target: {mode_label}")
    log_info(f"Pacing: {min_delay:.1f}s - {max_delay:.1f}s delay between actions.")
    
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
        
        try:
            page = context.pages[0] if context.pages else context.new_page()
            
            # Handle login
            if not wait_for_user_login(page):
                context.close()
                return
            
            # Detect user handle and profile
            log_info("Detecting profile handle...")
            my_handle = None
            profile_url = None
            
            # 1. Attempt to extract username from sidebar Profile link href
            for _ in range(5):
                try:
                    profile_link = page.locator('[aria-label="Profile"]').first
                    if profile_link.count() > 0:
                        href = profile_link.get_attribute("href")
                        if href and href != "/profile" and href != "/":
                            my_handle = href.strip("/").lower()
                            profile_url = f"https://x.com{href}"
                            break
                except Exception:
                    pass
                page.wait_for_timeout(800)

            # 2. Fallback: Click profile button and check redirected URL
            if not my_handle:
                try:
                    log_info("Clicking Profile button to detect handle...")
                    profile_btn = page.locator('[aria-label="Profile"]').first
                    if profile_btn.count() > 0:
                        profile_btn.click(force=True)
                        page.wait_for_load_state("domcontentloaded")
                        for _ in range(8):
                            if "/profile" not in page.url and "/home" not in page.url:
                                profile_url = page.url
                                path_parts = [p for p in profile_url.split("x.com/")[-1].split("twitter.com/")[-1].split("/") if p]
                                if path_parts and path_parts[0] not in ("profile", "home", "explore"):
                                    my_handle = path_parts[0].lower()
                                    break
                            page.wait_for_timeout(500)
                except Exception:
                    pass

            if not my_handle and profile_url:
                path_parts = [p for p in profile_url.split("x.com/")[-1].split("twitter.com/")[-1].split("/") if p]
                if path_parts and path_parts[0] not in ("profile", "home", "explore"):
                    my_handle = path_parts[0].lower()

            if not my_handle:
                # Ultimate fallback
                my_handle = input(f"\n{Fore.YELLOW}Could not auto-detect your Twitter handle. Enter handle (without @): ").strip().lstrip("@").lower()
                profile_url = f"https://x.com/{my_handle}"

            log_info(f"Targeting Twitter account: @{my_handle}")

            # Dismiss cookie banner
            try:
                cookie_btn = page.locator('button:has-text("Refuse non-essential cookies"), button:has-text("Refuse optional cookies"), button:has-text("Close"), [aria-label="Close"]').first
                if cookie_btn.count() > 0 and cookie_btn.is_visible():
                    cookie_btn.click(force=True, timeout=2500)
            except Exception:
                pass

            deleted_posts = 0
            undone_reposts = 0
            unhearted_likes = 0

            main_posts_url = f"https://x.com/{my_handle}"
            replies_url = f"https://x.com/{my_handle}/with_replies"

            # Phase 1: Main Posts from Profile (https://x.com/BradMcA - where all 4,343+ posts live)
            if mode in ("all", "posts", "main_only"):
                log_info("\n" + "="*60)
                log_info(f"PHASE 1: Deleting Main Profile Posts from {main_posts_url}")
                log_info("="*60)
                main_deleted, main_reposts = cleanup_posts_timeline(page, my_handle, main_posts_url, "Main Posts (Profile)", min_delay, max_delay)
                deleted_posts += main_deleted
                undone_reposts += main_reposts

            # Phase 2: Replies in Threads (https://x.com/BradMcA/with_replies)
            if mode in ("all", "posts", "replies_only") and not page.is_closed():
                log_info("\n" + "="*60)
                log_info(f"PHASE 2: Deleting Thread Replies from {replies_url}")
                log_info("="*60)
                rep_deleted, rep_reposts = cleanup_posts_timeline(page, my_handle, replies_url, "Replies", min_delay, max_delay)
                deleted_posts += rep_deleted
                undone_reposts += rep_reposts

            # Phase 3: Likes / Hearts (https://x.com/i/history/likes)
            if mode in ("all", "likes") and not page.is_closed():
                log_info("\n" + "="*60)
                log_info("PHASE 3: Un-hearting Liked Posts (Clearing Likes)")
                log_info("="*60)
                unhearted_likes = cleanup_likes(page, my_handle, min_delay, max_delay)

            # Print Final Summary
            print("\n" + f"{Fore.CYAN}=============================================================")
            print(f"{Fore.CYAN}                 TWITTER / X CLEANUP SUMMARY                 ")
            print(f"{Fore.CYAN}=============================================================")
            if mode in ("all", "posts", "main_only", "replies_only"):
                print(f"{Fore.GREEN}  - Posts & Replies Deleted : {deleted_posts}")
                print(f"{Fore.GREEN}  - Reposts Undone          : {undone_reposts}")
            if mode in ("all", "likes"):
                print(f"{Fore.GREEN}  - Likes Un-hearted        : {unhearted_likes}")
            print(f"{Fore.CYAN}=============================================================\n")

        finally:
            try:
                context.close()
            except Exception:
                pass
