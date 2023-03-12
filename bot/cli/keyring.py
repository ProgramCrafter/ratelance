from .colors import nh, h, nb, b, ns, s

from base64 import b16encode as hex_encode_b2b
from base64 import b16decode
import traceback
import hashlib
import time
import os

import nacl.signing
import nacl.secret



def b16encode(v):
  return hex_encode_b2b(v).decode('ascii')

class Keyring:
  def __init__(self, path=None):
    self.path = path or self.generate_keyring_path()
    self.keys_info = {}
  
  def __enter__(self):
    try:
      with open(self.path, 'r') as f:
        self.parse_keys_from(f)
    except IOError:
      open(self.path, 'x').close()
    return self      
  
  def __exit__(self, exc_type, exc_val, exc_trace):
    try:
      with open(self.path, 'r') as f:
        self.parse_keys_from(f)
    except IOError:
      pass
    
    self.flush_keys()
    
    if exc_val:
      raise
  
  def generate_keyring_path(self):
    appdata = os.environ['LOCALAPPDATA']
    return os.path.abspath(appdata + '/ratelance-private-keys.dat')
  
  def flush_keys(self):
    with open(self.path, 'w') as f:
      self.write_keys_to(f)
  
  def parse_keys_from(self, file):
    for line in file:
      version, public_key, secret_key, name = line.strip().split(' ', 3)
      assert version == 'v0.0.2'
      assert public_key.startswith('pub:ed25519:vk:')
      assert secret_key.startswith('prv:ed25519:sk:')
      
      key_id = hashlib.sha256(public_key.encode('ascii')).hexdigest()[::8]
      
      self.keys_info[key_id] = {
        'public': b16decode(public_key.removeprefix('pub:ed25519:vk:')),
        'secret': b16decode(secret_key.removeprefix('prv:ed25519:sk:')),
        'key_id': key_id,
        'name':   name
      }
  
  def write_keys_to(self, file):
    for (key_id, key_info) in self.keys_info.items():
      public_key = 'pub:ed25519:vk:' + b16encode(key_info['public'])
      secret_key = 'prv:ed25519:sk:' + b16encode(key_info['secret'])
      
      print('v0.0.2', public_key, secret_key, key_info['name'],
            file=file, flush=True)
  
  def add_key(self, secret_bytes, name):
    secret_key_obj = nacl.signing.SigningKey(secret_bytes)
    public_bytes = secret_key_obj.verify_key.encode()
    
    public_key_armored = 'pub:ed25519:vk:' + b16encode(public_bytes)
    key_id = hashlib.sha256(public_key_armored.encode('ascii')).hexdigest()[::8]
    
    self.keys_info[key_id] = {
      'public': public_bytes,
      'secret': secret_bytes,
      'key_id': key_id,
      'name':   name
    }
    self.flush_keys()
    return self.keys_info[key_id]
  
  def generate_new_key(self):
    return self.add_key(
      nacl.secret.random(32),
      f'''key@[{time.strftime('%Y.%m.%d %H:%M:%S')}]'''
    )


def process_keyring_cmd(command, keyring):
  if command == 'kl':
    print('Keys list:')
    
    for (key_id, key_info) in keyring.keys_info.items():
      print(f'- {b}{key_id}{nb} -', repr(key_info['name']))
    
  elif command == 'ke':
    key_id = input(f'  {h}Key ID:{nh} ')
    
    try:
      key_info = keyring.keys_info[key_id]
      assert key_info['key_id'] == key_id
      print('- ID:        ', key_id)
      print('- Name:      ', key_info['name'])
      print('- Public key:', b16encode(key_info['public']))
      print('- Secret key:', b16encode(key_info['secret']))
    except:
      traceback.print_exc()
    
  elif command == 'ki':
    secret = input(f'  {h}HEX secret key:{nh} ')
    name   = input(f'  {h}Key name:{nh} ')
    
    try:
      secret_bytes = b16decode(secret.upper())
      assert len(secret_bytes) == 32
      keyring.add_key(secret_bytes, name)
    except:
      traceback.print_exc()
      
  elif command == 'kn':
    key_info = keyring.generate_new_key()
    print(f'{h}Created key{nh}', key_info['key_id'], repr(key_info['name']))
    
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')
