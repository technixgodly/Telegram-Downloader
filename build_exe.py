import os
import subprocess
import sys
import json

def main():
    print("Installing PyInstaller if not already installed...")
    subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("Installing required dependencies...")
    subprocess.call([sys.executable, "-m", "pip", "install", "telethon"])
    
    session_files = []
    session_base = "telegram_downloader_session"
    
    for ext in [".session", ".session-journal", "-journal"]:
        if os.path.exists(f"{session_base}{ext}"):
            session_files.append(f"{session_base}{ext}")
    
    config_data_arg = []
    if os.path.exists("config.json"):
        try:
            with open("config.json", 'r') as f:
                config = json.load(f)
                api_id = config.get('api_id')
                api_hash = config.get('api_hash')
                
                if api_id and api_hash and str(api_id).isdigit() and api_hash and api_hash != "ENTER YOUR API HASH HERE":
                    print("Found valid config.json with API credentials")
                else:
                    print("Config file exists but contains invalid credentials")
        except Exception as e:
            print(f"Error reading config.json: {e}")
            
        config_data_arg = ["--add-data", "config.json;."]
    else:
        create_config = input("No config.json found. Create one now? (y/n): ").lower()
        if create_config == 'y':
            try:
                api_id = input("Enter your Telegram API ID: ").strip()
                api_hash = input("Enter your Telegram API Hash: ").strip()
                
                if api_id.isdigit() and api_hash:
                    with open("config.json", 'w') as f:
                        json.dump({'api_id': api_id, 'api_hash': api_hash}, f)
                    print("Created config.json with your credentials")
                    config_data_arg = ["--add-data", "config.json;."]
                else:
                    print("Invalid credentials. Will build without config file.")
            except Exception as e:
                print(f"Error creating config.json: {e}")
        else:
            print("Will build without config file. The executable will prompt for credentials on first run.")
    
    # Add session files if they exist
    session_data_args = []
    if session_files:
        for session_file in session_files:
            session_data_args.extend(["--add-data", f"{session_file};."])
        print(f"Found {len(session_files)} session file(s), will include in executable")
    else:
        print("No session files found. You need to run the script once to create them.")
        run_first = input("Would you like to run the script now to create session files? (y/n): ").lower()
        if run_first == 'y':
            print("Running downloader.py to create session files...")
            subprocess.call([sys.executable, "downloader.py"])
            
            session_files = []
            for ext in [".session", ".session-journal", "-journal"]:
                if os.path.exists(f"{session_base}{ext}"):
                    session_files.append(f"{session_base}{ext}")
            
            if session_files:
                for session_file in session_files:
                    session_data_args.extend(["--add-data", f"{session_file};."])
                print(f"Now found {len(session_files)} session file(s), will include in executable")
            else:
                print("Still no session files found. Continuing with build...")
    
    print("Building executable...")
    pyinstaller_args = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "--onefile",
        "--hidden-import=telethon",
        "--hidden-import=telethon.tl.types",
        "--hidden-import=json",
        "--name", "TelegramDownloader",
        "downloader.py"
    ]
    
    pyinstaller_args.extend(config_data_arg)
    pyinstaller_args.extend(session_data_args)
    
    subprocess.call(pyinstaller_args)
    
    batch_file_path = os.path.join("dist", "Run_TelegramDownloader.bat")
    with open(batch_file_path, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write("echo Starting Telegram Downloader...\n")
        batch_file.write("echo Note: This application requires console input.\n")
        batch_file.write("\n")
        batch_file.write(":: Run the executable\n")
        batch_file.write("TelegramDownloader.exe\n")
        batch_file.write("\n")
        batch_file.write("echo Exiting...\n")
        batch_file.write("pause\n")
    
    print("Build complete! The executable is in the 'dist' folder.")
    print("A batch file 'Run_TelegramDownloader.bat' has been created.")
    if not session_files:
        print("IMPORTANT: You need to run the script once normally to create session files before building the executable.")

if __name__ == "__main__":
    main() 