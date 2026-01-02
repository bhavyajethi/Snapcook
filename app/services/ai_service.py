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
        You are a professional chef. Analyze the image provided.
        1. Identify the dish name.
        2. List the ingredients.
        3. Provide step-by-step cooking instructions.
        4. Estimate calories and cooking time.
        
        Format the output clearly in Markdown. 
        If the image is not food, politely refuse.
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
            print(f"❌ AI Error: {e}")
            yield "Error: Failed to generate recipe. Please try again."

ai_service = AIService()