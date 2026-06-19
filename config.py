import os
import sys


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Error: {name} environment variable is required.", file=sys.stderr)
        sys.exit(1)
    return value


def get_database_url() -> str:
    db_url = require_env("DATABASE_URL")
    if "@db:" in db_url and not os.path.exists("/.dockerenv"):
        return db_url.replace("@db:", "@localhost:")
    return db_url
