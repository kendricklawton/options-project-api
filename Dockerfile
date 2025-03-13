# Stage 1: Build the application
FROM python:3.13.0-slim AS build

# Set environment variables to avoid writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt /app/

# Install dependencies in a virtual environment
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.13.0-slim AS runtime

# Create a non-root user again (to maintain security)
RUN useradd -m appuser

# Set the working directory in the container
WORKDIR /app

# Copy the application files from the build stage
COPY --from=build /app /app

#Copy the application code.
COPY --chown=appuser:appuser . /app/

# Copy the virtual environment from the build stage
COPY --from=build /app/venv /app/venv

# Expose the port for the app
EXPOSE 8080

# Set the PATH to use the virtual environment's bin directory
ENV PATH="/app/venv/bin:$PATH"

# Health check command
# HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl --fail http://localhost:8080/health || exit 1

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]