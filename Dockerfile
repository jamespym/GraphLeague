# Use a slim version of Python for a smaller, faster image
FROM python:3.11-slim

# Set the directory inside the container
WORKDIR /app

# Install system essentials for Streamlit and Neo4j drivers
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy your 'shopping list' and install libraries
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all your code into the container
COPY . .

# Tell Docker to listen on Streamlit's default port
EXPOSE 8501

# Start the app
ENTRYPOINT ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]