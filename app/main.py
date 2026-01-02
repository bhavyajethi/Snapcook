from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from app.core.config import settings
from fastapi import UploadFile, File
from app.services.image_service import image_service
from app.services.ai_service import ai_service
from fastapi.responses import StreamingResponse, HTMLResponse

# Global variable to hold the Redis connection
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    global redis_client
    # FIX 1: Use settings.redis_url (lowercase, matching config.py)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        print("✅ Connected to Upstash Redis successfully.")
    except Exception as e:
        print(f"❌ Failed to connect to Upstash Redis: {e}")
    
    yield # App runs here
    
    # SHUTDOWN
    # FIX 2: Close the actual 'redis_client' instance, not the class
    if redis_client:
        await redis_client.close()
        print("🛑 Redis connection closed.")

# FIX 3: Initialize app ONLY ONCE, using the variable settings.project_name
app = FastAPI(title=settings.project_name, lifespan=lifespan)

# --- RATE LIMITER MIDDLEWARE ---
@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    # Allow health check to bypass rate limiter
    if request.url.path == "/":
        return await call_next(request)

    client_ip = request.client.host
    limiter_key = f"rate_limit:{client_ip}"

    # Check if redis is connected before using it
    if redis_client:
        current_request = await redis_client.incr(limiter_key)
        
        if current_request == 1:
            await redis_client.expire(limiter_key, 30) # Reset count every 30s
        
        if current_request > 10:
            # FIX 4: Remove the 'return' so the error actually raises
            print(f"Blocking request from {client_ip}")
            raise HTTPException(status_code=429, detail="Too Many Requests")
    
    response = await call_next(request)
    return response

@app.get("/")
async def health_check():
    return {"status": "online", "message": "SnapCook is Ready for Images"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    # 1. Validate & Read Image
    image_bytes = await image_service.validate_image(file)

    # 2.Generate perceptual hash
    image_hash = image_service.generate_perceptual_hash(image_bytes)

    # 3. Check Cache
    cache_key = f"receipe:{image_hash}"
    if redis_client:
        cached_receipe = await redis_client.get(cache_key)
        if cached_receipe:
            print(f"Cache hit! Serving image {image_hash} from cache.")
            # If found then stream cached text also so frontend handles it similalrly
            # generator function for cached response
            async def stream_cached():
                yield cached_receipe
            return StreamingResponse(stream_cached(), media_type="text/plain")

    print(f"Cache miss! Processing image {image_hash} with AI.")

    # 4. Stream from AI(cached it)
    # wrapper is required to save to redis while streaming happens
    async def stream_cache_generator():
        full_response = ""
        async for chunk in ai_service.stream_receipe(image_bytes):
            full_response += chunk
            yield chunk # Send to user immediately

        is_valid_recipe = (
            len(full_response) > 50 and 
            ("Ingredients" in full_response or "Instructions" in full_response)
        )
        
        # save full response to redis
        if redis_client and is_valid_recipe:
            await redis_client.setex(cache_key, 86400, full_response) # 1 hour expiry
            print("New receiped saved to cache")

    return StreamingResponse(stream_cache_generator(), media_type="text/event-stream")

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    with open("app/templates/test.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/stats")
async def get_stats():
    if not redis_client:
        return {"error": "Redis not connected"}

    # 'pipe' is used to get all data in 1 network call
    pipe = redis_client.pipeline()
    pipe.get("stats:total_requests")
    pipe.get("stats:cache_hits")
    pipe.get("stats:time_saved")

    # Execute pipeline
    total, hits, time = await pipe.execute()

    # convert none to 0 if its the first test run 
    total = int(total) if total else 0 
    hits = int(hits) if hits else 0
    time = int(time) if time else 0

    return {
        "total_requests": total,
        "cache_hits": hits,
        "time_saved_seconds": time,
        "approx_money_saved": f"${(hits * 0.10):.2f}" # Assuming $0.10 per AI call for gemini 2.5 flash
    }