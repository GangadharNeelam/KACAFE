"""Flask server and cache configuration."""
import dash
import dash_bootstrap_components as dbc
from datetime import timedelta
from flask_caching import Cache
from config import config

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
    title="KA KAFE Operations",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

server = app.server
server.secret_key = config.SECRET_KEY
server.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    hours=config.SESSION_LIFETIME_HOURS
)

cache = Cache(server, config={"CACHE_TYPE": config.CACHE_TYPE})
