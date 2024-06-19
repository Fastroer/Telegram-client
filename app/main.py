import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.db.database import engine
from app.db.models import Base

app = FastAPI(docs_url="/api")

app.mount("/sessions", StaticFiles(directory="app/sessions"), name="sessions")

app.include_router(router)

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def main():
    await init_models()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
