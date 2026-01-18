from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .auth import router as auth_router
from .routes import router as api_router

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Strava Insight Portal")

# CORS configuration
origins = [
    "http://localhost:3000", # Frontend
    "http://localhost:5173", # Vite default
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(api_router, prefix="/api", tags=["api"])

@app.get("/")
def read_root():
    return {"message": "Strava Insight Portal API is running"}
