from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import sys

#denne py fil bruges til at give systemet adgang til gmail, uden at jeg skal logge ind igen. 

# Vi skal kun bruge readonly adgang i starten, bruges til at anmode om tilladelse
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
    # Check for credentials file exists
    credentials_file = "credentials.json"
    
    if not os.path.exists(credentials_file):
        print(f" Fejl: {credentials_file} findes ikke")
        sys.exit(1)
    
    try:
        # indlæs client_secret JSON fra Google
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)

        # gem token.json til senere brug
        with open("token.json", "w") as token:
            token.write(creds.to_json())

        print("Login OK – token gemt!")
        
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()

