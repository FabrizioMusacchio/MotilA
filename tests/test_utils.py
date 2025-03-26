# tests/test_utils.py
from motila.utils import hello_world_utils

def test_hello_world(capsys):
    hello_world_utils()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, World! Welcome to MotilA (from utils.py)!"
