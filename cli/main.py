from colors import nh, h, nb, b, ns, s
from about import PROMPT_SINGLE, PROMPT, ABOUT

import traceback
import os



def main():
  while True:
    print(PROMPT_SINGLE)
    
    try:
      while not (command := input(PROMPT).lower().strip()):
        pass
    except KeyboardInterrupt:
      command = 'q'
    
    if not command:
      pass
    elif command == 'h':
      print(ABOUT)
    elif command == 'q':
      break
    elif command == 'kl':
      print(f'Keyring: {len([])} keys')
    else:
      print(f'{b}not implemented:{nb} {repr(command)}')
    
    print()

try:
  os.system('')
  main()
except:
  traceback.print_exc()
  input('...')
