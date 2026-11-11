# Root entry point for Vercel: it looks for a Flask instance called "app" in this file.
from crb.app import create_app

app = create_app()
