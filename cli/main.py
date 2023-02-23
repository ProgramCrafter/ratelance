from keyring import Keyring, process_keyring_cmd
from about import PROMPT_SINGLE, PROMPT, ABOUT
from signing import sign_for_sending
from colors import b, nb

import traceback
import os

from tonsdk.utils import Address
from tonsdk.boc import Cell
from base64 import b64encode
import requests



def main():
  keys = Keyring()
  
  while True:
    print(PROMPT_SINGLE)
    
    try:
      while not (command := input(PROMPT).lower().strip()):
        pass
    except KeyboardInterrupt:
      command = 'q'
    
    try:
      if not command:
        pass
      elif command == 'h':
        print(ABOUT)
      elif command == 'q':
        break
      elif command == 'd':
        dest = 'EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7'
        payload = Cell()
        signed = sign_for_sending(payload, Address(dest), None,
                                  5*10**7, 'donate')
        if signed:
          requests.post('https://tonapi.io/v1/send/boc', json={
            'boc': b64encode(signed.to_boc(False)).decode('ascii')
          })
      elif command[0] == 'k':
        with keys: process_keyring_cmd(command, keys)
      else:
        print(f'{b}not implemented:{nb} {repr(command)}')
    except KeyboardInterrupt:
      print(f'{nb}\noperation cancelled')
    
    print('\n')

try:
  os.system('')
  
  
  
  main()
except:
  traceback.print_exc()
  input('...')
