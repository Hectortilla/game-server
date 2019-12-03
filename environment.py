import importlib
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'environment'), 'r') as _file:
    environment = _file.read().replace('\n', '')

if os.environ.get('DOCKER') is not None:
    environment = 'docker'

settings = importlib.import_module('settings.%s' % environment)
