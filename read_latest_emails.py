from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import os

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_latest_emails(max_results=5):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        maxResults=10
    ).execute()

    messages = result.get('messages', [])
    emails = []
    for message in messages:
        msg_id = message['id']
        msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif msg['payload']['body'].get('data'):
            body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
        emails.append({
            'sender': headers.get('From', 'Unknown'),
            'subject': headers.get('Subject', 'No Subject'),
            'body': body
        })

    # Gem de 10 seneste emails i en fil
    import json
    with open("latest_10_emails.json", "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

    return emails


def main():
    emails = get_latest_emails()
    for i, email in enumerate(emails, 1):
        print(f"\n--- Email {i} ---")
        print(f"From: {email['sender']}")
        print(f"Subject: {email['subject']}")
        print(f"Body:\n{email['body'][:500]}")
    

if __name__ == "__main__":
    main()
