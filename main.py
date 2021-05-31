import os
import sys
from json import load, JSONDecodeError
from datetime import datetime, timedelta
from requests import get

import fastapi
import uvicorn
import marko
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import Request, HTTPException

if not os.path.exists("./config.json"):
    print("No config file exists. Please copy 'config.template.json' to 'config.json' and modify it to your system.")
    sys.exit(1)

try:
    with open("./config.json", "r") as config_file:
        config = load(config_file)
except JSONDecodeError:
    print("Invalid JSON.")
    sys.exit(2)

app = fastapi.FastAPI()
app.state.invite = {
    "fetched_at": datetime.min,
    "url": "https://discord.gg/YBNWw7nMGH"
}
if config["allowed_origins"]:
    app.add_middleware(
        CORSMiddleware, allow_origins=config["allowed_origins"]
    )


@app.middleware("http")
async def markdown_middleware(request: Request, call_next):
    """Middleware to render markdown files."""
    if request.url.path.lower().endswith(".md"):
        try:
            with open("./static"+request.url.path) as file:
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


app.mount("/", StaticFiles(directory=config["static_dir"], html=True))
uvicorn.run(app, host=config["host"], port=config["port"])
