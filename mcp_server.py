import logging
import signal
import uvicorn

from fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.routing import Mount

from tools.orchestrator_service import orchestrator_mcp

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Current Date and Time", port=8000)
mcp.mount(orchestrator_mcp, prefix="orchestrator")

mcp_app = mcp.http_app()

app = FastAPI(lifespan=mcp_app.lifespan)
app.mount("/static", StaticFiles(directory="assets/workflows/"), name="static")
app.mount("/", mcp_app)
