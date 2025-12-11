import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from google import genai
import time
from google.genai.errors import ServerError
import user_intent

load_dotenv()

class Responder:
    def __init__(self):
        self.model = genai.Client()
        self.system_prompt = """
            You are a League of Legends coach.
            TASK: Use the following information to advise the user. Give your answer in natural language.
            The original user query has been has been distilled to its intention. However, the original query is still attached for additional context.
            
            Note: Archetype refers to the subclassses that Champions are divided into, e.g. Warden, Diver, Artillery
            """
        
    def generate_response(self, graph_data, context, user_query):
        # Configuration for retries
        max_retries = 3
        base_delay = 1  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # 1. Attempt the generation
                response = self.model.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{self.system_prompt}\n\nOriginal User Query:{user_query}\n\nContext:{context}\n\nChampion Information: {graph_data}",
                    config={
                        "temperature": 0.3,
                    }
                )
                return response
                
            except ServerError as e:
                # 2. Catch ONLY the 503 (Server Error)
                print(f"Server overloaded (Attempt {attempt + 1}/{max_retries})...")
                
                # 3. Wait longer each time (2s, 4s, 8s)
                sleep_time = base_delay * (2 ** attempt) 
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
            except Exception as e:
                # 4. If it's a 400 error (Invalid Prompt), don't retry. It won't fix itself.
                print(f"Critical API Error: {e}")
                break
                
        print("Failed to get response after multiple attempts.")
        return None
