# Uniqorn Backend 🦄

**Uniqorn** is an intelligent, agentic backend designed to power market research and product roadmap generation. Built on **FastAPI** and **OpenAI's Agents SDK**, it leverages a suite of specialized agents to analyze market signals, perform competitive research, and automatically generate detailed product roadmaps.

## 🚀 Features

### 🧠 Agentic Market Research
Uniqorn aggregates and synthesizes data from multiple high-signal sources to provide deep market contexts:
-   **Reddit**: Analyzes user sentiment, pain points, and discussions in relevant communities.
-   **Product Hunt**: Tracks trending products, launches, and maker activity.
-   **PitchBook**: Retrieves company profiles, funding status, and competitive landscapes (via Bright Data).
-   **Firecrawl**: Performs deep web searches and content extraction for real-time market data.
-   **NewsAPI**: Monitors global news for industry trends and announcements.
-   **Google Trends**: Analyzes search interest and macro demand shifts.
-   **Landscape Generation**: Automatically compiles "Competitive" and "Parallel" market insights.

### 🗺️ Automated Roadmap Generation
-   **Context-Aware**: Uses project context and market research to tailor roadmaps.
-   **Hierarchical Structure**: Generates Epics, Features, and actionable Tasks.
-   **Async Processing**: specialized agents work in parallel to expand high-level goals into granular specs.

### 💬 Landing Chatbot
-   **WebSocket Interface**: Real-time, bi-directional communication.
-   **Session Memory**: Maintains context across the conversation.
-   **Research-Enabled**: The chatbot can autonomously trigger web searches and research actions during a conversation to answer user queries grounded in data.

---

## 🏗️ Architecture

The system is built using a modular agentic architecture:
-   **`main.py`**: The entry point, hosting the FastAPI application and WebSocket manager.
-   **`apis/`**: REST endpoints for the frontend (Roadmap, Landscape, Context).
-   **`agent_calls/`**: wrappers for interacting with the AI agents.
-   **`tools/`**: specialized modules ensuring valid interaction with external third-party APIs (Reddit, Product Hunt, etc.).
-   **`schemas/`**: Pydantic models ensuring strict type safety for data exchange.

---

## 🛠️ Prerequisites

-   **Python 3.10+**
-   **Virtual Environment** (recommended)
-   **API Keys** for the services utilized.

---

## ⚙️ Installation

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd uniqorn-backend
    ```

2.  **Set Up Virtual Environment**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory and add your keys:

    ```env
    # Core
    OPENAI_API_KEY=sk-...

    # Market Research Tools
    REDDIT_CLIENT_ID=...
    REDDIT_CLIENT_SECRET=...
    REDDIT_USER_AGENT=startup_landscape_app/0.1

    PRODUCTHUNT_DEV_TOKEN=...

    FIRECRAWL_API_KEY=fc-...

    NEWSAPI_KEY=...

    # Bright Data (PitchBook)
    BRIGHTDATA_API_KEY=...
    ```

---


## 🔌 Frontend Integration

The backend is configured with **CORS enabled** for all origins (`*`), validating it for easy frontend integration (React, Vue, etc.).

### 1. REST APIs
Base URL: `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/roadmap` | POST | Generate a product roadmap |
| `/api/landscape` | POST | Generate a market landscape |
| `/api/context` | GET/POST | Manage project context |

### 2. Chatbot WebSocket
**URL:** `ws://localhost:8000/ws/chatbot/{session_id}`
*(Replace `{session_id}` with any unique string, e.g., a UUID)*

**Client Logic:**
1.  **Connect** to the WebSocket URL.
2.  **Listen** for JSON messages:
    *   `type: "chunk"` -> Append `content` to the current bot message (streaming).
    *   `type: "tool_call"` -> Show "Searching..." indicator.
    *   `type: "message_complete"` -> Stop loading indicator.
3.  **Send** JSON messages:
    ```json
    {
      "type": "message",
      "content": "Make me a roadmap for a pet rock startup",
      "web_search": true
    }
    ```

## 🏃 Usage

### Start the Server
Run the FastAPI server using `uvicorn` (configured in `main.py`):

```bash
python main.py
```
*The server typically runs on `http://0.0.0.0:8000`.*

### API Documentation
Once running, visit the interactive Swagger UI to explore and test endpoints:
-   **Docs**: `http://localhost:8000/docs`
-   **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints
-   `POST /api/landscape`: Triggers a market research report generation.
-   `POST /api/roadmap`: Generates a product roadmap based on provided context.
-   `WS /ws/chatbot/{session_id}`: WebSocket endpoint for the AI assistant.

---

## 🧪 Testing

You can run individual tool tests to ensure your API keys are working:

```bash
# Test Reddit
python tools/reddit.py

# Test Product Hunt
python tools/producthunt.py

# Test Firecrawl
python tools/firecrawl_tools.py
```
