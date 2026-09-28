from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    yield


app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator",
    description=(
        "AI-powered personalized fitness "
        "plan generator using Gemini."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static",
)


app.include_router(
    router
)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )