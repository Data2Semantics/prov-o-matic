from builder import get_dataset
from rdflib import Graph

from IPython.display import HTML
import hashlib
import requests

PROVOVIZ_SERVICE = "http://semweb.cs.vu.nl/provoviz/service"

def view_prov():
    graph = Graph()
    
    for s,p,o,_ in get_dataset().quads(None) :
        graph.add((s,p,o))
    
    graph_ttl = graph.serialize(format='turtle')
    
    graph_uri = "http://provomatic.org/export/{}".format(hashlib.md5(graph_ttl).hexdigest())
    
    payload = {'graph_uri': graph_uri, 'data': graph_ttl}
    response = requests.post(PROVOVIZ_SERVICE, data=payload)
    
    print response.text
    
    return HTML(response.text)
    
    