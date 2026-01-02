import imagehash
from PIL import Image
from io import BytesIO
from fastapi import UploadFile, HTTPException

class ImageService:
    @staticmethod
    async def validate_image(file: UploadFile) -> bytes:
        """
        Validates the file type and size. 
        Returns the raw bytes if valid.
        """
        # 1. Check Content Type (MIME)
        valid_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        
        if file.content_type not in valid_types:
            print(f" Rejected file type: {file.content_type}") # Debug print
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.content_type}. Only JPEG, PNG, and WebP are allowed."
            )
        
        # 2. Read bytes
        try:
            # We MUST use 'await' because reading a file is an IO operation
            contents = await file.read()
            
            # Reset cursor so we can read it again later if needed
            await file.seek(0) 
            
            return contents
        except Exception as e:
            print(f" File read error: {e}")
            raise HTTPException(status_code=500, detail="Failed to read file.")

    @staticmethod
    def generate_perceptual_hash(image_bytes: bytes) -> str:
        """
        Generates a 'Difference Hash' (dHash) for the image.
        """
        try:
            # Open image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Generate hash
            phash = str(imagehash.dhash(image))
            return phash
        except Exception as e:
            print(f" Hashing error: {e}")
            raise HTTPException(status_code=400, detail="Invalid image file.")

image_service = ImageService()