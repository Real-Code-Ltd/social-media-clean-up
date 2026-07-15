import os
import sys
from colorama import Fore, Style, init

# Add local path to import configs and modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TWITTER_USER_DATA, FACEBOOK_USER_DATA
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

def main():
    print_banner()
    
    while True:
        print(f"{Fore.WHITE}Please select a social media channel to clean up:")
        print(f"  {Fore.GREEN}1. Twitter / X")
        print(f"  {Fore.GREEN}2. Facebook")
        print(f"  {Fore.RED}3. Exit")
        
        choice = input(f"\n{Fore.WHITE}Enter selection (1, 2, or 3): ").strip()
        
        if choice == "1":
            print(f"\n{Fore.YELLOW}Selected: Twitter / X")
            headless_input = input("Run in headless mode? (y/N) (Default: N - recommended to see browser): ").strip().lower()
            headless = True if headless_input == 'y' else False
            
            try:
                run_twitter_cleanup(TWITTER_USER_DATA, headless=headless)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Script terminated by user.")
            except Exception as e:
                print(f"\n{Fore.RED}An error occurred: {e}")
            break
            
        elif choice == "2":
            print(f"\n{Fore.YELLOW}Selected: Facebook")
            headless_input = input("Run in headless mode? (y/N) (Default: N - recommended to see browser): ").strip().lower()
            headless = True if headless_input == 'y' else False
            
            try:
                run_facebook_cleanup(FACEBOOK_USER_DATA, headless=headless)
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
