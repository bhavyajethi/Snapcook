import google.generativeai as genai
from app.core.config import settings
from PIL import Image
from io import BytesIO
from typing import AsyncGenerator

class AIService:
    def __init__(self):
        # Configure the SDK with the key from our settings
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize the Flash model (optimized for speed/cost)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # The instructions we give the AI
        self.system_prompt = """
        Analyze this image strictly in two phases.
        
        PHASE 1: VISUAL INSPECTION (Internal Thought)
        - Identify the ingredients.
        - CRITICAL: Analyze the STATE of the ingredients (e.g., Is the banana green or brown? Is the chicken raw or cooked? Is the bread stale?).
        - Based on the state, decide the BEST culinary use. (e.g., Brown bananas -> Baking. Cooked meat -> Reheating/Salads).
        
        PHASE 2: RECIPE GENERATION
        - Act as a {style} Chef.
        - Generate a recipe that MATCHES the visual state identified in Phase 1.
        - If the food looks spoiled/unsafe, strictly refuse and warn the user.
        - If the food is "Leftovers" (already cooked), provide a "Second Life" recipe (e.g., turning roast chicken into tacos).
        
        Output format:
        ##  Visual Analysis
        * [Observation about state, e.g., "I see heavily bruised bananas..."]
        * [Decision, e.g., "Perfect for high-sugar baking."]
        
        ##  The Recipe: [Dish Name]
        ... (Ingredients & Steps)
        """

    async def stream_receipe(self, image_bytes: bytes) -> AsyncGenerator[str, None]:
        """
        Sends image to Gemini and yields chunks of text as they are generated.
        """
        try:
            # Convert raw bytes back to a Pillow Image for the SDK
            image = Image.open(BytesIO(image_bytes))
            
            # Call Gemini with stream=True
            # Note: We use generate_content_async for non-blocking performance
            response = await self.model.generate_content_async(
                [self.system_prompt, image], 
                stream=True
            )
            
            # Yield chunks as they arrive
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            print(f" AI Error: {e}")
            yield "Error: Failed to generate recipe. Please try again."

ai_service = AIService()