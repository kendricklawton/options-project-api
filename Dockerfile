# Use an official Python runtime as a parent image.
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn (WSGI server)
RUN pip install gunicorn

# Expose port 8080 for the app
EXPOSE 8080

# Command to run the app using Gunicorn with 4 worker processes
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]