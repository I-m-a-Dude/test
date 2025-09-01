FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir monai

# Copy the entire project
COPY . .

# Create model directory (model file will be mounted as volume)
RUN mkdir -p ./model

EXPOSE 8000

CMD ["python", "main.py"]