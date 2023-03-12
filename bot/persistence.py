import json
import os


class PersistentValue:
    def __init__(self, filename, default):
        path_s = os.path.sep
        
        self_dir = __file__ + path_s + '..' + path_s
        self.path = os.path.abspath(self_dir + filename)
        
        try:
            with open(self.path, 'r') as f:
                self.value = json.load(f)
        except:
            self.value = default
    
    def get(self):
        return self.value
    
    def set(self, value):
        self.value = value
        self.flush()
    
    def flush(self):
        with open(self.path, 'w') as f:
            json.dump(self.value, f)
    
    def set_max(self, value):
        if value > self.value:
            self.set(value)
