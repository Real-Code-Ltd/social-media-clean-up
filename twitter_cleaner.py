import asyncio
import time
import random
from playwright.async_api import async_playwright
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

async def get_user_post_info(tweet, user_handle):
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
        user_name_boxes = await tweet.locator('[data-testid="User-Name"]').all()
        if not user_name_boxes:
            return True, 0, "unknown"
            
        first_author = ""
        for idx, box in enumerate(user_name_boxes):
            links = await box.locator('a[href]').all()
            for link in links:
                href = (await link.get_attribute("href") or "").strip("/").lower()
                clean_handle = href.split("/")[0]
                if clean_handle and clean_handle not in ("home", "explore", "notifications", "messages"):
                    if not first_author:
                        first_author = clean_handle
                    if clean_handle == user_handle:
                        return True, idx, user_handle
                        
            text = (await box.inner_text()).lower()
            if f"@{user_handle}" in text:
                return True, idx, user_handle
                
        return False, -1, first_author or "another user"
    except Exception:
        return True, 0, "unknown"

async def check_login(page):
    """
    Checks if the user is currently logged in on Twitter/X.
    """
    try:
        await page.wait_for_timeout(2000)
        profile_btn = page.locator('[aria-label="Profile"]')
        compose_btn = page.locator('[data-testid="SideNav_NewTweet_Button"]')
        
        p_count = await profile_btn.count()
        c_count = await compose_btn.count()
        if p_count > 0 or c_count > 0:
            return True
        return False
    except Exception:
        return False

async def wait_for_user_login(page):
    """
    Prompts the user to log in if they are not already logged in.
    """
    log_info("Navigating to https://x.com/ ...")
    await page.goto("https://x.com/")
    
    if await check_login(page):
        log_success("Logged in automatically via saved session!")
        return True
    
    log_warn("No active session found. Please log in manually in the browser window.")
    log_info("Once you are logged in and see your home timeline, return here and press ENTER to continue...")
    
    for _ in range(100): # 5 minutes max auto-check
        if page.is_closed():
            return False
        if await check_login(page):
            log_success("Login detected! Proceeding...")
            return True
        await page.wait_for_timeout(3000)
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input, "Press Enter to verify login and continue...")
    if await check_login(page):
        log_success("Login verified!")
        return True
    else:
        log_error("Could not verify login. Please try again.")
        return False

async def reload_twitter_page(page, tag, color):
    """
    Reloads the current Twitter tab, waits for hydration, and handles cookie consent.
    """
    print(f"{color}[{tag}] 2 minutes elapsed. Refreshing tab to clear any sticking behavior...{Style.RESET_ALL}")
    try:
        await page.reload()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3500)
        # Dismiss cookie banner if reappeared
        try:
            cookie_btn = page.locator('button:has-text("Refuse non-essential cookies"), button:has-text("Refuse optional cookies"), button:has-text("Close"), [aria-label="Close"]').first
            if await cookie_btn.count() > 0 and await cookie_btn.is_visible():
                await cookie_btn.click(force=True, timeout=2000)
        except Exception:
            pass
        print(f"{color}[{tag}] Tab refreshed successfully! Resuming cleanup...{Style.RESET_ALL}")
        return True
    except Exception as ref_err:
        if "closed" in str(ref_err).lower() or page.is_closed():
            return False
        log_warn(f"[{tag}] Reload encountered an issue: {ref_err}")
        return True

async def cleanup_posts_timeline(page, my_handle, target_url, tab_label, tag, color, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    """
    Concurrent worker for deleting posts/replies/reposts from a specific timeline URL.
    Runs in its own browser tab.
    """
    print(f"{color}[{tag}] Tab opening: Navigating to {target_url} ...{Style.RESET_ALL}")
    try:
        await page.goto(target_url)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)
    except Exception as e:
        if "closed" in str(e).lower():
            print(f"{color}[{tag}] Browser tab closed during navigation.{Style.RESET_ALL}")
            return 0, 0
        print(f"{color}[{tag}] Error navigating: {e}{Style.RESET_ALL}")
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

    print(f"{color}[{tag}] Starting post deletion worker. Pacing: {min_delay:.1f}s - {max_delay:.1f}s{Style.RESET_ALL}")

    while scroll_attempts_without_actions < max_scroll_attempts:
        if page.is_closed():
            print(f"{color}[{tag}] Browser tab closed. Stopping worker.{Style.RESET_ALL}")
            break

        # Check if 2 minutes elapsed since last refresh to prevent sticking
        if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
            if not await reload_twitter_page(page, tag, color):
                break
            last_refresh_time = time.time()
            scroll_attempts_without_actions = 0
            continue

        # If navigated away from target URL, return back
        if not is_on_target_tab(page.url):
            print(f"{color}[{tag}] Navigated away to {page.url}. Returning to {target_url}...{Style.RESET_ALL}")
            try:
                await page.goto(target_url)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(3000)
            except Exception:
                break
            continue

        tweets = await page.locator('article[data-testid="tweet"]:not([data-cleanup-processed="true"])').all()
        action_taken_in_this_view = False

        for tweet in tweets:
            if page.is_closed():
                break
            if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
                break
            if not is_on_target_tab(page.url):
                print(f"{color}[{tag}] Redirect detected ({page.url}). Breaking to return to timeline...{Style.RESET_ALL}")
                break

            tweet_key = None
            try:
                status_links = await tweet.locator('a[href*="/status/"]').all()
                if status_links:
                    link_elem = status_links[-1] if len(status_links) > 1 else status_links[0]
                    href = await link_elem.get_attribute("href") or ""
                    if "/status/" in href:
                        tweet_key = href.split("/status/")[-1].split("?")[0].split("/")[0]
            except Exception:
                pass
            if not tweet_key:
                try:
                    tweet_key = await tweet.evaluate("el => el.innerText.slice(0, 30)")
                except Exception:
                    tweet_key = str(random.random())

            try:
                await tweet.evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
            except Exception:
                try:
                    await tweet.scroll_into_view_if_needed()
                except Exception:
                    pass
            await page.wait_for_timeout(300)

            try:
                # 1. Check if this is a Repost
                social_context = tweet.locator('[data-testid="socialContext"]')
                is_repost = False
                if await social_context.count() > 0:
                    text = (await social_context.first.inner_text()).lower()
                    if "reposted" in text or "retweeted" in text:
                        is_repost = True

                unretweet_btn = tweet.locator('[data-testid="unretweet"]')
                if await unretweet_btn.count() > 0 or is_repost:
                    print(f"{color}[{tag}] Found repost. Undoing repost...{Style.RESET_ALL}")
                    btn_to_click = unretweet_btn.first if await unretweet_btn.count() > 0 else tweet.locator('[data-testid="retweet"]').first
                    try:
                        await btn_to_click.click(timeout=3000)
                    except Exception:
                        await btn_to_click.click(force=True, timeout=3000)

                    undo_btn = page.locator(
                        '[data-testid="unretweetConfirm"], '
                        '[role="menu"] [role="menuitem"]:has-text("Undo Repost"), '
                        '[role="menu"] [role="menuitem"]:has-text("Undo repost"), '
                        '[data-testid="Dropdown"] [role="menuitem"]:has-text("Undo")'
                    ).first

                    try:
                        await undo_btn.wait_for(state="visible", timeout=3000)
                        await page.wait_for_timeout(250)
                        try:
                            await undo_btn.click(timeout=3000)
                        except Exception:
                            await undo_btn.click(force=True, timeout=3000)

                        try:
                            await undo_btn.wait_for(state="hidden", timeout=3000)
                        except Exception:
                            pass

                        reposts_undone_count += 1
                        action_taken_in_this_view = True
                        print(f"{color}[{tag}] Undone repost #{reposts_undone_count}!{Style.RESET_ALL}")

                        try:
                            await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass

                        delay = random.uniform(min_delay, max_delay)
                        print(f"{color}[{tag}] Pacing: waiting {delay:.1f}s before next action...{Style.RESET_ALL}")
                        await asyncio.sleep(delay)
                        break
                    except Exception as undo_err:
                        print(f"{color}[{tag}] Could not confirm 'Undo Repost': {undo_err}{Style.RESET_ALL}")
                        try:
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass
                        failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                        if failed_attempts[tweet_key] >= 2:
                            try:
                                await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                            except Exception:
                                pass
                        continue

                # 2. Check author across all posts in this thread card
                has_own_post, post_idx, author_name = await get_user_post_info(tweet, my_handle)
                if not has_own_post:
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

                # 3. Otherwise, it's our own post or our reply in this thread. Delete it.
                user_name_boxes = await tweet.locator('[data-testid="User-Name"]').all()
                carets = await tweet.locator('[data-testid="caret"]').all()
                if not carets:
                    carets = await tweet.locator('[aria-label="More"], [aria-label="More actions"]').all()

                if not carets:
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

                if post_idx > 0:
                    if post_idx < len(user_name_boxes):
                        try:
                            await user_name_boxes[post_idx].evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
                            await page.wait_for_timeout(300)
                        except Exception:
                            pass

                caret_btn = carets[post_idx] if post_idx < len(carets) else carets[-1]

                try:
                    await caret_btn.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    await caret_btn.click(timeout=3000)
                except Exception:
                    await caret_btn.click(force=True, timeout=3000)

                dropdown = page.locator('[data-testid="Dropdown"], div[role="menu"]').first
                menu_appeared = False
                try:
                    await dropdown.wait_for(state="visible", timeout=2500)
                    menu_appeared = True
                except Exception:
                    try:
                        await caret_btn.click(force=True, timeout=2000)
                        await dropdown.wait_for(state="visible", timeout=2000)
                        menu_appeared = True
                    except Exception:
                        menu_appeared = False

                if not menu_appeared:
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass
                    failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                    if failed_attempts[tweet_key] >= 2:
                        try:
                            await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass
                    continue

                delete_btn = dropdown.locator('[role="menuitem"]').filter(has_text="Delete").first
                if await delete_btn.count() == 0:
                    delete_btn = dropdown.locator('[data-testid="delete"], [role="menuitem"]:has-text("Delete")').first

                has_delete = False
                try:
                    if await delete_btn.count() > 0 and await delete_btn.is_visible():
                        has_delete = True
                    else:
                        await delete_btn.wait_for(state="visible", timeout=2000)
                        has_delete = True
                except Exception:
                    has_delete = False

                if has_delete:
                    try:
                        await delete_btn.scroll_into_view_if_needed()
                        await delete_btn.click(timeout=3000)
                    except Exception:
                        await delete_btn.click(force=True, timeout=3000)

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
                        await confirm_btn.wait_for(state="visible", timeout=6000)
                        await page.wait_for_timeout(350)
                        try:
                            await confirm_btn.click(timeout=3000)
                        except Exception:
                            await confirm_btn.click(force=True, timeout=3000)

                        try:
                            await confirm_btn.wait_for(state="hidden", timeout=3500)
                        except Exception:
                            pass

                        deleted_count += 1
                        action_taken_in_this_view = True
                        if post_idx > 0:
                            print(f"{color}[{tag}] Deleted reply #{deleted_count}!{Style.RESET_ALL}")
                        else:
                            print(f"{color}[{tag}] Deleted tweet #{deleted_count}!{Style.RESET_ALL}")

                        try:
                            await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                        except Exception:
                            pass

                        delay = random.uniform(min_delay, max_delay)
                        print(f"{color}[{tag}] Pacing: waiting {delay:.1f}s before next post...{Style.RESET_ALL}")
                        await asyncio.sleep(delay)
                        break
                    except Exception as conf_err:
                        print(f"{color}[{tag}] Could not confirm deletion in modal: {conf_err}{Style.RESET_ALL}")
                        try:
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(300)
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass
                        failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                        if failed_attempts[tweet_key] >= 2:
                            try:
                                await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                            except Exception:
                                pass
                        continue
                else:
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

            except Exception as ex:
                err_str = str(ex).lower()
                if "closed" in err_str or page.is_closed():
                    print(f"{color}[{tag}] Browser tab closed. Exiting worker...{Style.RESET_ALL}")
                    return deleted_count, reposts_undone_count
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
                failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                if failed_attempts[tweet_key] >= 2:
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                continue

        if action_taken_in_this_view:
            scroll_attempts_without_actions = 0
        else:
            scroll_attempts_without_actions += 1
            max_allowed_scrolls = 5 if (deleted_count == 0 and reposts_undone_count == 0) else max_scroll_attempts
            if scroll_attempts_without_actions >= max_allowed_scrolls:
                print(f"{color}[{tag}] No more posts found after {scroll_attempts_without_actions} scrolls.{Style.RESET_ALL}")
                break

            print(f"{color}[{tag}] Scrolling down to load more (attempt {scroll_attempts_without_actions}/{max_allowed_scrolls})...{Style.RESET_ALL}")
            try:
                await page.evaluate("window.scrollBy(0, 1200)")
                await page.wait_for_timeout(2500)
            except Exception as e:
                if "closed" in str(e).lower():
                    break

    print(f"{color}[{tag}] Worker finished: {deleted_count} deleted, {reposts_undone_count} reposts undone.{Style.RESET_ALL}")
    return deleted_count, reposts_undone_count

async def cleanup_likes(page, my_handle, tag="LIKES", color=Fore.MAGENTA, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    """
    Concurrent worker for un-hearting all liked posts.
    Runs in its own browser tab.
    """
    target_likes_url = f"https://x.com/{my_handle}/likes"
    print(f"{color}[{tag}] Tab opening: Navigating to {target_likes_url} ...{Style.RESET_ALL}")
    try:
        await page.goto(target_likes_url)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)
    except Exception as e:
        if "closed" in str(e).lower():
            print(f"{color}[{tag}] Browser tab closed during navigation.{Style.RESET_ALL}")
            return 0
        print(f"{color}[{tag}] Error navigating: {e}{Style.RESET_ALL}")
        return 0

    def is_on_likes_page(url):
        u = (url or "").lower()
        return "/likes" in u or "/i/history/likes" in u

    active_likes_url = page.url if is_on_likes_page(page.url) else target_likes_url
    print(f"{color}[{tag}] Active Likes URL: {active_likes_url}{Style.RESET_ALL}")

    unheart_count = 0
    scroll_attempts_without_actions = 0
    max_scroll_attempts = 10
    failed_attempts = {}
    last_refresh_time = time.time()

    print(f"{color}[{tag}] Starting Likes (hearts) worker. Pacing: {min_delay:.1f}s - {max_delay:.1f}s{Style.RESET_ALL}")

    while scroll_attempts_without_actions < max_scroll_attempts:
        if page.is_closed():
            print(f"{color}[{tag}] Browser tab closed. Stopping worker.{Style.RESET_ALL}")
            break

        # Check if 2 minutes elapsed since last refresh to prevent sticking
        if time.time() - last_refresh_time >= PAGE_REFRESH_INTERVAL:
            if not await reload_twitter_page(page, tag, color):
                break
            last_refresh_time = time.time()
            scroll_attempts_without_actions = 0
            continue

        # If navigated away from likes entirely, return back
        if not is_on_likes_page(page.url):
            print(f"{color}[{tag}] Navigated away to {page.url}. Returning to likes: {active_likes_url}...{Style.RESET_ALL}")
            try:
                await page.goto(active_likes_url)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2500)
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
            if await empty_state.count() > 0 and await empty_state.is_visible():
                print(f"{color}[{tag}] All likes have been cleared! Empty likes page detected.{Style.RESET_ALL}")
                break
        except Exception:
            pass

        tweets = await page.locator('article[data-testid="tweet"]:not([data-cleanup-processed="true"])').all()
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
                status_links = await tweet.locator('a[href*="/status/"]').all()
                if status_links:
                    link_elem = status_links[-1] if len(status_links) > 1 else status_links[0]
                    href = await link_elem.get_attribute("href") or ""
                    if "/status/" in href:
                        tweet_key = href.split("/status/")[-1].split("?")[0].split("/")[0]
            except Exception:
                pass
            if not tweet_key:
                try:
                    tweet_key = await tweet.evaluate("el => el.innerText.slice(0, 30)")
                except Exception:
                    tweet_key = str(random.random())

            try:
                await tweet.evaluate("el => el.scrollIntoView({ block: 'center', inline: 'nearest' })")
            except Exception:
                try:
                    await tweet.scroll_into_view_if_needed()
                except Exception:
                    pass
            await page.wait_for_timeout(250)

            try:
                # Find unlike button (red/filled heart)
                unlike_btn = tweet.locator('[data-testid="unlike"]').first
                if await unlike_btn.count() == 0:
                    unlike_btn = tweet.locator('[aria-label*="Liked"], [aria-label*="Unlike"]').first

                if await unlike_btn.count() > 0 and await unlike_btn.is_visible():
                    try:
                        await unlike_btn.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    try:
                        await unlike_btn.click(timeout=2500)
                    except Exception:
                        await unlike_btn.click(force=True, timeout=2500)

                    await page.wait_for_timeout(350)

                    # If click accidentally navigated into status page, return to likes
                    if "/status/" in page.url:
                        await page.goto(active_likes_url)
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(2000)

                    unheart_count += 1
                    action_taken_in_this_view = True
                    print(f"{color}[{tag}] Un-hearted post #{unheart_count}!{Style.RESET_ALL}")

                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass

                    delay = random.uniform(min_delay, max_delay)
                    print(f"{color}[{tag}] Pacing: waiting {delay:.1f}s before next un-heart...{Style.RESET_ALL}")
                    await asyncio.sleep(delay)
                    break
                else:
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                    continue

            except Exception as ex:
                err_str = str(ex).lower()
                if "closed" in err_str or page.is_closed():
                    print(f"{color}[{tag}] Browser tab closed. Stopping worker...{Style.RESET_ALL}")
                    return unheart_count
                failed_attempts[tweet_key] = failed_attempts.get(tweet_key, 0) + 1
                if failed_attempts[tweet_key] >= 2:
                    try:
                        await tweet.evaluate("el => el.setAttribute('data-cleanup-processed', 'true')")
                    except Exception:
                        pass
                continue

        if action_taken_in_this_view:
            scroll_attempts_without_actions = 0
        else:
            scroll_attempts_without_actions += 1
            print(f"{color}[{tag}] Scrolling down to load more likes (attempt {scroll_attempts_without_actions}/{max_scroll_attempts})...{Style.RESET_ALL}")
            try:
                await page.evaluate("window.scrollBy(0, 1200)")
                await page.wait_for_timeout(2500)
            except Exception as e:
                if "closed" in str(e).lower():
                    break

    print(f"{color}[{tag}] Worker finished: Total un-hearted: {unheart_count}{Style.RESET_ALL}")
    return unheart_count

async def _async_run_twitter_cleanup(user_data_dir, headless=False, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY, mode="all"):
    """
    Internal asynchronous controller managing browser lifecycle and concurrent tabs.
    """
    log_info("Starting Twitter/X Concurrent Cleanup Engine...")
    log_info(f"Pacing: {min_delay:.1f}s - {max_delay:.1f}s per tab.")
    
    async with async_playwright() as p:
        log_info(f"Launching browser with profile: {user_data_dir}")
        args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        ignore_default_args = ["--enable-automation"]
        
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome",
                args=args,
                ignore_default_args=ignore_default_args,
                no_viewport=True
            )
        except Exception:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                args=args,
                ignore_default_args=ignore_default_args,
                no_viewport=True
            )
        
        try:
            page1 = context.pages[0] if context.pages else await context.new_page()
            
            # Handle login on initial page
            if not await wait_for_user_login(page1):
                await context.close()
                return
            
            # Detect user handle
            log_info("Detecting user profile handle...")
            my_handle = None
            profile_url = None
            
            for _ in range(5):
                try:
                    profile_link = page1.locator('[aria-label="Profile"]').first
                    if await profile_link.count() > 0:
                        href = await profile_link.get_attribute("href")
                        if href and href != "/profile" and href != "/":
                            my_handle = href.strip("/").lower()
                            profile_url = f"https://x.com{href}"
                            break
                except Exception:
                    pass
                await page1.wait_for_timeout(800)

            if not my_handle:
                try:
                    profile_btn = page1.locator('[aria-label="Profile"]').first
                    if await profile_btn.count() > 0:
                        await profile_btn.click(force=True)
                        await page1.wait_for_load_state("domcontentloaded")
                        for _ in range(8):
                            if "/profile" not in page1.url and "/home" not in page1.url:
                                profile_url = page1.url
                                path_parts = [p for p in profile_url.split("x.com/")[-1].split("twitter.com/")[-1].split("/") if p]
                                if path_parts and path_parts[0] not in ("profile", "home", "explore"):
                                    my_handle = path_parts[0].lower()
                                    break
                            await page1.wait_for_timeout(500)
                except Exception:
                    pass

            if not my_handle and profile_url:
                path_parts = [p for p in profile_url.split("x.com/")[-1].split("twitter.com/")[-1].split("/") if p]
                if path_parts and path_parts[0] not in ("profile", "home", "explore"):
                    my_handle = path_parts[0].lower()

            if not my_handle:
                loop = asyncio.get_running_loop()
                my_handle = (await loop.run_in_executor(None, input, f"\n{Fore.YELLOW}Could not auto-detect your handle. Enter handle (without @): ")).strip().lstrip("@").lower()

            log_info(f"Targeting Twitter account: @{my_handle}")

            main_posts_url = f"https://x.com/{my_handle}"
            replies_url = f"https://x.com/{my_handle}/with_replies"

            tasks = []
            tab_roles = [] # (type, tag)

            if mode == "all":
                log_info("\n" + "="*65)
                log_info("MULTI-TAB CLEANUP ACTIVATED: Spawning 3 tabs concurrently:")
                print(f"  {Fore.GREEN}Tab 1 [POSTS]   : Main Profile Posts ({main_posts_url})")
                print(f"  {Fore.CYAN}Tab 2 [REPLIES] : Thread Replies ({replies_url})")
                print(f"  {Fore.MAGENTA}Tab 3 [LIKES]   : Likes / Hearts (https://x.com/i/history/likes)")
                log_info("="*65 + "\n")

                page2 = await context.new_page()
                page3 = await context.new_page()

                tasks.append(cleanup_posts_timeline(page1, my_handle, main_posts_url, "Main Posts (Profile)", "POSTS", Fore.GREEN, min_delay, max_delay))
                tab_roles.append("posts")

                tasks.append(cleanup_posts_timeline(page2, my_handle, replies_url, "Thread Replies", "REPLIES", Fore.CYAN, min_delay, max_delay))
                tab_roles.append("replies")

                tasks.append(cleanup_likes(page3, my_handle, "LIKES", Fore.MAGENTA, min_delay, max_delay))
                tab_roles.append("likes")

            elif mode == "posts":
                log_info("\n" + "="*65)
                log_info("MULTI-TAB CLEANUP ACTIVATED: Spawning 2 tabs concurrently:")
                print(f"  {Fore.GREEN}Tab 1 [POSTS]   : Main Profile Posts ({main_posts_url})")
                print(f"  {Fore.CYAN}Tab 2 [REPLIES] : Thread Replies ({replies_url})")
                log_info("="*65 + "\n")

                page2 = await context.new_page()

                tasks.append(cleanup_posts_timeline(page1, my_handle, main_posts_url, "Main Posts (Profile)", "POSTS", Fore.GREEN, min_delay, max_delay))
                tab_roles.append("posts")

                tasks.append(cleanup_posts_timeline(page2, my_handle, replies_url, "Thread Replies", "REPLIES", Fore.CYAN, min_delay, max_delay))
                tab_roles.append("replies")

            elif mode == "main_only":
                log_info(f"\nSingle Tab: Deleting Main Profile Posts from {main_posts_url} ...")
                tasks.append(cleanup_posts_timeline(page1, my_handle, main_posts_url, "Main Posts (Profile)", "POSTS", Fore.GREEN, min_delay, max_delay))
                tab_roles.append("posts")

            elif mode == "likes":
                log_info("\nSingle Tab: Un-hearting Likes from https://x.com/i/history/likes ...")
                tasks.append(cleanup_likes(page1, my_handle, "LIKES", Fore.MAGENTA, min_delay, max_delay))
                tab_roles.append("likes")

            # Run all tabs concurrently!
            try:
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            except (KeyboardInterrupt, asyncio.CancelledError):
                for t in tasks:
                    if not t.done():
                        t.cancel()
                return

            deleted_posts = 0
            undone_reposts = 0
            unhearted_likes = 0

            for role, res in zip(tab_roles, raw_results):
                if isinstance(res, Exception):
                    if "closed" not in str(res).lower() and not isinstance(res, (asyncio.CancelledError, KeyboardInterrupt)):
                        log_warn(f"Tab {role} encountered an error: {res}")
                elif role in ("posts", "replies"):
                    del_cnt, rep_cnt = res
                    deleted_posts += del_cnt
                    undone_reposts += rep_cnt
                elif role == "likes":
                    unhearted_likes += res

            # Print Final Combined Summary
            print("\n" + f"{Fore.CYAN}=============================================================")
            print(f"{Fore.CYAN}                 TWITTER / X CLEANUP SUMMARY                 ")
            print(f"{Fore.CYAN}=============================================================")
            print(f"{Fore.GREEN}  - Total Posts & Replies Deleted : {deleted_posts}")
            print(f"{Fore.GREEN}  - Total Reposts Undone          : {undone_reposts}")
            print(f"{Fore.MAGENTA}  - Total Likes Un-hearted        : {unhearted_likes}")
            print(f"{Fore.CYAN}=============================================================\n")

        finally:
            try:
                await context.close()
            except Exception:
                pass

def run_twitter_cleanup(user_data_dir, headless=False, min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY, mode="all"):
    """
    Synchronous entrypoint called by main.py that runs the async multi-tab engine.
    """
    try:
        asyncio.run(_async_run_twitter_cleanup(user_data_dir, headless=headless, min_delay=min_delay, max_delay=max_delay, mode=mode))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n{Fore.YELLOW}Cleanup terminated by user.")
    except Exception as e:
        if "closed" in str(e).lower():
            print(f"\n{Fore.CYAN}Browser window closed. Cleanup ended.")
        else:
            print(f"\n{Fore.RED}An error occurred: {e}")
