import os
import sys
from json import load, JSONDecodeError
from datetime import datetime, timedelta
from requests import get

import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

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
