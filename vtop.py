import os
import sys
import zipfile
import subprocess
import shutil

def setup_environment():
    # 1. Check/Install dependencies
    try:
        import httpx
    except ImportError:
        print("[-] httpx missing. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "beautifulsoup4", "lxml"])
        import httpx

    target_folder = "vitap_vtop_client"
    
    if not os.path.exists(target_folder):
        print(f"[!] {target_folder} missing. Fetching from source...")
        
        # Ensure the URL is absolute and starts with https://
        url = "https://codeload.github.com/Udhay-Adithya/vitap-vtop-client/zip/refs/heads/main"
        
        try:
            # Added verify=False only if your college network blocks SSL, 
            # otherwise keep it secure with default settings.
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                print(f"[-] Connecting to: {url}")
                r = client.get(url)
                
                if r.status_code != 200:
                    print(f"[!] HTTP Error {r.status_code}. Checking fallback branch...")
                    url = "https://codeload.github.com/Udhay-Adithya/vitap-vtop-client/zip/refs/heads/master"
                    r = client.get(url)

                if r.status_code == 200:
                    with open("core.zip", "wb") as f:
                        f.write(r.content)
                else:
                    print("[!] Fatal: Could not reach GitHub. Check your internet/proxy.")
                    sys.exit(1)

            # Extraction Logic
            print("[-] Extracting...")
            with zipfile.ZipFile("core.zip", "r") as zip_ref:
                zip_ref.extractall("temp_ext")

            extracted_root = os.listdir("temp_ext")[0]
            inner_path = os.path.join("temp_ext", extracted_root, target_folder)
            
            if os.path.exists(inner_path):
                shutil.move(inner_path, os.getcwd())
            
            # Cleanup
            os.remove("core.zip")
            shutil.rmtree("temp_ext")
            print("[+] Setup complete.")

        except Exception as e:
            print(f"[!] Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    setup_environment()
    if os.path.exists("main.py"):
        subprocess.run([sys.executable, "main.py"])