import asyncio
import os
import sys
import subprocess
from random import SystemRandom
from json import load, JSONDecodeError
from io import BytesIO
from datetime import date, datetime, timedelta
from functools import partial
from pathlib import Path
from requests import get
from warnings import warn
from base64 import b64encode
from threading import Thread as Process

import fastapi
import uvicorn
import marko
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi import Request, HTTPException

randomiser = SystemRandom()  # cryptographically secure numbers :sunglasses:

if sys.version_info >= (3, 10):
    print(
        "Warning: dragdev.xyz is only tested to work with python 3.6-9. 3.10+ is not currently guaranteed to work.",
        file=sys.stderr,
    )

if not os.path.exists("./config.json"):
    print("No config file exists. Please copy 'config.template.json' to 'config.json' and modify it to your system.")
    sys.exit(1)

if os.getcwd() != str(Path(__file__).parent):
    print("Not in the correct working directory, moving...")
    os.chdir(Path(__file__).parent)

try:
    with open("./config.json", "r") as config_file:
        config = load(config_file)
except JSONDecodeError:
    print("Invalid JSON.")
    sys.exit(2)

app = fastapi.FastAPI()
app.state.invite = {"fetched_at": datetime.min, "url": "https://discord.gg/YBNWw7nMGH"}
app.state.loop = asyncio.get_event_loop()
app.state.last_canvas = b""
if config["allowed_origins"]:
    app.add_middleware(CORSMiddleware, allow_origins=config["allowed_origins"], allow_methods=["GET", "HEAD"])


@app.middleware("http")
async def markdown_middleware(request: Request, call_next):
    """Middleware to render markdown files."""
    if request.url.path.lower().endswith(".md"):
        try:
            stat = os.stat("./static" + request.url.path)
            etag = b64encode(str(stat.st_mtime).encode()).decode()
        except FileNotFoundError:
            raise HTTPException(404)

        if request.headers.get("if-none-match"):
            if etag == request.headers["if-none-match"]:
                return Response(None, 304)
        with open("./static" + request.url.path) as file:
            content = file.read()

        with open("./static/assets/template-markdown.html") as template:
            html_template = template.read()

        formatted = marko.convert(content)
        _html = html_template.replace("$", formatted)
        comment = "<!-- Automatically generated at {}. -->\n".format(datetime.utcnow().strftime("%c"))

        response = HTMLResponse(comment + _html, headers={"etag": etag})
    else:
        response = await call_next(request)
    return response


@app.get("/server")
def get_server_invite():
    if (datetime.now() + timedelta(hours=1)) >= app.state.invite["fetched_at"] or not config["bot_token"]:
        return app.state.invite["url"]

    widget = get(
        "https://discord.com/api/v8/guilds/772980293929402389/invites",
        headers={"Authorization": "Bot " + config["bot_token"]},
    )
    data = widget.json()
    app.state.invite["url"] = "https://discord.gg/" + data["code"]
    app.state.invite["fetched_at"] = datetime.now()
    return app.state.invite["url"]


@app.get("/pixels")
async def get_pixels_image(resize_x: int = None, resize_y: int = None, fmt: str = "webp"):
    fmt = fmt.lower()
    if fmt not in ["webp", "png", "jpg", "jpeg"]:
        raise HTTPException(406, ["webp", "png", "jpeg", "jpg"])
    max_noise_level = config.get("max_noise", ...)
    if max_noise_level is ...:
        max_noise_level = randomiser.randint(5, 30)
        warn(
            "You should set a noise_level for /pixels by setting `max_noise: int` in config.json."
            " The recommended value is 20 if you really want to stop bots."
        )

    async def e(f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(f, *args, **kwargs))

    try:
        from PIL import Image
    except ImportError:
        raise HTTPException(
            501, {"detail": "This server has not installed dependencies, unable to process pixels data."}
        )
    token = config.get("pixels_token")
    if not token:
        raise HTTPException(501, {"detail": "This server has not provided authentication for the DragDev Pixels API."})
    if token.startswith("$"):
        token = os.getenv(token[1:])
        if not token:
            raise HTTPException(
                501, {"detail": "This server has not provided authentication for the DragDev Pixels API."}
            )
    start_download = datetime.now()
    response = await e(get, "https://pixels.dragdev.xyz/get_pixels", headers={"Authorization": "Bearer " + token})
    content = response.content
    if response.status_code != 200:
        if not app.state.last_canvas:
            raise HTTPException(response.status_code, response.text, dict(response.headers))
        else:
            content = app.state.last_canvas
    else:
        app.state.last_canvas = response.content
    end_download = datetime.now()
    start_fetch_size = datetime.now()
    size = await e(get, "https://pixels.dragdev.xyz/get_size")
    if size.status_code != 200:
        size = {"width": 272, "height": 135}
    else:
        size = await e(size.json)  # we could just use aiohttp...
    end_fetch_size = datetime.now()

    start_render_image = datetime.now()
    img = await e(Image.frombytes, "RGB", tuple(size.values()), content)
    end_render_image = datetime.now()

    # Now we need to "obfuscate" the image to prevent people scraping this endpoint for the canvas
    start_resize_image = datetime.now()
    end_resize_image = datetime.now()
    if resize_x and resize_y:
        # resize the image to the correct width
        resize_x = min(4069, resize_x)
        resize_y = min(2160, resize_y)

        start_resize_image = datetime.now()
        img = await e(img.resize, (resize_x, resize_y), Image.NEAREST)
        end_resize_image = datetime.now()
    start_obfuscate = datetime.now()

    def obfuscate():
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = img.getpixel((x, y))
                noise_level = randomiser.randint(1, max_noise_level)
                r += noise_level
                g += noise_level
                b += noise_level
                img.putpixel((x, y), (r, g, b))
    proc = Process(target=obfuscate)
    print("Starting thread @", proc.native_id)
    proc.start()
    proc.join()
    print("Finished thread @", proc.native_id)
    end_obfuscate = datetime.now()
    timings = {
        "download_image": (end_download - start_download).total_seconds(),
        "fetch_size": (end_fetch_size - start_fetch_size).total_seconds(),
        "render_image": (end_render_image - start_render_image).total_seconds(),
        "resize_image": (end_resize_image - start_resize_image).total_seconds(),
        "obfuscate_image": (end_obfuscate - start_obfuscate).total_seconds(),
    }
    io = BytesIO()
    start_save = datetime.now()
    await e(img.save, io, format=fmt.lower())
    io.seek(0)
    end_save = datetime.now()
    start_read = datetime.now()
    data = await e(io.read)
    end_read = datetime.now()
    timings["save_image"] = (end_save - start_save).total_seconds()
    timings["read_rendered_data"] = (end_read - start_read).total_seconds()
    return Response(
        data,
        203,
        media_type="image/" + fmt,
        headers={
            "Cache-Control": "public,max-age=120",
            "Server-Timing": ", ".join(f"{k};dur={v*1000}" for k, v in timings.items()),
        },
    )


app.mount("/", StaticFiles(directory=config["static_dir"], html=True))

if __name__ == "__main__":
    print("Checking for updates...")
    cmd = subprocess.run(["git", "fetch"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not cmd.stdout:
        print("Site is up to date.")
    else:
        print("Updating...")
        cmd2 = subprocess.run(["git", "pull"] + config.get("git_path", ["origin", "master"]))
        requires_restart = (b"main.py", b"requirements.txt")
        if b"requirements.txt" in cmd2.stdout:
            print("Updating requirements...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-Ur", "requirements.txt"])
        if any(x in requires_restart for x in cmd2.stdout):
            print("Restart required.", file=sys.stderr)
            sys.exit(1)
        print("Done. Starting.")
    uvicorn.run(app, host=config["host"], port=config["port"])
