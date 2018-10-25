import copy
import json
import os
import yaml
import traceback
import re
from ros.util import Resource

class Config(dict):
    def __init__(self, config=None, prefix=''):
        if config == None:
            local_config = os.path.expanduser("~/.ros.yaml")
            default_config = os.path.join(os.path.dirname(__file__), "ros.yaml")
            config = local_config if os.path.exists (local_config) else default_config
        if isinstance(config, str):
            config_path = Resource.get_resource_path (config)
            with open(config_path, 'r') as f:
                self.conf = yaml.safe_load (f)
        elif isinstance(config, dict):
            self.conf = config
        else:
            raise ValueError
        
        self.prefix = prefix

        new_conf = copy.deepcopy (self.conf)
        self.key_dig (base_k = None,
                      k = None,
                      d = self.conf,
                      root_d = new_conf)
        #print (json.dumps(new_conf, indent=2))
        self.conf.update (new_conf)
        
    def key_dig (self, base_k, k, d, root_d):
        if base_k:
            if k:
                this_key = f"{base_k}_{k}"
            else:
                raise ValueError ("shouldn't happen")
        else:
            if k:
                this_key = k
            else:
                this_key = ""
        if isinstance (d, dict):
            for nk, nv in d.items ():
                v = self.key_dig (
                    base_k = this_key,
                    k = nk,
                    d = nv,
                    root_d = root_d)
        elif isinstance(d, str):
            root_d[this_key] = str(d)
            root_d[this_key.upper()] = str(d)
    
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
