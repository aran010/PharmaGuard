# --- Stage 1: Build the Frontend ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# We set VITE_API_URL to an empty string so it uses relative paths for the API
ENV VITE_API_URL=""
RUN npm run build

# --- Stage 2: Setup the Backend & Bundle ---
FROM python:3.11-slim
WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from Stage 1 to the backend's static directory
COPY --from=frontend-builder /app/frontend/dist ./backend/static

# Copy sample data (optional, useful for testing)
COPY sample_data/ ./sample_data/

# Hugging Face Spaces specifies the PORT environment variable
ENV PORT=7860
EXPOSE 7860

# Set working directory to backend to run from there
WORKDIR /app/backend

# Use uvicorn to run the app
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
