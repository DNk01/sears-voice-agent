import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from app.scheduling.queries import (
    find_technicians as _find_technicians,
    book_appointment as _book_appointment,
    create_image_request,
    get_image_analysis as _get_image_analysis,
)
from app.vision.email_sender import send_upload_link
from app.config import settings

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "find_technicians",
            "description": "Find available technicians for a given zip code and appliance type. Returns up to 3 options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {"type": "string", "description": "5-digit zip code of the customer"},
                    "appliance_type": {
                        "type": "string",
                        "enum": ["washer", "dryer", "refrigerator", "dishwasher", "oven", "hvac", "other"],
                    },
                },
                "required": ["zip_code", "appliance_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a technician appointment after the customer has confirmed a time slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tech_id": {"type": "integer"},
                    "slot_id": {"type": "integer"},
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "customer_email": {"type": "string"},
                    "appliance_type": {"type": "string"},
                    "zip_code": {"type": "string"},
                },
                "required": ["tech_id", "slot_id", "customer_name", "customer_phone", "appliance_type", "zip_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_image_request",
            "description": "Send an email with an image upload link when a photo would help diagnose the issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                "required": ["email", "session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_image_analysis",
            "description": "Check whether the customer has uploaded a photo and return the analysis result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        },
    },
]


async def dispatch_tool(name: str, args: dict, db: Session) -> str:
    """Execute a tool call and return a string result for the LLM."""
    try:
        if name == "find_technicians":
            results = _find_technicians(args["zip_code"], args["appliance_type"], db)
            if not results:
                return "No technicians available for that zip code and appliance type."
            return json.dumps(results)

        elif name == "book_appointment":
            result = _book_appointment(
                tech_id=int(args["tech_id"]),
                slot_id=int(args["slot_id"]),
                customer_name=args["customer_name"],
                customer_phone=args["customer_phone"],
                customer_email=args.get("customer_email"),
                appliance_type=args["appliance_type"],
                zip_code=args["zip_code"],
                db=db,
            )
            return json.dumps(result)

        elif name == "send_image_request":
            token = create_image_request(args["session_id"], args["email"], db)
            try:
                await send_upload_link(args["email"], token, settings.base_url)
                return "Image upload link sent to the customer's email."
            except Exception as e:
                logger.error("Resend failed for %s: %s", args["email"], e)
                upload_url = f"{settings.base_url}/upload/{token}"
                return f"Email delivery failed. Give the customer this URL directly: {upload_url}"

        elif name == "get_image_analysis":
            result = _get_image_analysis(args["session_id"], db)
            if result is None:
                return "No image has been uploaded yet."
            return json.dumps(result)

        else:
            return f"Unknown tool: {name}"

    except ValueError as e:
        logger.warning("Tool %s value error: %s", name, e)
        return f"Error: {e}"
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return f"Tool execution failed: {e}"
