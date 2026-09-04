# 🧹 Social Media Cleanup Tool 🧹

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-v1.40%2B-green.svg)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated, privacy-first command-line tool to sweep away your past post history, replies, and likes on **Twitter (X)** and **Facebook**. Take control of your digital footprint, clean up your profile, and start fresh! 🚀

---

## 🌟 Key Features

*   **⚡ Multi-Tab Concurrent Engine (New!)**:
    *   **Tab 1 `[POSTS]`**: Targets your main profile timeline (`https://x.com/your_handle`) to delete all your primary posts (tested on profiles with 4,000+ historical posts).
    *   **Tab 2 `[REPLIES]`**: Deletes your conversation replies and comments in other users' threads (`/with_replies`).
    *   **Tab 3 `[LIKES]`**: Un-hearts all your liked posts on your likes timeline (`/i/history/likes`).
    *   All 3 tabs run simultaneously side-by-side in the same browser session to dramatically accelerate cleanup.
*   **🚀 Turbo API Direct Deletion & Toast Suppression (New!)**:
    *   **In-Browser GraphQL API**: Automatically captures authenticated session credentials from the first action and executes subsequent deletions via direct in-browser GraphQL calls (`DeleteTweet` / `UnfavoriteTweet`), cutting deletion time per post from ~4s down to ~0.3s.
    *   **Zero Banner Interference**: Automatically suppresses Twitter's floating notification toast banner (`data-testid="toast"`) and zeroes out CSS transition delays so animations and popups never block clicks or viewports.
    *   **Sequential View Processing**: Deletes all visible tweets in a viewport batch without reloading or re-querying the whole DOM from scratch.
*   **❤️ Complete Likes & Hearts Removal**: Automatically removes all your past likes/hearts without confirmation fatigue.
*   **⏱️ 2-Minute Sticking Safeguard**: Every 2 minutes, the active tabs automatically refresh to flush browser memory leaks, clear virtualized timeline sticking, and ensure steady progress through massive post histories.
*   **🛡️ Human-Like & Turbo Pacing Options**:
    *   **Turbo Mode [Default]**: 0.3s – 0.5s delay (Ideal for 1,000+ posts).
    *   **Fast**: 1.0s delay.
    *   **Moderate**: 1.5s – 2.5s delay.
    *   **Safe & Steady**: 2.5s – 4.5s delay.
    *   **Custom**: User-defined minimum and maximum delay.
*   **🔐 One-Time Sign In**: Uses Playwright's local persistent browser profile. You only log in once in the visible browser; future runs remember your session automatically!
*   **🎨 Vibrant Color-Coded Terminal Dashboard**: Real-time terminal feedback color-coded per stream:
    *   `[POSTS]` in Green
    *   `[REPLIES]` in Cyan
    *   `[LIKES]` in Magenta
*   **📘 Dual Platform Support**: Full support for both **Twitter / X** and **Facebook**.

---

## 🔒 Security & Privacy (Safe for Public Repositories)

Your security and privacy are 100% protected:
*   **Zero Remote Servers**: No database connections, telemetry, external analytics, or cloud APIs. Everything runs strictly on your local machine.
*   **No API Tokens Required**: You do not need to register developer accounts or grant broad third-party OAuth app permissions.
*   **Strictly Ignored Session Data**: All session cookies, tokens, and browser profiles are stored locally inside the `.user_data/` directory, which is permanently excluded via `.gitignore`.
*   **Audit Verified**: The repository contains zero hardcoded credentials, usernames, passwords, or session tokens, making it completely safe to be public.

---

## 🛠️ Technology Stack

*   **Python 3.8+**: Application logic and asynchronous concurrency (`asyncio`).
*   **Playwright (Python)**: High-performance browser automation driving Chromium / Google Chrome with native multi-tab support.
*   **Colorama**: Terminal styling and color-coded status reporting.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.8 or higher installed, then clone the repository:
```bash
git clone https://github.com/Real-Code-Ltd/social-media-clean-up.git
cd social-media-clean-up
```

### 2. Install Dependencies
Install the required packages and install the Playwright browser binaries:
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Usage
Run the tool directly from your terminal:
```bash
python main.py
```

---

## 🎮 Interactive Menu Flow

When launched, the interactive CLI allows you to press <kbd>Enter</kbd> to accept recommended defaults or customize your cleanup:

1.  **Select Channel** `[Default: 1 - Twitter / X]`:
    *   `1. Twitter / X`
    *   `2. Facebook`
    *   `3. Exit`
2.  **Headless Mode** `[Default: N - Visible Browser]`:
    *   `N` (Recommended): Keeps the browser visible so you can watch the automation in real time.
    *   `y`: Runs silently in the background.
3.  **Activity Mode (Twitter/X)** `[Default: 1 - All Activity Multi-Tab]`:
    *   `1. All Activity [Multi-Tab: 3 Concurrent Tabs]`: Main profile posts, thread replies, and likes all cleaned together.
    *   `2. Main Profile Posts only [1 Tab]`: Targets only your main profile posts (`https://x.com/your_handle`).
    *   `3. Posts & Replies [Multi-Tab: 2 Concurrent Tabs]`: Cleans all tweets and thread replies.
    *   `4. Likes / Hearts only [1 Tab]`: Cleans only your likes/hearts history.
4.  **Speed Selection** `[Default: 1 - Turbo Mode]`:
    *   `1. Turbo Mode` (0.3s – 0.5s delay - Recommended for 1000+ posts) `[Default]`
    *   `2. Fast` (1.0s delay)
    *   `3. Moderate` (1.5s – 2.5s delay)
    *   `4. Safe & Steady` (2.5s – 4.5s delay)
    *   `5. Custom Delay` (specify min/max seconds)

> **Tip**: Press <kbd>Ctrl+C</kbd> in your terminal at any time to pause or stop the cleanup loop safely.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
