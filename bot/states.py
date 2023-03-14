import functools
import logging
import html
import json
import time
import os

from stateful import IState, MultiuserStateMachine, RegisterState

import cli.polyfills  # ordering is important
from cli.jobs import load_jobs


def flatten(arr):
    for row in arr:
        yield from row


def is_cmd(message, command):
    return message.startswith(command + ' ') or message == command


@RegisterState
class StartState(IState):
    '''
    Welcome state, where everyone not yet known to bot starts.
    '''
    def needs_message(self):
        return True
    
    def enter_state(self, in_msg_full, reply, send_callback):
        reply_text = f'''
Hello, <b>{in_msg_full['from']['first_name']}</b>! How could I serve you?
'''.strip()
        
        reply(reply_text, keyboard=[
          ['List available jobs', 'Look up job status', 'List offers to specific job']
        ])
    
    def run(self, in_msg_full, reply, send_callback):
        in_msg_body = in_msg_full.get('text', '')
        if in_msg_body == '/restart' and in_msg_full['from']['id'] == 1463706336:
          reply('Restarting.')
          os.startfile(__file__.removesuffix('states.py') + 'main.py')
          return SentinelState(self)
        
        if in_msg_body == 'List available jobs':
          job_texts = ['=== Available jobs ===']
          for (job, poster, value, desc) in load_jobs():
            job_texts.append(f'Order by <pre>{poster}</pre> worth approximately {value/1e9} TON')
            job_texts.append(f'Address: <pre>{job}</pre>')
            job_texts.append(desc)
            job_texts.append('')
          
          reply('\n'.join(job_texts))
          
          self.enter_state(in_msg_full, reply, send_callback)
          return self
        
        self.enter_state(in_msg_full, reply, send_callback)
        return self
    
    def __repr__(self):
        return ''
    
    @staticmethod
    def load(state_repr):
        return StartState()


@RegisterState
class SentinelState(IState):
    '''
    State where bot needs to shutdown.
    '''
    def __init__(self, previous_state=None):
        logging.debug(f'State just before bot shutdown: {previous_state}')
        self.previous_state = previous_state
    
    def needs_message(self):
        return False
    
    def enter_state(self, in_msg_full, reply, send_callback):
        reply('Stopping.')
    
    def run(self, in_msg_full, reply, send_callback):
        return self
    
    def __repr__(self):
        if not self.previous_state:
            return ''
        
        return self.previous_state.__class__.__name__ + ':' + repr(self.previous_state)
    
    @staticmethod
    def load(state_repr):
        logging.info(f'Loading SentinelState: {state_repr}')
        
        if state_repr != 'None':
            return IState.load(state_repr)    # state just before SentinelState
        
        return SentinelState()


def format_donation_msg():
    return '''
TON, mainnet: <pre>EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7</pre>
ton://transfer/EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7
'''.strip()


def donation_middleware(backend, in_msg_full):
    in_msg_body = in_msg_full.get('text', '')
    sender = in_msg_full['from']['id']
    lt = in_msg_full['message_id']
    
    if in_msg_body == '/donate':
        backend.send_message(sender, format_donation_msg(), reply=lt)
        return True
    else:
        return False
