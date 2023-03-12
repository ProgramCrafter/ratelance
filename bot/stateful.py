import json
import abc


class IState(abc.ABC):
    registered_states = {}
    
    @abc.abstractmethod
    def needs_message(self): pass
    
    @abc.abstractmethod
    def enter_state(self, in_msg_full, reply, send_callback): pass
    
    @abc.abstractmethod
    def run(self, in_msg_full, reply, send_callback): pass
    
    @staticmethod
    def load(state_repr):
        state_name, state_value = state_repr.split(':', 1)
        return IState.registered_states[state_name].load(state_value)


def RegisterState(state_class):
    IState.registered_states[state_class.__name__] = state_class
    return state_class


class UserStateMachine:
    def __init__(self, start_state):
        self.state = start_state
    
    def __repr__(self):
        return self.state.__class__.__name__ + ':' + repr(self.state)
    
    def next(self, backend, in_msg_full):
        if self.state.needs_message() and not in_msg_full:
            return
        
        def reply(reply_text, keyboard=None):
            backend.send_message(in_msg_full['chat']['id'], reply_text, reply=in_msg_full['message_id'],
                                 keyboard=keyboard)
        
        self.state = self.state.run(in_msg_full, reply, backend.send_message)
    
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
    
    def next(self, backend, in_msg_full):
        if not in_msg_full:
            for chat_id, machine in self.users.items():
                machine.next(backend, in_msg_full)
        else:
            if any(intercept(backend, in_msg_full) for intercept in self.interceptors):
                return
            
            chat_id = in_msg_full['chat'].get('id', 0)
            
            if chat_id not in self.users:
                self.users[chat_id] = UserStateMachine(self.start_state_class())
            
            self.users[chat_id].next(backend, in_msg_full)
    
    def needs_message(self):
        return all(machine.state.needs_message() for machine in self.users.values())
    
    def state_is(self, state_class):
        return any(machine.state_is(state_class) for machine in self.users.values())
