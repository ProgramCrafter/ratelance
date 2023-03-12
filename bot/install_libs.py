import shlex
import sys
import os

interpreter = sys.executable.replace('pythonw', 'python')
pip_prefix = shlex.quote(interpreter).replace("'", '"') + ' -m pip install '

try:
    import portalocker
except:
    print(pip_prefix + 'portalocker')
    os.system(pip_prefix + 'portalocker')

try:
    import requests
except:
    os.system(pip_prefix + 'requests')

try:
    import tonsdk
except:
    os.system(pip_prefix + 'tonsdk bitstring==3.1.9')

try:
    import nacl
except:
    os.system(pip_prefix + 'pynacl')
