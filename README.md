# 🧹 Social Media Cleanup Tool 🧹

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-v1.40%2B-green.svg)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy First](https://img.shields.io/badge/Privacy-100%25%20Local-success.svg)](#-privacy--security-by-design)
[![Zero Telemetry](https://img.shields.io/badge/Telemetry-Zero%20Data%20Collected-brightgreen.svg)](#-privacy--security-by-design)

An industrial-grade, privacy-first automation suite designed to **completely erase your historical social media activity** across **Twitter (X)** and **Facebook**. Reclaim your personal privacy, scrub your digital footprint, eliminate old posts, un-heart likes, and take back control of your online presence! 🚀

---

## 🏷️ Keywords & Privacy Pillars

`Digital Footprint Removal` • `Privacy Protection` • `Social Media Wipe` • `Delete Old Tweets` • `Bulk Post Deletion` • `Mass Unlike` • `Twitter History Eraser` • `Facebook Activity Log Cleaner` • `Right to Be Forgotten` • `Anti-Doxxing` • `Scrape Protection` • `Playwright Automation` • `Zero Telemetry` • `Local Execution` • `Multi-Threading Concurrency`

### Why Digital Privacy Matters
Social media platforms archive your public posts, conversation replies, political opinions, locations, and personal reactions indefinitely. This data is constantly indexed by search engines, scraped by third-party data brokers, and used to train AI models or build behavioral profiles. 

This tool empowers you with **true data sovereignty**:
* **Complete Activity Scrubbing**: Permanently deletes posts, thread comments, reposts/retweets, likes, and reactions.
* **100% Local & Private**: Operates exclusively in your local browser instance. No external API keys, no third-party servers, no telemetry, and zero credentials shared.
* **Massive Volume Ready**: Built to effortlessly process accounts with 5,000+ posts without timing out or sticking.

---

## 📑 Table of Contents
1. [Platform Features: Twitter / X](#-twitter--x-cleanup-engine)
2. [Platform Features: Facebook](#-facebook-cleanup-engine)
3. [Core Security & Architecture](#-privacy--security-by-design)
4. [Installation & Prerequisites](#-getting-started)
5. [Twitter / X Step-by-Step Instructions](#-twitter--x-instructions)
6. [Facebook Step-by-Step Instructions](#-facebook-instructions)
7. [Speed & Pacing Profiles](#-speed--pacing-profiles)
8. [License](#-license)

---

## 🐦 Twitter / X Cleanup Engine

Engineered specifically to solve the hurdles of high-volume Twitter/X accounts (such as accounts with 4,800+ historical posts, deeply nested replies, and sticky virtualized feeds).

### Key Twitter / X Capabilities
* **⚡ 3-Tab Concurrent Multi-Threading**:
  * **Tab 1 `[POSTS]`**: Cleans your primary profile feed (`https://x.com/your_handle`) to purge all original posts.
  * **Tab 2 `[REPLIES]`**: Targets your conversation replies and thread comments (`https://x.com/your_handle/with_replies`).
  * **Tab 3 `[LIKES]`**: Un-hearts all your liked posts on your likes timeline (`https://x.com/i/history/likes`).
  * *All 3 streams run simultaneously in parallel browser tabs within a single session.*
* **🚀 Turbo API Direct GraphQL Deletion**:
  * Automatically intercepts authenticated session credentials from the first action and executes subsequent deletions via direct in-browser GraphQL calls (`DeleteTweet` / `UnfavoriteTweet`).
  * Cuts deletion latency from ~4.5 seconds down to **~0.3s–0.5s per post** while maintaining direct HTTP 200 GraphQL verification.
* **🚫 Zero-Delay CSS Toast & Notification Suppression**:
  * Injects custom CSS rules to eliminate Twitter's floating notification banner (`data-testid="toast"` `"Your post was deleted. View"`), which otherwise blocks clicks on subsequent post menus for 4–5 seconds.
  * Drops menu and modal CSS transition durations to `0.001s` for instant UI responsiveness.
* **🔄 2-Minute Anti-Sticking Safeguard**:
  * Automatically refreshes tabs every 120 seconds to clear browser memory leaks, flush React DOM bloat, and bypass virtualized feed sticking.
* **🛡️ Dual-Layer Verification**:
  * Verifies every deletion using two signals: direct HTTP 200 response from Twitter's GraphQL endpoint AND physical DOM detachment of the tweet element.
* **🔁 Undo Reposts / Retweets**:
  * Detects and undoes Retweets/Reposts seamlessly in the timeline stream.

---

## 📘 Facebook Cleanup Engine

Designed to automate the removal of interactions across Facebook's activity management interface.

### Key Facebook Capabilities
* **📰 Activity Log Automation**:
  * Directly automates Facebook's **Comments & Reactions Activity Log** (`YOURACTIVITYCOMMENTSANDREACTIONSSCHEMA`).
* **🎯 Multi-Action Disappearance Engine**:
  * Detects and executes context-specific options:
    * `Delete` / `Remove` (for comments and wall posts)
    * `Unlike` / `Remove reaction` (for reactions and likes)
    * `Remove tag` (for tagged content)
* **🔍 Modal & Confirmation Handling**:
  * Automatically detects and confirms secondary Facebook confirmation dialogs (`div[role="dialog"]`).
* **✅ Verified State Changes**:
  * Waits up to 8 seconds for the target row to disappear completely from the DOM before advancing, ensuring thorough deletion.
* **🔒 Persistent Saved Session**:
  * Logs in once using Playwright's persistent Chromium context—no need to enter your Facebook password repeatedly.

---

## 🔒 Privacy & Security by Design

* **Safe for Public Repositories**:
  * The codebase contains **zero personal handles, usernames, passwords, cookies, or API keys**.
  * All browser cache, local storage, cookies, and session states reside in `.user_data/`, which is permanently ignored by `.gitignore`.
* **No Developer Accounts or API Fees**:
  * Avoids Twitter's costly enterprise API fees and Facebook's restricted Graph API permissions by automating your own browser session directly.
* **Transparent Codebase**:
  * Pure Python with open-source dependencies ([Playwright](https://playwright.dev/python/), [Colorama](https://pypi.org/project/colorama/)). No obfuscated scripts.

---

## 🛠️ Technology Stack

* **Language**: Python 3.8+
* **Engine**: [Playwright](https://playwright.dev/python/) (driving Chromium / Google Chrome)
* **Concurrency**: `asyncio` for multi-tab simultaneous execution
* **Terminal UI**: [Colorama](https://pypi.org/project/colorama/) with color-coded multi-stream logging:
  * `[POSTS]` in Green
  * `[REPLIES]` in Cyan
  * `[LIKES]` in Magenta
  * `[FACEBOOK]` in Blue

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.8 or higher installed on your system.

### 2. Clone the Repository
```bash
git clone https://github.com/Real-Code-Ltd/social-media-clean-up.git
cd social-media-clean-up
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 4. Launch the Application
```bash
python main.py
```

---

## 🐦 Twitter / X Instructions

### Step 1: Select Platform
Choose `1. Twitter / X` from the main menu.

### Step 2: Choose Browser Visibility
* `N` **(Default & Recommended)**: Visible browser window. Allows you to observe the cleanup live.
* `y`: Headless mode (silent background execution).

### Step 3: Log In (First Run Only)
If you are not already logged into Twitter/X, a browser window will open to `https://x.com/login`. Log in manually. Once logged in, your session is saved locally in `.user_data/twitter_profile` and will never ask you to log in again.

### Step 4: Choose Activity Stream
* `1. All Activity [Multi-Tab: 3 Concurrent Tabs]` **[Default]**:
  * Launches 3 tabs simultaneously: Main Posts, Thread Replies, and Likes.
* `2. Main Profile Posts only [1 Tab]`:
  * Focuses exclusively on deleting your original posts from your main profile feed.
* `3. Posts & Replies [Multi-Tab: 2 Concurrent Tabs]`:
  * Cleans all posts and thread replies across 2 tabs without unliking.
* `4. Likes / Hearts only [1 Tab]`:
  * Cleans only your likes/hearts history.

### Step 5: Select Speed / Pacing
Select `1. Turbo Mode` (0.3s - 0.5s delay) for high-speed deletion, or choose a steady human-like pace.

---

## 📘 Facebook Instructions

### Step 1: Select Platform
Choose `2. Facebook` from the main menu.

### Step 2: Log In (First Run Only)
If not logged in, the browser opens `https://www.facebook.com/`. Log in manually. Your session is saved locally in `.user_data/facebook_profile` for future runs. Press <kbd>Enter</kbd> in your terminal once your home feed is visible.

### Step 3: Automatic Activity Log Cleanup
The tool navigates directly to your Facebook Activity Log for Comments & Reactions. It will systematically:
1. Open the action menu for each item.
2. Click `Unlike`, `Delete`, `Remove reaction`, or `Remove tag`.
3. Confirm any secondary prompt.
4. Verify the item has disappeared from your history.
5. Scroll down automatically when new items need to be loaded.

---

## ⚡ Speed & Pacing Profiles

| Mode | Delay Range | Description |
| :--- | :--- | :--- |
| **🚀 Turbo Mode [Default]** | **0.3s – 0.5s** | Direct GraphQL API batch deletion + zeroed CSS animations. Cleans 1,000+ posts in minutes. |
| **⚡ Fast** | **1.0s** | 1-second fixed pacing between actions. |
| **⚖️ Moderate** | **1.5s – 2.5s** | Balanced pacing mimicking active human browsing. |
| **🛡️ Safe & Steady** | **2.5s – 4.5s** | Conservative pacing recommended for cautious accounts. |
| **⚙️ Custom** | *User-defined* | Define custom minimum and maximum delays in seconds. |

> **Emergency Stop**: Press <kbd>Ctrl+C</kbd> in your terminal at any time to pause or cancel the cleanup loop cleanly.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
