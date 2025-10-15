from google.cloud import pubsub_v1
import json
import base64
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from vector_db import save_emails

load_dotenv() #load env variables
open_api_key = os.environ.get("OPENAI_API_KEY")
llm = ChatOpenAI(api_key=open_api_key, model="gpt-3.5-turbo", temperature=0)