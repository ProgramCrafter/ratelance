import logging
import abc

import requests

from tg import check_bot_ok, send, yield_messages
from stem import StemClient


class IBackend(abc.ABC):
    @abc.abstractmethod
    def __init__(self): pass
    
    @abc.abstractmethod
    def receive_all_new_messages(self):
        '''
        Receives all new messages from current backend and marks them read.
        Yields tuples (chat_id, message_text, message_id).
        '''
        pass
    
    @abc.abstractmethod
    def send_message(self, chat, text, **kw):
        pass


class TelegramBackend(IBackend):
    '''
    Standard bot backend: Telegram.
    '''
    def __init__(self):
        check_bot_ok()
    
    def receive_all_new_messages(self):
        yield from yield_messages()
    
    def send_message(self, chat, text, reply=None,
                     keyboard=None, parse_mode='html'):
        return send(chat, text, reply, keyboard, parse_mode)


class StemBackend(IBackend):
    '''
    Backend transferring messages through https://stem.fomalhaut.me.
    This bridge does not have concept of users, keyboards, message parsing and replies.
    '''
    def __init__(self):
        self.client = StemClient()
        self.client.subscribe('ratelance-chat')
    
    def receive_all_new_messages(self):
        message = self.client.recv()
        if message and not message.startswith(b'>>>'):
            yield {
              'from': {'id': -1, 'first_name': 'Stem'},
              'text': msg.decode('utf-8'),
              'message_id': int.from_bytes(msg, 'big')
            }
    
    def send_message(self, chat, text, reply=None,
                     keyboard=None, parse_mode='html'):
        # special way to display keyboard
        if keyboard:
          keyboard_repr = '\n' + '\n'.join(repr(row) for row in keyboard)
        else:
          keyboard_repr = ''
        
        self.client.send('ratelance-chat', f'>>> {reply}\n{text}{keyboard_repr}')


class UnitTestBackend(IBackend):
    '''
    Allows to test bot against predefined dialogues before deployment.
    Raises exception on message mismatch or absence.
    '''
    def __init__(self, expected_dialogue):
        self.messages = []
        
        for line in expected_dialogue.strip().split('\n\n')[::-1]:
            chat_id, direction, msg = line.split(' ', 2)
            
            self.messages.append((int(chat_id), direction, msg))
    
    def receive_all_new_messages(self):
        sent_messages = []
        
        while self.messages and self.messages[-1][1] == '>':
            chat_id, direction, msg = self.messages.pop()
            sent_messages.append({
              'from': {'id': chat_id, 'first_name': f'Test{chat_id}'},
              'text': msg,
              'message_id': len(self.messages)
            })
        
        if not sent_messages:
            raise Exception('No further messages sent till current moment')
        
        return sent_messages
    
    def send_message(self, chat, text, reply=None, keyboard=None):
        if not self.messages:
            raise Exception('No further messages sending expected')
        
        current_msg = (chat, '<', text)
        needed = self.messages[-1]
        
        if needed != current_msg:
            raise Exception(f'Message mismatch: expected {needed}, got {current_msg}')
        
        logging.info(f'[TEST]    Sent message correctly: {chat} < {text}')
        
        self.messages.pop()
    
    def test_succeeded(self):
        return not self.messages
