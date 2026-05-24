import pytest

# Ensure pytest-asyncio works in auto mode for our WS tests
pytest_plugins = ("pytest_asyncio",)
