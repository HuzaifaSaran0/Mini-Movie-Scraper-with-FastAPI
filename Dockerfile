# Use a lightweight, modern Python image
FROM python:3.12-slim

# Install the uv package manager directly from Astral's image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Silence the uv hardlink warning across Docker volumes
ENV UV_LINK_MODE=copy

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies into the container's environment.
RUN uv sync --frozen

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application using uvicorn directly
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]