import functools
import logging
import secrets
import html
import json
import time
import os

from stateful import IState, MultiuserStateMachine, RegisterState, load_chat_id
from keyutils import KeyCustodialUtils
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
        chat_id = load_chat_id(message_info)
        keypair = KeyCustodialUtils.get_keypair_for_user(chat_id)
        
        if 'message' in message_info:
            text = message_info['message'].get('text', '')
            if text == '/setwallet' or text == '/start set-wallet':
                new_state = SetWalletState(self.settings)
                new_state.enter_state(message_info, reply, send_callback)
                return new_state
            if text == '/me' or text == '/start me':
                wallet_text = f'Wallet: <pre>{self.settings.get("address","")}</pre>\n'
                pkey_text = f'Public key - ID {keypair["key_id"]}: <pre>{keypair["public_armored"]}</pre>'
                reply(wallet_text + pkey_text, keyboard=[['Show secret key'], ['/setwallet']])
            if text == 'Show secret key' or text == '/showsecret':
                chat_id = message_info['message']['chat']['id']
                keypair = KeyCustodialUtils.get_keypair_for_user(chat_id)
                reply('<pre>%s</pre>' % keypair['secret_armored'])
                
            return self
        elif 'chosen_inline_result' in message_info:
            reply(JobPostUtils.format_deploy_links(
                message_info['chosen_inline_result']['query'],
                self.settings['address'],
                keypair['public']
            ))
            return self
        
        if 'address' not in self.settings:
            reply([], {'text': 'Set wallet address', 'start_parameter': 'set-wallet'})
        elif message_info['inline_query']['chat_type'] in ('group', 'supergroup'):
            reply([], {'text': 'Usage in groups is locked', 'start_parameter': 'me'})
        else:
            reply(JobPostUtils.format_article_list(
                message_info['inline_query']['query'],
                self.settings['address'],
                keypair['public']
            ), None)
            
            chat_id = message_info['inline_query']['from']['id']
            # send_callback(chat_id, 'You need to deploy the job.')
        
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
    elif in_msg_body == '//restart':
        os.startfile(__file__.replace('states.py', 'main.py'))
        raise KeyboardInterrupt
    else:
        return False
