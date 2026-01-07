# 🥗 SnapCook – High-Performance AI Recipe Microservice

![Status](https://img.shields.io/badge/Status-Under_Development-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-High_Performance-green?style=for-the-badge&logo=fastapi)
![Redis](https://img.shields.io/badge/Redis-Caching_&_Rate_Limiting-red?style=for-the-badge&logo=redis)

<!-- > **🚧 WORK IN PROGRESS:** This project is currently in active development.  -->
## 🚀 Overview

Although **SnapCook** is a simple project but I have tried to learn and implemented latency-optimized microservices that generates detailed recipes from food images. SnapCook is engineered for **cost-efficiency** and **perceived performance**. 

It uses **Perceptual Image Hashing** to detect duplicate uploads (saving expensive AI calls) and **Server-Sent Events (SSE)** to stream AI tokens in real-time, reducing perceived latency from ~6s to <500ms.

## 🏗️ System Architecture

* **Backend:** FastAPI (Python) for high-concurrency async handling.
* **Database/Cache:** Redis (Upstash) for semantic caching and distributed rate limiting.
* **AI Engine:** Google Gemini 2.5 Flash (Streamed Response).
* **Frontend:** HTML5 + Vanilla JS (moving to HTMX/Tailwind).

## ✨ Key Engineering Features

* **⚡ Real-Time Streaming:** Uses Server-Sent Events (SSE) to deliver recipe text token-by-token.
* **🧠 Semantic Caching:** Implements **Perceptual Hashing (pHash)** to identify identical images even if renamed or slightly resized, serving cached results instantly (0ms latency).
* **🛡️ Distributed Rate Limiting:** Token-bucket algorithm via Redis to prevent abuse and manage AI costs.
* **📊 Live Observability:** Built-in dashboard tracking Cache Hit Ratio, Time Saved.

## 🛠️ Installation & Setup

This project uses `uv` for lightning-fast dependency management.

1. **Clone the repository**:  
   ```bash
   git clone https://github.com/bhavyajethi/Snapcook.git
   
2. **Configure Environment**:
Create a .env file in the root directory:
#.env
REDIS_URL="redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379"
GEMINI_API_KEY="YOUR_GOOGLE_AI_KEY"

3. **Install Dependencies**:
uv sync
# OR manually: uv add fastapi uvicorn redis google-generativeai imagehash pillow python-multipart

4. **Run the Server**:
uv run uvicorn app.main:app --reload


