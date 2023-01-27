import base64
import sys

with open(__file__ + '/../' + sys.argv[1], 'rb') as f:
  print(base64.b16encode(f.read()).decode('ascii'))
