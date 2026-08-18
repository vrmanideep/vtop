import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scope must exactly match what your app needs
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def force_auth():
    print("[.] Initiating Gmail OAuth flow...")
    
    if os.path.exists('token.json'):
        print("[-] Old token.json found. Deleting it to force a new one...")
        os.remove('token.json')

    try:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        print("[✓] Success! A fresh token.json has been generated.")
    except Exception as e:
        print(f"[x] Error: {e}\nMake sure 'credentials.json' is in this folder!")

if __name__ == '__main__':
    force_auth()