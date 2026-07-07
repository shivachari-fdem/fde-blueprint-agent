# Use the official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose port 8080 (Cloud Run's default)
EXPOSE 8080

# Command to run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
