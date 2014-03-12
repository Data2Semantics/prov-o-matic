from builder import get_dataset
from rdflib import Graph

from IPython.display import HTML
import hashlib
import requests
import os 

#PROVOVIZ_SERVICE = "http://semweb.cs.vu.nl/provoviz/service"
PROVOVIZ_SERVICE = "http://localhost:5000/service"


def view_prov():
    graph = Graph()
    
    for s,p,o,_ in get_dataset().quads(None) :
        graph.add((s,p,o))
    
    graph_ttl = graph.serialize(format='turtle')
    
    digest = hashlib.md5(graph_ttl).hexdigest()
    
    graph_uri = "http://provomatic.org/export/{}".format(digest)
    
    payload = {'graph_uri': graph_uri, 'data': graph_ttl}
    response = requests.post(PROVOVIZ_SERVICE, data=payload)
    
    html_filename = '{}_provoviz.html'.format(digest)
    html_file = open(html_filename,'w')
    html_file.write(response.text)
    html_file.close()
    
    iframe = "<iframe width='100%' height='450px' src='http://localhost:8000/{}'></iframe>".format(html_filename)
    
    
    return HTML(iframe)
    
    