import asyncio
import os
import sys
import subprocess
from random import SystemRandom
from json import load, JSONDecodeError
from io import BytesIO
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from requests import get
from warnings import warn

import fastapi
import uvicorn
import marko
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi import Request, HTTPException

randomiser = SystemRandom()  # cryptographically secure numbers :sunglasses:

if sys.version_info >= (3, 10):
    print("Warning: dragdev.xyz is only tested to work with python 3.6-9. 3.10+ is not currently guaranteed to work.",
          file=sys.stderr)

if not os.path.exists("./config.json"):
    print("No config file exists. Please copy 'config.template.json' to 'config.json' and modify it to your system.")
    sys.exit(1)

if os.getcwd() != Path(__file__).parent:
    print("Not in the correct working directory, moving...")
    os.chdir(Path(__file__).parent)

try:
    with open("./config.json", "r") as config_file:
        config = load(config_file)
except JSONDecodeError:
    print("Invalid JSON.")
    sys.exit(2)

print("Checking for updates...")
cmd = subprocess.run(["git", "fetch"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if not cmd.stdout:
    print("Site is up to date.")
else:
    print("Updating...")
    subprocess.run(["git", "pull", "origin", "master"])
    print("Done. Starting.")

app = fastapi.FastAPI()
app.state.invite = {
    "fetched_at": datetime.min,
    "url": "https://discord.gg/YBNWw7nMGH"
}
app.state.loop = asyncio.get_event_loop()
app.state.last_canvas = b""
if config["allowed_origins"]:
    app.add_middleware(
        CORSMiddleware, allow_origins=config["allowed_origins"]
    )


@app.middleware("http")
async def markdown_middleware(request: Request, call_next):
    """Middleware to render markdown files."""
    if request.url.path.lower().endswith(".md"):
        try:
            with open("./static" + request.url.path) as file:
                content = file.read()
        except FileNotFoundError:
            raise HTTPException(404)
        with open("./static/assets/template-markdown.html") as template:
            html_template = template.read()
        formatted = marko.convert(content)
        response = HTMLResponse(html_template.replace("$", formatted))
    else:
        response = await call_next(request)
    return response


@app.get("/server")
def get_server_invite():
    if (datetime.now() + timedelta(hours=1)) >= app.state.invite["fetched_at"] or not config["bot_token"]:
        return app.state.invite["url"]

    widget = get(
        "https://discord.com/api/v8/guilds/772980293929402389/invites",
        headers={
            "Authorization": "Bot " + config["bot_token"]
        }
    )
    data = widget.json()
    app.state.invite["url"] = "https://discord.gg/" + data["code"]
    app.state.invite["fetched_at"] = datetime.now()
    return app.state.invite["url"]


@app.get("/pixels")
async def get_pixels_image(resize_x: int = None, resize_y: int = None):
    max_noise_level = config.get("max_noise", ...)
    if max_noise_level is ...:
        max_noise_level = randomiser.randint(5, 30)
        warn(
            "You should set a noise_level for /pixels by setting `max_noise: int` in config.json."
            " The recommended value is 20 if you really want to stop bots."
        )

    async def e(f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(f, *args, **kwargs)
        )

    try:
        from PIL import Image
    except ImportError:
        raise HTTPException(501,
                            {"detail": "This server has not installed dependencies, unable to process pixels data."})
    token = config.get("pixels_token")
    if not token:
        raise HTTPException(501, {"detail": "This server has not provided authentication for the DragDev Pixels API."})
    if token.startswith("$"):
        token = os.getenv(token[1:])
        if not token:
            raise HTTPException(501,
                                {"detail": "This server has not provided authentication for the DragDev Pixels API."})
    response = await e(
        get,
        "https://pixels.dragdev.xyz/get_pixels",
        headers={
            "Authorization": "Bearer " + token
        }
    )
    content = response.content
    if response.status_code != 200:
        if not app.state.last_canvas:
            raise HTTPException(response.status_code, response.text, dict(response.headers))
        else:
            content = app.state.last_canvas
    app.state.last_canvas = response.content
    size = await e(
        get,
        "https://pixels.dragdev.xyz/get_size"
    )
    if size.status_code != 200:
        size = {"width": 272, "height": 135}
    else:
        size = await e(size.json)  # we could just use aiohttp...

    img = await e(Image.frombytes, "RGB", tuple(size.values()), content)

    # Now we need to "obfuscate" the image to prevent people scraping this endpoint for the canvas
    for y in range(img.height):
        for x in range(img.width):
            _r, _g, _b = img.getpixel((x, y))
            r, g, b = img.getpixel((x, y))
            noise_level = randomiser.randint(1, max_noise_level)
            r += noise_level
            g += noise_level
            b += noise_level
            img.putpixel((x, y), (r, g, b))

    if resize_x and resize_y:
        # resize the image to the correct width
        img = await e(img.resize, (resize_x, resize_y), Image.NEAREST)
    io = BytesIO()
    await e(img.save, io, format="png")
    io.seek(0)
    return Response(
        await e(io.read),
        203,
        media_type="image/png"
    )


app.mount("/", StaticFiles(directory=config["static_dir"], html=True))
uvicorn.run(app, host=config["host"], port=config["port"])
