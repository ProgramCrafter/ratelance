from keyring import Keyring, process_keyring_cmd
from about import PROMPT_SINGLE, PROMPT, ABOUT
from colors import nh, h, nb, b, ns, s

import traceback
import os



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
      elif command[0] == 'k':
        with keys: process_keyring_cmd(command, keys)
      else:
        print(f'{b}not implemented:{nb} {repr(command)}')
    except KeyboardInterrupt:
      print(f'{nb}\noperation cancelled')
    
    print()

try:
  os.system('')
  main()
except:
  traceback.print_exc()
  input('...')
