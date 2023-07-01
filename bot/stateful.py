import json
import abc


class IState(abc.ABC):
    registered_states = {}
    
    @abc.abstractmethod
    def needs_message(self): pass
    
    @abc.abstractmethod
    def enter_state(self, message_info, reply, send_callback): pass
    
    @abc.abstractmethod
    def run(self, message_info, reply, send_callback): pass
    
    @staticmethod
    def load(state_repr):
        state_name, state_value = state_repr.split(':', 1)
        return IState.registered_states[state_name].load(state_value)


def RegisterState(state_class):
    IState.registered_states[state_class.__name__] = state_class
    return state_class


def _load_chat_id(message_info):
    if 'inline_query' in message_info:
        return message_info['inline_query']['from']['id']
    elif 'message' in message_info:
        return message_info['message'].get('chat', {}).get('id', -1)
    else:
        # unreachable
        return -2


class UserStateMachine:
    def __init__(self, start_state):
        self.state = start_state
    
    def __repr__(self):
        return self.state.__class__.__name__ + ':' + repr(self.state)
    
    def next(self, backend, message_info):
        '''
        typeof message_info = 
          {'inline_query': {'id': str, 'from': User, 'query': str, 'offset': str}} |
          {'message': {'message_id': int, 'from': User?, 'date': int, 'chat': Chat,
                       'reply_to_message': Message, 'text': str?}};
        '''
        
        if self.state.needs_message() and not message_info:
            return
        
        chat_id = _load_chat_id(message_info)
        
        if 'message' in message_info:
            incoming_id = message_info['message']['message_id']
            
            def reply(reply_text, **kw):
                backend.send_message(chat_id, reply_text, reply=incoming_id, **kw)
            
            self.state = self.state.run(message_info, reply, backend.send_message)
        else:
            incoming_id = message_info['inline_query']['id']
            
            def reply_inline(results, button, **kw):
                backend.respond_inline_query(incoming_id, results, button, **kw)
            
            self.state = self.state.run(message_info, reply_inline, None)
        
    
    def state_is(self, state_class):
        return isinstance(self.state, state_class)
    
    @staticmethod
    def load(machine_repr):
        self = UserStateMachine(None)
        self.state = IState.load(machine_repr)
        return self


class MultiuserStateMachine:
    def __init__(self, start_state_class):
        self.start_state_class = start_state_class
        self.interceptors = []
        self.users = {}
    
    def __repr__(self):
        return json.dumps({str(chat_id): repr(machine)
                           for (chat_id, machine) in self.users.items()})
    
    @staticmethod
    def load(users_repr, start_state_class):
        self = MultiuserStateMachine(start_state_class)
        self.users = {int(chat_id): UserStateMachine.load(machine_repr)
                      for (chat_id, machine_repr) in json.loads(users_repr).items()}
        return self
    
    def next(self, backend, message_info):
        '''
        typeof message_info = 
          {'inline_query': {'id': str, 'from': User, 'query': str, 'offset': str}} |
          {'message': {'message_id': int, 'from': User?, 'date': int, 'chat': Chat,
                       'reply_to_message': Message, 'text': str?}};
        '''
        
        if not message_info:
            for chat_id, machine in self.users.items():
                machine.next(backend, message_info)
        else:
            if any(intercept(backend, message_info) for intercept in self.interceptors):
                return
            
            chat_id = _load_chat_id(message_info)
            
            if chat_id not in self.users:
                self.users[chat_id] = UserStateMachine(self.start_state_class())
            
            self.users[chat_id].next(backend, message_info)
    
    def needs_message(self):
        return all(machine.state.needs_message() for machine in self.users.values())
    
    def state_is(self, state_class):
        return any(machine.state_is(state_class) for machine in self.users.values())
