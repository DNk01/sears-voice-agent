import base64
import json
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

VISION_PROMPT = """You are an appliance repair expert analyzing a customer photo.

Examine the image and return a JSON object with these fields:
- "appliance_type": one of washer, dryer, refrigerator, dishwasher, oven, hvac, other
- "visible_issues": list of visible problems (damage, wear, leaks, unusual buildup, etc.)
- "error_codes": list of any error codes visible on the display
- "recommendations": list of specific repair or diagnostic steps based on what you see

Return ONLY the JSON object, no other text."""


async def analyze_image(image_path: str) -> dict:
    """Analyze an appliance image using GPT-4o Vision. Returns structured diagnosis."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
    }.get(ext, "image/jpeg")

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                ],
            }
        ],
        max_tokens=500,
    )

    content = response.choices[0].message.content or ""
    try:
        clean = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"raw_description": content}
