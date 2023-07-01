#!/usr/bin/python3
# encoding: utf-8

from collections import deque
import traceback
import logging
import html
import time
import os


# Checking all third-party libraries are installed before proceeding.
import install_libs

import portalocker

from states import StartState, SentinelState, donation_middleware
from stateful import MultiuserStateMachine
from backends import TelegramBackend


# Setting logging configuration before `test.py` is launched.
logging.basicConfig(format='%(asctime)s  [%(levelname)s]  %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S',
                    filename=os.path.abspath(__file__+'/../bot.log'),
                    level=logging.DEBUG)


# import test


LOCK_PATH = os.path.abspath(__file__ + '/../.lock')


def load_multiuser_machine():
    try:
        with open(os.path.abspath(__file__ + '/../bot.json')) as f:
            return MultiuserStateMachine.load(f.read(), StartState)
    except FileNotFoundError:
        return MultiuserStateMachine(StartState)


try:
    # Waiting for old bot instance to close.
    
    logging.info('Bot is waiting for older instance to close.')
    time.sleep(1)
    
    messages = deque()
    
    with portalocker.Lock(LOCK_PATH, 'w') as _:
        logging.info('Bot started.')
        backend = TelegramBackend()
        machine = load_multiuser_machine()
        machine.interceptors.append(donation_middleware)
        
        while not machine.state_is(SentinelState):
            if not len(messages) and machine.needs_message():
                for e in backend.receive_all_new_messages():
                    logging.info(f'Putting message into queue: {e}')
                    messages.append(e)
        
            if not machine.needs_message():
                machine.next(backend, None)
            elif len(messages):
                msg = messages.popleft()
                
                logging.info(f'Processing message from queue: {msg}')
                machine.next(backend, msg)
            
            time.sleep(2)

except KeyboardInterrupt:
    logging.warning(backend.send_message(1463706336, 'Stopped by KeyboardInterrupt'))
except:
    logging.error('Started sending crash log')

    remaining_messages = list(messages)

    if 'machine' not in globals(): machine = None
    if 'remaining_messages' not in globals(): remaining_messages = None

    crash_log = f'''
<b>BOT CRASHED</b>
<i>Unparsed messages:</i> {html.escape(repr(remaining_messages))}

<i>Machine state:</i> {html.escape(repr(machine))}

{html.escape(traceback.format_exc())}
    '''.strip()

    logging.error(crash_log)
    logging.warning(backend.send_message(1463706336, crash_log))
finally:
    logging.info('Bot has stopped.')

    with open(os.path.abspath(__file__ + '/../bot.json'), 'w') as f:
        f.write(repr(machine))
