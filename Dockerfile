# Docker image
FROM python:3.10-slim

# App directory
WORKDIR /app

# Define env variables here, can be also defined from caprover panel
ENV TEST_ENV_KEY = "testing"
RUN apt -y update && apt install -y python-dateutil
# Copy files to container
COPY . .

# Install requirements
RUN pip3 install -r requirements.txt

# Port to be exposed
EXPOSE 8080

# Define starting command
ENTRYPOINT ["python", "app.py"]