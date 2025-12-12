from graph_retriever import GraphRetriever, Switchboard
from responder import Responder
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from google import genai
import time
from google.genai.errors import ServerError

def run_app():
    sb = Switchboard()
    graph = GraphRetriever()
    responder = Responder()
    print("System Ready.\n")
    
    while True:
        user_query = input("You: ")
        if user_query.lower() == "exit":
            break
        
        try:
            time.sleep(1)
            graph_data, context = sb.handle_query(user_query, graph)
            if graph_data == "NA":
                print("GraphLeague: I can't answer that right now.")
                continue
            time.sleep(1)
            final_response = responder.generate_response(graph_data, context, user_query)
            print(f"GraphLeague: {final_response.text}")
        except Exception as e:
            print(f"Error processing request: {e}")

    graph.close()

if __name__ == "__main__":
    run_app()
            
            
        