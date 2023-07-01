import functools
import logging
import secrets
import html
import json
import time
import os

from stateful import IState, MultiuserStateMachine, RegisterState
from textutils import JobPostUtils

import cli.polyfills
from cli.dnsresolver import resolve_to_userfriendly, TONDNSResolutionError


def flatten(arr):
    for row in arr:
        yield from row


#VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
'''
typeof message_info = 
  {'inline_query': {'id': str, 'from': User, 'query': str, 'offset': str}} |
  {'message': {'message_id': int, 'from': User?, 'date': int, 'chat': Chat,
               'reply_to_message': Message, 'text': str?}};
'''
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


@RegisterState
class StartState(IState):
    '''
    Welcome state, where everyone not yet known to bot starts.
    '''
    
    def __init__(self, settings=None): self.settings = settings or {}
    def needs_message(self): return True
    def enter_state(self, message_info, reply, send_callback): pass
    
    @staticmethod
    def load(state_repr):   return StartState(json.loads(state_repr))
    def __repr__(self):     return json.dumps(self.settings)
    
    def run(self, message_info, reply, send_callback):
        if 'message' in message_info:
            text = message_info['message'].get('text', '')
            if text == '/start set-wallet':
                new_state = SetWalletState(self.settings)
                new_state.enter_state(message_info, reply, send_callback)
                return new_state
            return self
        
        if 'address' not in self.settings:
            reply([], {'text': 'Set wallet address', 'start_parameter': 'set-wallet'})
            return self
        
        reply(JobPostUtils.format_article_list(
            message_info['inline_query']['query'],
            self.settings['address']
        ), None)
        
        return self


@RegisterState
class SetWalletState(IState):
    def __init__(self, settings=None): self.settings = settings or {}
    def needs_message(self): return True
    def enter_state(self, message_info, reply, send_callback):
        reply('Provide your TON wallet address in any format.')
    
    @staticmethod
    def load(state_repr):   return StartState(json.loads(state_repr))
    def __repr__(self):     return json.dumps(self.settings)
    
    def run(self, message_info, reply, send_callback):
        if 'message' in message_info:
            text = message_info['message'].get('text', '')
            try:
                self.settings['address'] = resolve_to_userfriendly(text)
                reply(f'Wallet address set to {self.settings["address"]}.', custom={
                    'reply_markup': {'inline_keyboard': [[{
                        'text': 'Back to original chat',
                        'switch_inline_query': ''
                    }]]}
                })
                return StartState(self.settings)
            except TONDNSResolutionError as e:
                reply('Error when resolving address: ' + str(e) + '. Please, try again.')
            except Exception as e:
                reply(repr(e))
        else:
            reply([], {'text': 'Set wallet address', 'start_parameter': 'set-wallet'})
        return self


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
    
    def enter_state(self, message_info, reply, send_callback):
        reply('Stopping.')
    
    def run(self, message_info, reply, send_callback):
        return self
    
    @staticmethod
    def load(state_repr):
        logging.info(f'Loading SentinelState: {state_repr}')
        if state_repr != 'None': return IState.load(state_repr)    # state just before SentinelState
        return SentinelState()
    def __repr__(self):
        if not self.previous_state: return ''
        return self.previous_state.__class__.__name__ + ':' + repr(self.previous_state)


def format_donation_msg():
    return '''
TON, mainnet: <pre>EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7</pre>
ton://transfer/EQCyoez1VF4HbNNq5Rbqfr3zKuoAjKorhK-YZr7LIIiVrSD7
'''.strip()


def donation_middleware(backend, in_msg_full):
    if 'message' not in in_msg_full: return
    in_msg_full = in_msg_full['message']
    in_msg_body = in_msg_full.get('text', '')
    sender = in_msg_full['from']['id']
    lt = in_msg_full['message_id']
    
    if in_msg_body == '/donate':
        backend.send_message(sender, format_donation_msg(), reply=lt)
        return True
    elif in_msg_body == '/stopkb':
        raise KeyboardInterrupt
    else:
        return False
