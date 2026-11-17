import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from uvicorn import Config, Server

if __name__ == "__main__":
    config = Config("app.main:app", host="0.0.0.0", port=8000, loop="asyncio")
    server = Server(config)
    asyncio.run(server.serve())