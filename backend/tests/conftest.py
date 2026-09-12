import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def set_test_env():
    os.environ["TESTING"] = "1"
