# CortexAI – Context-Aware AI Assistant Platform

An intelligent, context-aware AI assistant that understands webpage content and generates relevant responses using Large Language Models (LLMs).

CortexAI combines a Python FastAPI backend, Ollama-powered AI responses, Redis caching, and an event-driven infrastructure with Apache Kafka. It is designed with a modular architecture to support scalability, reliability, and future enhancements.

---

## 🚀 Project Overview

CortexAI is an AI-powered web assistant that allows users to interact with webpage content through natural language questions.

Instead of asking an AI model to answer questions without context, CortexAI provides relevant webpage information to the LLM so that it can generate more accurate and context-aware responses.

### Key Features

- **Context-Aware AI:** Uses webpage title, URL, and content to generate relevant answers.
- **LLM Integration:** Integrates Ollama to run local Large Language Models.
- **REST API:** Provides backend APIs using FastAPI.
- **Redis Caching:** Caches responses to avoid repeated LLM calls for identical requests.
- **Cache Expiration:** Supports configurable cache TTL.
- **Fault Tolerance:** Handles Redis failures gracefully so chat requests can continue.
- **Kafka Infrastructure:** Includes Apache Kafka infrastructure for asynchronous event-driven processing.
- **PostgreSQL:** Includes PostgreSQL infrastructure for persistent data capabilities.
- **Dockerized Services:** Uses Docker Compose to manage infrastructure services.

---

## 🏗️ Architecture

```text
                  User
                   |
                   v
             Frontend UI
                   |
                   v
             FastAPI Backend
                   |
          +--------+--------+
          |                 |
          v                 v
      Redis Cache       Ollama LLM
          |                 |
          |                 v
          |             AI Response
          |                 |
          +--------<--------+
                   |
                   v
              API Response
                   |
                   v
                 User

        Supporting Infrastructure
        --------------------------
        Apache Kafka
        PostgreSQL
```

### Request Processing Flow

1. The user submits a question through the frontend.
2. The frontend sends the question and webpage context to the FastAPI backend.
3. The backend generates a unique cache key using the question and webpage context.
4. Redis is checked for an existing response.
5. If a cached response exists, it is returned immediately.
6. If no cached response exists, the backend sends the contextual prompt to Ollama.
7. Ollama generates an answer using the selected local LLM.
8. The generated response is stored in Redis with a configurable expiration time.
9. The response is returned to the frontend.

---

## 🛠️ Technology Stack

| Category | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, Vite |
| AI / LLM | Ollama |
| Default LLM | Qwen 2.5 7B |
| Caching | Redis |
| Messaging Infrastructure | Apache Kafka |
| Database Infrastructure | PostgreSQL |
| Containerization | Docker, Docker Compose |
| Testing | Pytest |

---

## 📁 Project Structure

```text
CortexAI/
│
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── ai_provider.py
│   │   │   └── cache_service.py
│   │   │
│   │   ├── __init__.py
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_cache_operations.py
│   │   │   └── test_cache_service.py
│   │   │
│   │   └── test_api_chat.py
│   │
│   ├── test_ai_provider.py
│   └── test_connections.py
│
├── frontend/
│   ├── public/
│   │   ├── overlay.js
│   │   ├── service-worker.js
│   │   └── manifest.json
│   │
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── content.ts
│   │   └── main.tsx
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
├── CODE_WALKTHROUGH.md
├── .gitignore
└── README.md
```

---

## ⚙️ Prerequisites

Make sure you have the following installed:

- Python 3.12+
- Node.js and npm
- Docker Desktop
- Git
- Ollama

---

## 🔧 Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ravikumar197/CortexAI-Context-Aware-AI-Assistant-Platform.git

cd CortexAI-Context-Aware-AI-Assistant-Platform
```

### 2. Start Infrastructure Services

Start Redis, PostgreSQL, and Kafka using Docker Compose.

```bash
docker compose up -d
```

Verify running containers:

```bash
docker compose ps
```

### 3. Configure Ollama

Install Ollama and download the default model:

```bash
ollama pull qwen2.5:7b
```

Make sure Ollama is running:

```bash
ollama serve
```

If Ollama is already running as a background service, you do not need to start it again.

### 4. Set Up Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install fastapi "uvicorn[standard]" ollama redis kafka-python "psycopg[binary]" pytest httpx
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Set Up Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the frontend using the URL displayed in your terminal.

---

## 🔌 API Endpoints

### 1. Analyze Webpage Context

**Endpoint**

```http
POST /api/context/analyze
```

Purpose:

Processes webpage context using the configured AI provider.

### 2. Chat with Webpage Context

**Endpoint**

```http
POST /api/chat
```

Example request:

```json
{
  "question": "What is Redis caching?",
  "page_title": "Redis Tutorial",
  "page_url": "https://example.com/redis",
  "page_text": "Redis is an in-memory data store used for caching."
}
```

Example response:

```json
{
  "answer": "Redis is an in-memory data store...",
  "cached": false
}
```

When the same request is submitted again before the cache expires:

```json
{
  "answer": "Redis is an in-memory data store...",
  "cached": true
}
```

---

## ⚡ Redis Caching

CortexAI uses Redis to reduce unnecessary LLM requests.

### Cache Key Generation

The cache key is generated using SHA-256 based on:

- User question
- Webpage title
- Webpage URL
- Webpage content

This ensures that different questions or webpage contexts generate different cache entries.

### Cache Configuration

The default cache expiration time is 300 seconds (5 minutes).

You can configure it using:

```bash
export CHAT_CACHE_TTL=600
```

### Fault Tolerance

Redis is treated as an optional performance layer.

If Redis becomes unavailable:

- The application continues processing chat requests.
- The AI provider generates the response.
- Cache read/write failures are logged.
- The API does not fail solely because Redis is unavailable.

---

## 📨 Kafka Infrastructure

Apache Kafka is included in the Docker Compose infrastructure to support event-driven communication.

Potential use cases include:

- Chat completion events
- Request processing events
- Background task execution
- Usage analytics
- Asynchronous processing

Kafka can be accessed from the local backend using:

```text
127.0.0.1:9092
```

---

## 🗄️ PostgreSQL Infrastructure

PostgreSQL is included as the relational database infrastructure.

It can support future persistent storage requirements such as:

- User information
- Chat history
- Conversation metadata
- Application configurations

---

## 🧪 Testing

CortexAI includes unit tests and API integration tests using Pytest.

Navigate to the backend directory:

```bash
cd backend
```

Run all tests:

```bash
python -m pytest -q tests
```

Run cache-specific tests:

```bash
python -m pytest -q tests/unit
```

Run API tests:

```bash
python -m pytest -q tests/test_api_chat.py
```

The test suite covers:

- Cache key generation
- Cache hit and miss scenarios
- Redis failures
- Cache expiration configuration
- AI provider mocking
- API error handling

---

## 🔐 Environment Configuration

Do not commit credentials or sensitive configuration values to GitHub.

Use environment variables for application configuration.

Example:

```env
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
REDIS_URL=redis://127.0.0.1:6379/0
CHAT_CACHE_TTL=300
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
POSTGRES_PASSWORD=your_password
```

Keep your actual `.env` file private.

---

## 🛣️ Future Enhancements

- Implement complete Kafka producer and consumer workflows.
- Integrate PostgreSQL for persistent chat history.
- Add authentication and authorization.
- Implement conversation management.
- Introduce streaming LLM responses.
- Add monitoring and observability.
- Implement retry mechanisms and dead-letter queues.
- Improve frontend user experience.
- Add automated CI/CD pipelines.

---

## 🎯 Project Goals

The main objective of CortexAI is to demonstrate how modern backend and AI technologies can work together to build a scalable, context-aware assistant.

The project focuses on practical implementation of:

- RESTful API development
- LLM integration
- Redis caching strategies
- Kafka-based event-driven architecture
- Database infrastructure
- Docker-based development
- Automated testing
- Fault-tolerant backend design

---

## 👨‍💻 Author

**Ravi Kumar**

GitHub: [ravikumar197](https://github.com/ravikumar197)

Project Repository:

[CortexAI – Context-Aware AI Assistant Platform](https://github.com/ravikumar197/CortexAI-Context-Aware-AI-Assistant-Platform)

---

⭐ If you find this project interesting, feel free to explore the repository and contribute.
