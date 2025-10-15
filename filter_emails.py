from google.cloud import pubsub_v1
import json
import base64
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

load_dotenv() #load env variables
open_api_key = os.environ.get("OPENAI_API_KEY")
llm = ChatOpenAI(api_key=open_api_key, model="gpt-3.5-turbo", temperature=0)

# Sæt Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"] #tillader mig at læse mails
PROJECT_ID = "n8namalie"  
SUBSCRIPTION_ID = "gmail-sub"   

def get_new_emails(history_id=None):
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        service = build("gmail", "v1", credentials=creds)
        emails = []

        message_ids = []

        if history_id:
            history = service.users().history().list(
                userId='me',
                startHistoryId=history_id,
                historyTypes=['messageAdded']
            ).execute()
            history_records = history.get('history', [])
            for record in history_records:
                for msg in record.get('messages', []):
                    message_ids.append(msg['id'])

        # Hvis ingen message_ids fundet → hent seneste mails direkte
        if not message_ids:
            result = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=3
            ).execute()
            for msg in result.get('messages', []):
                message_ids.append(msg['id'])

        for msg_id in message_ids:
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            import re
            sender_header = headers.get('From', '').lower()
            match = re.search(r'<(.+?)>', sender_header)
            sender_email = match.group(1) if match else sender_header

            if sender_email.strip().lower() != "amcj@ek.dk":
                continue

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

        return emails
    except Exception as e:
        print("Fejl i get_new_emails:", e)
        return []

    

def evaluate_email(sender, subject, body):
    prompt = f"""
You are an email assistant. You receive an email with the following information:

Sender: {sender}
Subject: {subject}
Content: {body}

Your task is to:
1. Determine if the email is from Substack (check if sender or subject contains 'substack').
2. If yes, identify which specific Substack newsletter it is (e.g. by unique subject or sender details).
3. If the email contains information about asset allocations, extract the percentage or share for each of these: UPRO, Bitcoin, Gold, Money Market. If not present, set to null.
4. Return a JSON object with:
   - isSubstack: true/false
   - newsletter: name of the newsletter or null
   - allocations: {{ "UPRO": value or null, "Bitcoin": value or null, "Gold": value or null, "Money Market": value or null }}
   - summary: very short summary (max 10 words)

Example output:
{{
    "isSubstack": true,
    "newsletter": "Navn på nyhedsbrev",
    "allocations": {{"UPRO": 20, "Bitcoin": 30, "Gold": 25, "Money Market": 25}},
    "summary": "Fordeling af aktiver fra Substack"
}}
"""
    try:
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        import re
        response_text = re.sub(r',([\s]*[}\]])', r'\1', response_text)
        return json.loads(response_text)
    except Exception as e:
        print(f"Failed evaluation: {e}")
        return {
            "isSubstack": False,
            "newsletter": None,
            "allocations": {"UPRO": None, "Bitcoin": None, "Gold": None, "Money Market": None},
            "summary": ""
        }
def handle_substack_notifications(message):
    try:
        try:
            data = json.loads(base64.b64decode(message.data).decode("utf-8"))
        except Exception:
            data = json.loads(message.data.decode("utf-8"))

        substack_emails = get_new_emails(data.get('historyId'))

        if substack_emails:
            for email in substack_emails:
                try:
                    evaluation = evaluate_email(email['sender'], email['subject'], email['body'])
                    print('new email from substack has been evaluated:', evaluation)
                except Exception as e:
                    print("Fejl under evaluering:", e)
        else:
            print("Ingen nye emails fundet.")
    except Exception as e:
        print("Fejl i handle_substack_notifications:", e)
    finally:
        message.ack()


def main():
    subscriber = pubsub_v1.SubscriberClient() #opretter forbindelse til google cloud pub/sub
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=handle_substack_notifications) #kalder handle_substack_gmails hver gange en besked kommer

    try:
        streaming_pull_future.result()  # blokerer og holder connection åben
    except KeyboardInterrupt: #ctrl+c interrupt 
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()