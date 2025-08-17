FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project including the model
COPY . .

# Ensure the model file is in the correct location
# If ag_model.pth is in a specific directory, adjust the path accordingly
COPY ag_model.pth ./model/ag_model.pth

EXPOSE 8000

CMD ["python", "main.py"]