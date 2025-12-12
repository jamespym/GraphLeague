import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from google import genai
import time
from google.genai.errors import ServerError
from backend import user_intent

load_dotenv()

class Responder:
    def __init__(self):
        self.model = genai.Client()
        self.system_prompt = """
            You are a League of Legends coach.
            TASK: Use ONLY the following information to advise the user. Adopt a professional and coaching tone.
            IF the user query is an irrelevant topic, simply let the user know you are unable to proceed with his request.
            IF Champion Information is an empty list, inform the user that what his requesting for does not exist, based on the information available.
            The original user query has been has been distilled to its intention. However, the original query is still attached for additional context.
            Do not include an intro, but do give a summary if helpful.
            Note: Archetype refers to the subclassses that Champions are divided into, e.g. Warden, Diver, Artillery
            """
        
    def generate_response(self, graph_data, context, user_query):
        max_retries = 10
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.model.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{self.system_prompt}\n\nOriginal User Query:{user_query}\n\nContext:{context}\n\nChampion Information: {graph_data}",
                    config={
                        "temperature": 0.2
                    }
                )
                return response
                
            except ServerError as e:
                #print(f"Server overloaded (Attempt {attempt + 1}/{max_retries})...")
                sleep_time = base_delay * (2 ** attempt) 
                #print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Critical API Error: {e}")
                break
                
        print("Failed to get response after multiple attempts.")
        return None
