from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Conversational Document Intake Assistant for Personal Wishes Document generation",
)

# CORS middleware for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": f"{settings.app_name} is running", "docs_url": "/docs"}
