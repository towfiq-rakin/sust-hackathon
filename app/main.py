import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas import TicketRequest, TicketResponse

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QueueStorm Investigator API", version="1.0.0")

# Import analyzer lazily to avoid circular imports and ensure app loads instantly
from app.analyzer import analyze_ticket_flow

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(f"Validation error: {exc}")
    # Return a 422 for validation/semantic issues as per requirements
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Internal error: {exc}", exc_info=True)
    # Non-sensitive message, no stack traces
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-ticket", response_model=TicketResponse)
async def analyze_ticket(request: TicketRequest):
    # Ensure complaint is not empty
    if not request.complaint or not request.complaint.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complaint text cannot be empty or blank"
        )
    
    try:
        response = analyze_ticket_flow(request)
        return response
    except Exception as e:
        logger.error(f"Error during analysis of ticket {request.ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal analysis pipeline error"
        )
