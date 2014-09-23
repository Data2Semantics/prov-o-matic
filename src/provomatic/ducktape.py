import rdflib
import json
import requests

from builder import add_prov

import logging

log = logging.getLogger('provomatic.ducktape')
log.setLevel(logging.DEBUG)

class Ducktape(object):
    
    _ip = None
    
    def __init__(self, ip):
        self._ip = ip
        return

    def load(self, provenance_uri,data_uri):
        r = requests.get(data_uri)
        
        tables = json.loads(r.content)
        
        for name,data in tables.items():
            log.debug("Loading {}".format(name))
            self._ip.push({name: data})
            self.__dict__[name] = data
            
            
            
            
        r = requests.get(provenance_uri)
        add_prov(provenance_uri,r.content)
        
    
            
        
    
    
    


