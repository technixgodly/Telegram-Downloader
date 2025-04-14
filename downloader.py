import os, re, asyncio, datetime, random, string, logging, sys, json
from tkinter import Tk, filedialog
try:
    import http.client
    import urllib.parse
    from telethon import TelegramClient, events
    from telethon.tl.types import PeerChannel, InputPeerChannel
except ImportError:
    os.system('pip install telethon')
    os.system('cls')
    print('Installed dependencies, please run the tool again.')
    input('Press Enter to exit...')
    exit()

# Debug mode 
DEBUG_MODE = "--debug" in sys.argv
if DEBUG_MODE:
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    print("DEBUG MODE ENABLED")
else:
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# running as executable or script
if getattr(sys, 'frozen', False):
    # executable
    application_path = os.path.dirname(sys.executable)
    if DEBUG_MODE:
        print(f"Running as executable from: {application_path}")
else:
    # script
    application_path = os.path.dirname(os.path.abspath(__file__))
    if DEBUG_MODE:
        print(f"Running as script from: {application_path}")

CONFIG_FILE = os.path.join(application_path, 'config.json')

def get_api_credentials():
    if DEBUG_MODE:
        print("\nDEBUG: Starting credential retrieval process")
    
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    
    if DEBUG_MODE:
        print(f"DEBUG: Environment variables - API_ID: {'Found' if api_id else 'Not found'}, API_HASH: {'Found' if api_hash else 'Not found'}")
    

    if api_id and api_hash and api_id.isdigit() and api_hash:
        logger.info("Using API credentials from environment variables")
        return api_id, api_hash

    if os.path.exists(CONFIG_FILE):
        if DEBUG_MODE:
            print(f"DEBUG: Config file exists at: {CONFIG_FILE}")
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                api_id = config.get('api_id')
                api_hash = config.get('api_hash')
                
                if DEBUG_MODE:
                    print(f"DEBUG: Config file contents - API_ID: {'Found' if api_id else 'Not found'}, API_HASH: {'Found' if api_hash else 'Not found'}")
                

                if api_id and api_hash and str(api_id).isdigit() and api_hash and api_hash != "ENTER YOUR API HASH HERE":
                    logger.info(f"Loaded API credentials from config file: {CONFIG_FILE}")
                    return str(api_id), api_hash
                else:
                    logger.warning("Invalid credentials in config file")
                    if DEBUG_MODE:
                        print("DEBUG: Config file validation failed:")
                        print(f"  - API_ID is numeric: {str(api_id).isdigit() if api_id else 'No API_ID found'}")
                        print(f"  - API_HASH is not empty: {bool(api_hash) if api_hash else 'No API_HASH found'}")
                        print(f"  - API_HASH is not default: {api_hash != 'ENTER YOUR API HASH HERE' if api_hash else 'No API_HASH found'}")
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            if DEBUG_MODE:
                print(f"DEBUG: Error reading config file: {e}")
    else:
        logger.info(f"No config file found at: {CONFIG_FILE}")
        if DEBUG_MODE:
            print(f"DEBUG: Config file not found at: {CONFIG_FILE}")
    

    print("\nTelegram API credentials not found or not properly configured.")
    print("You need to get your API ID and API Hash from https://my.telegram.org/apps")
    
    try:
        api_id = input("\nEnter your Telegram API ID: ").strip()
        api_hash = input("Enter your Telegram API Hash: ").strip()
        

        if not api_id.isdigit() or not api_hash:
            print("Invalid credentials. API ID must be a number and API Hash cannot be empty.")
            return None, None
            

        os.environ["TELEGRAM_API_ID"] = api_id
        os.environ["TELEGRAM_API_HASH"] = api_hash
        

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'api_id': api_id, 'api_hash': api_hash}, f)
            print(f"Credentials saved to config file: {CONFIG_FILE}")
            if DEBUG_MODE:
                print(f"DEBUG: Credentials successfully saved to config file")
        except Exception as e:
            logger.error(f"Error saving to config file: {e}")
            if DEBUG_MODE:
                print(f"DEBUG: Error saving to config file: {e}")
            print("Credentials saved to environment variables for this session only.")
        
    except EOFError:
        print("\nERROR: Cannot read input. Make sure you're running this from a terminal/command prompt.")
        return None, None
    
    return api_id, api_hash


API_ID, API_HASH = get_api_credentials()
if not API_ID or not API_HASH:
    print("Cannot proceed without valid API credentials.")
    print("\nTroubleshooting tips:")
    print("1. Run with --debug flag for more information")
    print("2. Check if config.json exists and has correct permissions")
    print("3. Try deleting config.json and setting credentials again")
    print("4. Set environment variables TELEGRAM_API_ID and TELEGRAM_API_HASH manually")
    input("Press Enter to exit...")
    exit()

if DEBUG_MODE:
    print(f"DEBUG: Final API credentials - API_ID: {'Valid' if API_ID and API_ID.isdigit() else 'Invalid'}, API_HASH: {'Valid' if API_HASH else 'Invalid'}")

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
        
        # parse webhook
        url_parts = urllib.parse.urlparse(DISCORD_WEBHOOK_URL)
        
        # host and path
        host = url_parts.netloc
        path = url_parts.path
        
        boundary = '----WebKitFormBoundary' + ''.join(random.sample(string.ascii_letters + string.digits, 16))
        
        # read file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # prep data
        payload = []
        payload.append(f'--{boundary}'.encode())
        payload.append(f'Content-Disposition: form-data; name="file"; filename="{file_name}"'.encode())
        payload.append(b'Content-Type: application/octet-stream')
        payload.append(b'')
        payload.append(file_content)
        payload.append(f'--{boundary}--'.encode())
        
        # Join with crlf
        body = b'\r\n'.join(payload)
        
        # init connection
        conn = http.client.HTTPSConnection(host)
        
        # headers
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        }
        
        # send req
        conn.request('POST', path, body=body, headers=headers)
    
        response = conn.getresponse()
        
        if response.status == 200 or response.status == 204:
            logger.info(f"Successfully sent {file_name} to Discord webhook")
            conn.close()
            return True
        else:
            logger.error(f"Failed to send {file_name} to Discord webhook: {response.status}")
            conn.close()
            return False
    except Exception as e:
        logger.error(f"Error sending file to Discord webhook: {e}")
        return False

async def setup_client():
    """Set up and connect the Telegram client."""
    global client
    
    # init client
    client = TelegramClient('telegram_downloader_session', int(API_ID), API_HASH)
    
    try:
        await client.start()
        
        if not await client.is_user_authorized():
            logger.info("You need to log in to your Telegram account.")
            logger.info("Please check your Telegram app for the login code and enter it below.")
            try:
                phone = input("Enter your phone number (with country code): ")
                await client.send_code_request(phone)
                code = input("Enter the code you received: ")
                await client.sign_in(code=code)
            except EOFError:
                logger.error("ERROR: Cannot read input. Make sure you're running this from a terminal/command prompt.")
                logger.error("If using the executable, do not double-click it - open a command prompt and run it from there.")
                return False
            except Exception as e:
                logger.error(f"Login failed: {e}")
                return False
        
        logger.info("Successfully logged in to Telegram!")
        return True
    except Exception as e:
        logger.error(f"Error setting up client: {e}")
        return False

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
    try:
        if DEBUG_MODE:
            print("DEBUG: Starting main function")
        asyncio.run(main())
        input("\nPress Enter to exit...")
    except RuntimeError as e:
        if "lost sys.stdin" in str(e):
            print("\nERROR: This application requires console input.")
            print("Please run it from a command prompt/terminal, not by double-clicking.")
            print("\nTo use this application:")
            print("1. Open Command Prompt or PowerShell")
            print("2. cd to the folder containing this executable")
            print("3. Run the application")
            input("\nPress Enter to exit...")
        else:
            print(f"An error occurred: {e}")
            if DEBUG_MODE:
                import traceback
                traceback.print_exc()
            input("\nPress Enter to exit...")
    except Exception as e:
        print(f"An error occurred: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        input("\nPress Enter to exit...")
