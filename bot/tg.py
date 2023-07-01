__all__ = ['check_bot_ok', 'send', 'yield_messages']


import traceback
import logging

import requests

from persistence import PersistentValue
from utils import TOKEN


url = 'https://api.telegram.org/bot%s/' % TOKEN
update_id = PersistentValue('update_id.txt', default=0)


def check_bot_ok():
    assert requests.get(url + 'getMe').json()['ok']


def yield_messages():
    '''
    Generator yielding new messages sent from users to Telegram bot.
    '''
    
    try:
        updates = requests.get(url + 'getUpdates', params={
            'offset': update_id.get() + 1,
            'timeout': 15
        }, timeout=20).json()
    except requests.exceptions.ReadTimeout:
        return
    except Exception as e:
        logging.error(repr(e))
        return
    
    if not updates['ok']:
        logging.error('Request failed: ' + updates['description'])
        return
    
    for update in updates['result']:
        update_id.set_max(update['update_id'])
        
        '''
        typeof update = 
          {'inline_query': {'id': str, 'from': User, 'query': str, 'offset': str}} |
          {'message': {'message_id': int, 'from': User?, 'date': int, 'chat': Chat,
                       'reply_to_message': Message, 'text': str?}};
        '''
        
        if 'message' in update or 'inline_query' in update:
            logging.debug(update)
            yield update


def respond_inline_query(query_id, results, button):
    msg_params = {
        'inline_query_id': query_id,
        'results': results,
        'is_personal': True,
        'cache_time': 40
    }
    if button: msg_params['button'] = button
    
    logging.warning(msg_params)
    try:
        result = requests.post(url + 'answerInlineQuery', json=msg_params).json()
    except:
        result = {'ok': False, 'description': traceback.format_exc()}
    
    if not result.get('ok', False):
        logging.warning('Inline responding failed ' + str(result))
    
    return result


def send(chat, text, reply=None, keyboard=None, parse_mode='html', custom={}):
    '''
    Function sending message `text` via Telegram bot to user specified by `chat`.
    If `reply` is specified, the sent message is reply to message with specified ID.
    `keyboard` must be either None or List[List[str]] - buttons' text.
    `parse_mode` is forwarded to Telegram as-is and changes text handling.
    '''
    
    msg_params = {'chat_id': chat, 'text': text, 'parse_mode': parse_mode}
    
    if reply:
        msg_params['reply_to_message_id'] = reply
    
    if keyboard:
        msg_params['reply_markup'] = {
          'keyboard': keyboard,
          'one_time_keyboard': True
        }
    else:
        msg_params['reply_markup'] = {'remove_keyboard': True}
    
    msg_params.update(custom)
    
    try:
        result = requests.post(url + 'sendMessage', json=msg_params).json()
    except:
        result = {'ok': False, 'description': traceback.format_exc()}
    
    if not result.get('ok', False):
        logging.warning('Sending message failed ' + str(result))
    
    return result
