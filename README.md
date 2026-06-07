# Telegram File Downloader

## Features

- Download files from any Telegram channel you have access to
- Filter downloads by file extension (e.g., .txt, .pdf, .mp3)
- Set time parameters (download files from specified days/hours)
- Save to folder or send to a Discord webhook
- Renaming to avoid dupes

## Requirements

- Python 3.9+
- Telegram account
- Telegram API credentials (API ID and API Hash)
- Optional: Discord webhook

## Setup

1. Get your Telegram credentials from [my.telegram.org/apps](https://my.telegram.org/apps)
2. Update the `API_ID` and `API_HASH` in the file with your credentials


## Usage

1. Run the script:
   ```
   python telegramdl.py
   ```
   - If you don't have the dependancies installed, it will automatically install them for you

2. Follow the prompts:
   - Enter Telegram channel link or ID
   - Specify time frame (e.g., '7d' for 7 days, '24h' for 24 hours, 'all' for all messages)
   - Enter file extension to download (e.g., .txt, .pdf)
   - Choose download method (save to folder or send to webhook)

## Channel Link Formats

The tool accepts various channel formats:
- Channel ID (numeric)
- Username (e.g., 'channelname')
- t.me links (e.g., 't.me/channelname')
- web.telegram.org links (a bit broken i think)
