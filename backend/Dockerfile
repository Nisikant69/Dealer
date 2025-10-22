# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 python:3.11-slim
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY ./requirements.txt .

RUN apt-get update && \
    apt-get install -y build-essential libcairo2-dev --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]