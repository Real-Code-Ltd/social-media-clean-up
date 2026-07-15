# 🧹 Social Media Cleanup Tool 🧹

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-v1.40%2B-green.svg)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated, privacy-first command-line tool to sweep away your past post history on **Twitter (X)** and **Facebook**. Take control of your digital footprint, clean up your profile, and start fresh! 🚀

---

## 🌟 Key Features

*   **Dual Platform Support**: Clean up both **Twitter/X** (tweets and reposts) and **Facebook** posts.
*   **One-Time Sign In**: Uses a secure local persistent browser profile. You only log in once; future runs bypass authentication automatically!
*   **Local & Secure**: Absolutely zero database connections or remote servers. All your cookies and credentials remain 100% on your machine.
*   **Human-Like Interaction**: Incorporates random pacing (2–5 seconds delay) and real-time scrolling to prevent accounts from getting flagged or rate-limited.
*   **Vibrant Terminal Feedback**: Interactive CLI with color-coded status messages so you know exactly what the automation is doing.

---

## 🔒 Security Design (Local & Private)

Your privacy is the highest priority. Unlike third-party social media cleanup services:
*   **No API Tokens Required**: You don't need to register developer accounts or grant broad API permissions.
*   **Local Browser Profile Storage**: Credentials and session states (cookies, local storage, etc.) are saved directly on your computer inside the `.user_data/` directory.
*   **No Third-Party Access**: The script never transmits your login information or data to any external server. 
*   **Safe Execution**: Run in headful mode to watch exactly what the script is doing and verify that it only interacts with the delete options.

---

## 🛠️ Technology Stack

*   **Python 3**: The core application logic.
*   **Playwright (Python)**: High-performance browser automation library. It runs a chromium instance to interact with the web elements just like a human would.
*   **Colorama**: Python library to colorize terminal text, providing clear visual progress indicators (`[SUCCESS]`, `[INFO]`, `[WARN]`, `[ERROR]`).

---

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have Python installed, then clone the repository:
```bash
git clone https://github.com/Real-Code-Ltd/social-media-clean-up.git
cd social-media-clean-up
```

### 2. Install Dependencies
Install the required packages and setup the Playwright browser:
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Usage
Run the main script and follow the on-screen menu:
```bash
python main.py
```

### 4. Interactive Flow
1.  **Select the channel** to clean up:
    *   `1` for Twitter/X
    *   `2` for Facebook
2.  Choose whether to run in **headless mode** (running in the background). *Note: The first time you run the tool for a platform, choose `N` (headful mode) to open the browser window and log in manually.*
3.  Sign in to your account. The automation will pause and wait. Once signed in, it will automatically navigate to your profile and begin the cleanup process!
4.  Press `Ctrl+C` in your terminal at any time to pause or stop the deletion loop.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
