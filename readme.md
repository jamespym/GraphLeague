GraphLeague: AI LoL Draft Assistant
An AI-powered League of Legends coaching assistant built with Neo4j, Pydantic, Gemini, and Streamlit. It uses a Knowledge Graph to provide strategic counter-picks and team compositions.

### Quick Start ###
1. Configure Environment
Create a `.env` file in the root directory. Never commit this file to version control. 
Add the following template and replace the placeholders with your actual credentials:

```text
GEMINI_API_KEY='your_google_gemini_api_key_here'
NEO4J_PASSWORD='your_secure_password_here'
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j

2. Launch with Docker
Run the following command to start the database and the web app:

Bash
docker compose --env-file .env up -d

3. Seed the Knowledge Graph
Populate the Neo4j database with champion data:

Bash
docker cp backend/processed_champions_v4.json graphleague_coach:/app/backend/
docker exec -it graphleague_coach python backend/graph_builder.py

### Tech Stack ###
Frontend: Streamlit
Database: Neo4j (Graph Database)
LLM: Google Gemini gemini-2.5-flash

Infrastructure: Docker & GitHub Actions

### Automation ###
This project uses GitHub Actions to automatically:

1. Verify the Docker build.
2. Test database authentication and seeding.
3. Ensure Python syntax is correct.