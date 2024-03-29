from cli.keyring import Keyring, process_keyring_cmd
from cli.about import PROMPT_SINGLE, PROMPT, ABOUT
from cli.contracts import process_contract_cmd
from cli.offers import process_offers_cmd
from cli.jobs import process_jobs_cmd
from cli.signing import sign_send
from cli.colors import b, nb
import cli.polyfills

import traceback
import os

from tonsdk.utils import Address
from tonsdk.boc import Cell
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
        donate_addr = 'EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7'
        sign_send([
          (Address(donate_addr), None, Cell(), 5*10**7),
        ], 'donate')
      elif command[0] == 'k':
        with keys: process_keyring_cmd(command, keys)
      elif command[0] == 'j':
        with keys: process_jobs_cmd(command, keys)
      elif command[0] == 'o':
        with keys: process_offers_cmd(command, keys)
      elif command[0] == 'c':
        with keys: process_contract_cmd(command, keys)
      else:
        print(f'{b}not implemented:{nb} {repr(command)}')
    except KeyboardInterrupt:
      print(f'{nb}\noperation cancelled')
    
    print('\n')

try:
  if __name__ == '__main__':
    os.system('')
    main()
except:
  traceback.print_exc()
  input('...')
