import json
import os
import pytest
from ros.config import Config

@pytest.fixture(scope='module')
def config():
    return Config ("ros.yaml")

def test_config (config):
    assert config['USER'] == os.environ['USER']
