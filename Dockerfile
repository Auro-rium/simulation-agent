# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (basic build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency definition first to leverage Docker cache
COPY pyproject.toml .

# Install dependencies directly from pyproject.toml
# Note: We rely on pip's ability to read pyproject.toml (modern pip)
# or we can extract them. Simplest is to install the project itself in editable mode or just install deps.
# creating a temp requirements.txt for robustness if pip install . takes too long to rebuild
RUN pip install --upgrade pip

# Copy the entire project
COPY . .

# Install the project and dependencies
RUN pip install .

# Expose Streamlit port
EXPOSE 8501

# Healthcheck to ensure container is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
