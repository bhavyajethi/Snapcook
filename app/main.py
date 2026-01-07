from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from app.core.config import settings
from app.services.image_service import image_service
from app.services.ai_service import ai_service
import time
import json

# --- 1. SETUP ---
redis_client = None
templates = Jinja2Templates(directory="app/templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        print(" Redis Connected")
    except Exception as e:
        print(f" Redis Connection Failed: {e}")
    yield
    # Shutdown
    if redis_client:
        await redis_client.close()
        print(" Redis Closed")

app = FastAPI(title=settings.project_name, lifespan=lifespan)

# --- 2. THE RATE LIMITER DEPENDENCY (Clean Architecture) ---
# We use this ONLY on routes that cost money (AI).
async def check_rate_limit(request: Request):
    if not redis_client:
        return # Fail open if Redis is down (Service Availability > Rate Limiting)
        
    client_ip = request.client.host
    limiter_key = f"rate_limit:{client_ip}"
    
    # Count requests
    current_request = await redis_client.incr(limiter_key)
    
    if current_request == 1:
        await redis_client.expire(limiter_key, 60) # Reset every 60s
        
    if current_request > 10:
        print(f" Blocking {client_ip} (Quota Exceeded)")
        # This raises a standard 429 error that FastAPI handles automatically
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

# --- 3. ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # This route is FREE (No rate limit)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stats")
async def get_stats():
    # This route is FREE (No rate limit) - Your dashboard will never get blocked now
    if not redis_client:
        return {"error": "Redis not connected"}
    
    pipe = redis_client.pipeline()
    pipe.get("stats:total_requests")
    pipe.get("stats:cache_hits")
    # pipe.get("stats:time_saved")
    total, hits = await pipe.execute()
    
    return {
        "total_requests": int(total or 0),
        "cache_hits": int(hits or 0),
        # "time_saved_seconds": int(time or 0)
    }

# --- THE EXPENSIVE ROUTE (PROTECTED) ---
@app.post("/analyze", dependencies=[Depends(check_rate_limit)]) 
async def analyze_food(file: UploadFile = File(...)):
    # 1. Validate & Read
    image_bytes = await image_service.validate_image(file)
    
    # 2. Hash
    image_hash = image_service.generate_perceptual_hash(image_bytes)
    cache_key = f"recipe:{image_hash}"
    
    # 3. Check Cache
    if redis_client:
        cached_recipe = await redis_client.get(cache_key)
        if cached_recipe:
            print("Cache Hit!")

            try:
                data = json.loads(cached_recipe)
                receipe_text = data['content']
                #saved_time = float(data['time_taken'])
            except:
                receipe_text = str(cached_recipe)
                #saved_time = 5

            # Stats Update
            pipe = redis_client.pipeline()
            pipe.incr("stats:total_requests")
            pipe.incr("stats:cache_hits")
            # pipe.incrby("stats:time_saved", saved_time) 
            await pipe.execute()
            
            async def stream_cached():
                yield receipe_text
            return StreamingResponse(stream_cached(), media_type="text/plain")

    # 4. AI Process (Cache Miss)
    print("Cache Miss. Calling Gemini...")
    if redis_client:
         await redis_client.incr("stats:total_requests")

    # start_time = time.time()

    async def stream_and_cache_generator():
        full_response = ""
        async for chunk in ai_service.stream_receipe(image_bytes):
            full_response += chunk
            yield chunk 

        # end_time = time.time()
        # duration = round(end_time - start_time, 2)
        
        # Validate before caching
        is_valid = len(full_response) > 50 and ("Ingredients" in full_response or "Instructions" in full_response)
        
        if redis_client and is_valid:
            cache_data = {
                "content": full_response,
                # "time_duration": duration
            }
            await redis_client.setex(cache_key, 259200, full_response)
            print("Saved to Redis.")

    return StreamingResponse(stream_and_cache_generator(), media_type="text/event-stream")