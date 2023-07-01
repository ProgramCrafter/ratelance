import logging
import abc

import requests

from tg import check_bot_ok, send, respond_inline_query, yield_messages


class IBackend(abc.ABC):
    @abc.abstractmethod
    def __init__(self): pass
    
    @abc.abstractmethod
    def receive_all_new_messages(self):
        '''
        Receives all new messages from current backend and marks them read.
        
        typeof result = Array[
          {'inline_query': {'id': str, 'from': User, 'query': str, 'offset': str}} |
          {'message': {'message_id': int, 'from': User?, 'date': int, 'chat': Chat,
                       'reply_to_message': Message, 'text': str?}}
        ];
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
                     keyboard=None, parse_mode='html', custom={}):
        return send(chat, text, reply, keyboard, parse_mode, custom)
    
    def respond_inline_query(self, query_id, results, button):
        return respond_inline_query(query_id, results, button)
