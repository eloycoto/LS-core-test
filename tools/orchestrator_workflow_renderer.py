import json
import logging
import uuid
from pathlib import Path

import cairosvg
from fastmcp.server.context import Context
from playwright.async_api import async_playwright

from .orchestrator_service import orchestrator_mcp

logger = logging.getLogger(__name__)


class WorkflowRenderer:
    def __init__(self):
        self.html_path = (
            Path(__file__).parent.parent / "assets" / "workflow-renderer" / "index.html"
        )
        self.workflows_dir = Path(__file__).parent.parent / "assets" / "workflows"

    async def render_workflow_to_png_file(self, workflow_data: str) -> str:
        """
        Render workflow data to PNG file and return the file path

        Args:
            workflow_data (str): JSON string of workflow data

        Returns:
            str: Path to the saved PNG file
        """
        # Generate unique filename
        file_id = str(uuid.uuid4())
        png_path = self.workflows_dir / f"{file_id}.png"

        # Ensure the directory exists
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        svg = await self.render_workflow_to_svg(workflow_data)
        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"))

        # Save to file
        with open(png_path, "wb") as f:
            f.write(png_bytes)

        return str(png_path)

    async def render_workflow_to_svg(self, workflow_data: str) -> str:
        """
        Render workflow data to SVG using headless browser

        Args:
            workflow_data (str): JSON string of workflow data

        Returns:
            str: SVG content
        """
        logger.info("Starting workflow rendering process...")
        logger.info(f"HTML path: {self.html_path.absolute()}")

        async with async_playwright() as p:
            logger.info("Launching headless browser...")
            browser = await p.chromium.launch()
            page = await browser.new_page()

            page.on(
                "console",
                lambda msg: logger.info(f"Browser console [{msg.type}]: {msg.text}"),
            )
            page.on("pageerror", lambda err: logger.error(f"Browser error: {err}"))

            # Load the HTML file
            logger.info(f"Loading HTML file: file://{self.html_path.absolute()}")
            await page.goto(f"file://{self.html_path.absolute()}")

            # Wait for editor to initialize
            logger.info("Waiting for editor to initialize...")
            await page.wait_for_function("typeof render_workflow === 'function'")
            await page.wait_for_function("ready(); EditorIsReady === true")

            # Execute the workflow rendering on page load
            try:
                # Example rendering
                # await page.evaluate("""
                # render_workflow(
                #     document.getElementById("renderWorkflow"),
                #     JSON.stringify(sample_data)
                # );
                # """)

                await page.evaluate(f"""
                    let workflow_data = {workflow_data};
                    render_workflow(
                        document.getElementById("renderWorkflow"),
                        JSON.stringify(workflow_data)
                    );
                """)

                # Get the SVG content
                await page.wait_for_function(
                    "document.getElementById('renderWorkflow')."
                    "querySelector('svg') !== null"
                )
                svg_content = await page.evaluate(
                    "document.getElementById('renderWorkflow').innerHTML"
                )
            except Exception as e:
                logger.error(f"Error calling render_workflow: {e}")
                # Try to get any error messages from the page
                errors = await page.evaluate(
                    "document.querySelector('#renderWorkflow').innerHTML"
                )
                logger.info(f"Container content: {errors}")
                raise

            logger.info(
                f"SVG generated, length: "
                f"{len(svg_content) if svg_content else 0} characters"
            )
            await browser.close()
            logger.info("Browser closed")
            return svg_content


@orchestrator_mcp.tool()
async def orchestrator_preview_workflow(
    ctx: Context, session_id: str, workflow: str
) -> str:
    """
    Generate PNG preview of a orchestrator workflow.

    Args:
        session_id: Session identifier for tracking
        workflow: JSON string representing the serverless workflow

    Returns:
        str: URL of the PNG image
    """
    host = ctx.get_http_request().url
    hostname = host.hostname
    if hostname == "host.docker.internal":
        hostname = "localhost"

    try:
        logger.info(f"Generating workflow preview for session {session_id}")

        # Validate that workflow is valid JSON
        try:
            json.loads(workflow)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON workflow: {e}")
            raise ValueError(f"Invalid JSON workflow: {e}")

        # Create renderer and generate PNG file
        renderer = WorkflowRenderer()
        png_path = await renderer.render_workflow_to_png_file(workflow)

        filename = Path(png_path).name
        image_url = f"http://{hostname}:{host.port}/static/{filename}"

        logger.info(
            f"Successfully generated PNG for session {session_id} at {image_url}"
        )
        return image_url

    except Exception as e:
        logger.error(f"Error generating workflow preview for session {session_id}: {e}")
        raise
