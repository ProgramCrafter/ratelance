#!/usr/bin/python3
# encoding: utf-8

import traceback
import logging
import queue

from states import StartState, SentinelState
from stateful import MultiuserStateMachine
from backends import UnitTestBackend


logging.basicConfig(format='%(asctime)s    [%(levelname)s]    %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S',
                    level=logging.DEBUG)

dialogue = '''
12223822 > /start

12223822 < Hello, <b>12223822</b>!
'''

# intentionally not wrapped in `if __name__ == '__main__':`
# tests should be executed when file is imported

try:
    machine = MultiuserStateMachine(StartState)
    backend = UnitTestBackend(dialogue)
    
    messages = queue.SimpleQueue()
    
    while not backend.test_succeeded():
        if machine.state_is(SentinelState):
            raise Exception('[TEST]    Machine tried to stop before test end')
        
        if messages.empty() and machine.needs_message():
            for e in backend.receive_all_new_messages():
                logging.info(f'[TEST]    Putting message into queue: {e}')
                messages.put_nowait(e)
        
        if not machine.needs_message():
            machine.next(backend, None)
        elif not messages.empty():
            msg = messages.get_nowait()
            
            logging.info(f'[TEST]    Processing message from queue: {msg}')
            machine.next(backend, msg)
    
    logging.info('[TEST]    success')
except:
    logging.error(f'[TEST]    failed: {traceback.format_exc()}')
finally:
    if __name__ == '__main__':
        input('...')
