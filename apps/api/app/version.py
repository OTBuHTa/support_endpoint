"""Single source of truth for runtime release identity."""

import os

API_VERSION = "0.9.0-rc1"
BUILD_REVISION = os.getenv("APP_BUILD_REVISION", "unknown")
