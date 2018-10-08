import os
import yaml
import traceback
import re
from ros.util import Resource

class Config(dict):
    def __init__(self, config="ros.yaml", prefix=''):
        '''
        if not config.startswith (os.sep):
            config = os.path.join (os.path.dirname (__file__), config)
        '''
        if isinstance(config, str):
            config_path = Resource.get_resource_path (config)
            with open(config_path, 'r') as f:
                self.conf = yaml.safe_load (f)
        elif isinstance(config, dict):
            self.conf = config
        else:
            raise ValueError
        self.prefix = prefix
    def get_service (self, service):
        result = {}
        try:
            result = self['translator']['services'][service]
        except:
            traceback.print_exc()
        return result
    def __setitem__(self, key, val):
        raise TypeError("Setting configuration is not allowed.")
    def __str__(self):
        return "Config with keys: "+', '.join(list(self.conf.keys()))
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    def __getitem__(self, key):
        '''
        Use this accessor instead of getting conf directly in order to permit overloading with environment variables.
        Imagine you have a config file of the form

          person:
            address:
              street: Main

        This will be overridden by an environment variable by the name of PERSON_ADDRESS_STREET,
        e.g. export PERSON_ADDRESS_STREET=Gregson
        '''
        key_var = re.sub('[\W]', '', key)
        name = self.prefix+'_'+key_var if self.prefix else key_var
        try:
            env_name = name.upper()
            return os.environ[env_name]
        except KeyError:
            value = self.conf[key]
            if isinstance(value, dict):
                return Config(value, prefix=name)
            else:
                return value
