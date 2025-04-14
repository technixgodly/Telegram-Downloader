import os, re, asyncio, datetime, random, string, logging
from tkinter import Tk, filedialog
try:
    import requests
    from telethon import TelegramClient, events
    from telethon.tl.types import PeerChannel, InputPeerChannel
except ImportError:
    os.system('pip install requests')
    os.system('pip install telethon')
    os.system('cls')
    print('Installed dependencies, please run the tool again.')
    input('Press Enter to exit...')
    exit()


# logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# telegram api credentials
# Get from https://my.telegram.org/apps
API_ID = ENTER YOUR API ID HERE
API_HASH = 'ENTER YOUR API HASH HERE'

# Discord webhook url (you can leave it blank and it will ask for input)
DISCORD_WEBHOOK_URL = None

client = None

async def download_files(channel_entity, time_frame=None, save_path=None, use_webhook=False, file_extension='.txt'):
    """Download files from a channel within the inputted time frame."""
    try:
        if time_frame and time_frame.lower() != "all":
            # (e.g., "7d" for 7 days, "3h" for 3 hours)
            unit = time_frame[-1].lower()
            value = int(time_frame[:-1])
            
            if unit == 'd':
                since_date = datetime.datetime.now() - datetime.timedelta(days=value)
            elif unit == 'h':
                since_date = datetime.datetime.now() - datetime.timedelta(hours=value)
            elif unit == 'm':
                since_date = datetime.datetime.now() - datetime.timedelta(minutes=value)
            else:
                logger.error(f"Invalid time unit: {unit}. Use 'd' for days, 'h' for hours, 'm' for minutes.")
                return
        else:
            since_date = None  # get all messages
        
        downloaded_count = 0
        
        logger.info(f"Downloading files with extension {file_extension} from {getattr(channel_entity, 'title', channel_entity.id)}...")
        
        async for message in client.iter_messages(channel_entity):
            # Skip msgs before the date specified
            if since_date and message.date < since_date.replace(tzinfo=datetime.timezone.utc):
                break
                
            if message.file and message.file.name and message.file.name.endswith(file_extension):
                # rndm str
                random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                
                # get timestamp
                timestamp = message.date.strftime('%Y%m%d_%H%M%S')

                file_name, file_ext = os.path.splitext(message.file.name)
                # append to filename
                unique_file_name = f"{timestamp}_{file_name}_{random_str}{file_ext}"
                
                if use_webhook and DISCORD_WEBHOOK_URL:
                    # temp dir
                    temp_path = await client.download_media(message, f"temp/{unique_file_name}")
                    if temp_path:
                        send_to_discord_webhook(temp_path, unique_file_name)
                        os.remove(temp_path)  # clean up
                        downloaded_count += 1
                else:
                    # Download to path
                    if save_path:
                        full_path = os.path.join(save_path, unique_file_name)
                        await client.download_media(message, full_path)
                        downloaded_count += 1
                        logger.info(f"Downloaded: {unique_file_name} (original: {message.file.name})")
        
        logger.info(f"Download complete. Downloaded {downloaded_count} files with extension {file_extension}.")
    except Exception as e:
        logger.error(f"Error downloading files: {e}")

def parse_channel_link(link_or_id):
    """Parse channel ID from various formats."""
    try:
        # Handle web links
        if "web.telegram.org" in link_or_id:
            # fetch ID
            match = re.search(r'#-?(\d+)', link_or_id)
            if match:
                channel_id = int(match.group(0).replace('#', ''))
                return channel_id
        
        # handle dms
        try:
            channel_id = int(link_or_id)
            if channel_id > 0 and "channel" in link_or_id.lower():
                channel_id = -channel_id
            return channel_id
        except ValueError:
            pass
            
        # Handle t.me links
        if "t.me/" in link_or_id:
            return link_or_id.split("t.me/")[1]
            
        return link_or_id  # return as channel id
    except Exception as e:
        logger.error(f"Error parsing channel link: {e}")
        return link_or_id

def select_folder():
    """Open a folder selection dialog and return the selected path."""
    root = Tk()
    root.withdraw()  # Hide main window
    root.attributes('-topmost', True)  # bring to front
    folder_path = filedialog.askdirectory()
    root.destroy()
    return folder_path

def send_to_discord_webhook(file_path, file_name):
    """Send a file to Discord webhook."""
    try:
        if not DISCORD_WEBHOOK_URL:
            logger.error("Discord webhook URL is not set.")
            return False
            
        with open(file_path, 'rb') as f:
            file_content = f.read()
            
        files = {'file': (file_name, file_content)}
        response = requests.post(DISCORD_WEBHOOK_URL, files=files)
        
        if response.status_code == 200:
            logger.info(f"Successfully sent {file_name} to Discord webhook")
            return True
        else:
            logger.error(f"Failed to send {file_name} to Discord webhook: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error sending file to Discord webhook: {e}")
        return False

async def setup_client():
    """Set up and connect the Telegram client."""
    global client
    
    # init client
    client = TelegramClient('telegram_downloader_session', API_ID, API_HASH)
    await client.start()
    
    if not await client.is_user_authorized():
        logger.info("You need to log in to your Telegram account.")
        logger.info("Please check your Telegram app for the login code and enter it below.")
        try:
            await client.send_code_request(input("Enter your phone number (with country code): "))
            await client.sign_in(code=input("Enter the code you received: "))
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    logger.info("Successfully logged in to Telegram!")
    return True

async def main():
    """Main function to run the downloader."""
    if not API_ID or not API_HASH:
        print("Please set your API_ID and API_HASH in the script.")
        print("You can get these from https://my.telegram.org/apps")
        return
        
    if not await setup_client():
        return
        
    try:
        # get channel link or id
        channel_input = input("Enter Telegram channel link or ID: ")
        channel_id = parse_channel_link(channel_input)
        
        # get channel entity
        try:
            logger.info(f"Attempting to access channel with ID: {channel_id}")
            
            # Handler
            if isinstance(channel_id, int):
                
                if channel_id < 0:  # check if channel is negative
                    # use PeerChannel
                    channel_entity = await client.get_entity(PeerChannel(channel_id * -1))
                else:
                    channel_entity = await client.get_entity(channel_id)
            else:
                # usernames and other identifiers
                channel_entity = await client.get_entity(channel_id)
                
            logger.info(f"Successfully accessed channel: {getattr(channel_entity, 'title', channel_id)}")
        except ValueError as e:
            logger.error(f"Couldn't find channel with ID/link: {channel_id}")
            logger.error(f"Error details: {str(e)}")
            print("\nTip: For private channels, you need to be a member of the channel first.")
            print("For public channels, try using the username (e.g., 'username' instead of the numeric ID).")
            return
        except Exception as e:
            logger.error(f"Error accessing channel: {str(e)}")
            print("\nTroubleshooting steps:")
            print("1. Make sure you've joined the channel before trying to download from it")
            print("2. Try using the channel username if it has one")
            print("3. For private channels without usernames, you must access them through dialog list")
            return
            
        time_frame = input("Enter time frame (e.g., '7d' for 7 days, '24h' for 24 hours, or 'all' for all messages): ")
        file_extension = input("Enter file extension to download (default: .txt): ") or '.txt'
        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension
            
        download_method = input("Save to folder (f) or send to Discord webhook (d)? ").lower()
        save_path = None
        use_webhook = False
        
        if download_method == 'f':
            print("Please select a folder to save the files...")
            save_path = select_folder()
            if not save_path:
                logger.error("No folder selected. Exiting.")
                return
            
            # make dir if it doesn't exist
            os.makedirs(save_path, exist_ok=True)
        elif download_method == 'd':
            global DISCORD_WEBHOOK_URL
            if not DISCORD_WEBHOOK_URL:
                DISCORD_WEBHOOK_URL = input("Enter Discord webhook URL: ")
            use_webhook = True
            # make temp dir
            os.makedirs("temp", exist_ok=True)
        else:
            logger.error("Invalid download method selected. Exiting.")
            return
            
        # dl files
        await download_files(channel_entity, time_frame, save_path, use_webhook, file_extension)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
