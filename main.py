import os
import sys
from colorama import Fore, Style, init

# Add local path to import configs and modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TWITTER_USER_DATA, FACEBOOK_USER_DATA, DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY
from twitter_cleaner import run_twitter_cleanup
from facebook_cleaner import run_facebook_cleanup

# Initialize colorama for beautiful terminal output
init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.CYAN}=============================================================
{Fore.CYAN}            SOCIAL MEDIA POST CLEANER / ARCHIVER            
{Fore.CYAN}=============================================================
{Fore.WHITE}  Automates deleting posts and cleaning up profiles.
  Uses Playwright browser sessions to remember your login.
=============================================================
"""
    print(banner)

def prompt_pacing_selection():
    print(f"\n{Fore.WHITE}Select cleanup speed:")
    print(f"  {Fore.GREEN}1. Fast (1.0s delay - Default)")
    print(f"  {Fore.GREEN}2. Moderate (1.5 - 2.5s delay)")
    print(f"  {Fore.GREEN}3. Safe & Steady (2.5 - 4.5s delay)")
    print(f"  {Fore.GREEN}4. Custom delay")
    
    speed_choice = input(f"{Fore.WHITE}Enter speed selection (1, 2, 3, or 4) [Default: 1]: ").strip()
    
    if speed_choice == "2":
        return 1.5, 2.5
    elif speed_choice == "3":
        return 2.5, 4.5
    elif speed_choice == "4":
        try:
            custom_min = float(input("Enter minimum delay in seconds (e.g. 1.0): ").strip())
            custom_max = float(input("Enter maximum delay in seconds (e.g. 2.0): ").strip())
            if custom_min > 0 and custom_max >= custom_min:
                return custom_min, custom_max
            else:
                print(f"{Fore.YELLOW}Invalid range. Using default Fast delay ({DEFAULT_MIN_DELAY}s).")
        except ValueError:
            print(f"{Fore.YELLOW}Invalid input. Using default Fast delay ({DEFAULT_MIN_DELAY}s).")
            
    return 1.0, 1.0

def prompt_twitter_activity():
    print(f"\n{Fore.WHITE}Select Twitter activity to clean:")
    print(f"  {Fore.GREEN}1. All Activity [Multi-Tab: 3 Concurrent Tabs] (Posts, Replies & Likes) [Default]")
    print(f"  {Fore.GREEN}2. Main Profile Posts only [1 Tab] (Your profile posts from https://x.com/your_handle)")
    print(f"  {Fore.GREEN}3. Posts & Replies [Multi-Tab: 2 Concurrent Tabs] (Main posts and thread replies)")
    print(f"  {Fore.GREEN}4. Likes / Hearts only [1 Tab] (Un-heart all liked posts)")
    
    act_choice = input(f"{Fore.WHITE}Enter activity selection (1, 2, 3, or 4) [Default: 1]: ").strip()
    if act_choice == "2":
        return "main_only"
    elif act_choice == "3":
        return "posts"
    elif act_choice == "4":
        return "likes"
    return "all"

def main():
    print_banner()
    
    while True:
        print(f"{Fore.WHITE}Please select a social media channel to clean up:")
        print(f"  {Fore.GREEN}1. Twitter / X [Default]")
        print(f"  {Fore.GREEN}2. Facebook")
        print(f"  {Fore.RED}3. Exit")
        
        choice = input(f"\n{Fore.WHITE}Enter selection (1, 2, or 3) [Default: 1]: ").strip()
        if not choice:
            choice = "1"
        
        if choice == "1":
            print(f"\n{Fore.YELLOW}Selected: Twitter / X")
            headless_input = input("Run in headless mode? (y/N) (Default: N - recommended to see browser): ").strip().lower()
            headless = True if headless_input == 'y' else False
            
            mode = prompt_twitter_activity()
            min_delay, max_delay = prompt_pacing_selection()
            
            try:
                run_twitter_cleanup(TWITTER_USER_DATA, headless=headless, min_delay=min_delay, max_delay=max_delay, mode=mode)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Script terminated by user.")
            except Exception as e:
                if "closed" in str(e).lower():
                    print(f"\n{Fore.CYAN}Browser window closed. Cleanup ended.")
                else:
                    print(f"\n{Fore.RED}An error occurred: {e}")
            break
            
        elif choice == "2":
            print(f"\n{Fore.YELLOW}Selected: Facebook")
            headless_input = input("Run in headless mode? (y/N) (Default: N - recommended to see browser): ").strip().lower()
            headless = True if headless_input == 'y' else False
            
            min_delay, max_delay = prompt_pacing_selection()
            
            try:
                run_facebook_cleanup(FACEBOOK_USER_DATA, headless=headless, min_delay=min_delay, max_delay=max_delay)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Script terminated by user.")
            except Exception as e:
                print(f"\n{Fore.RED}An error occurred: {e}")
            break
            
        elif choice == "3":
            print(f"\n{Fore.CYAN}Exiting. Have a great day!")
            break
        else:
            print(f"\n{Fore.RED}Invalid selection. Please choose 1, 2, or 3.\n")

if __name__ == "__main__":
    main()
