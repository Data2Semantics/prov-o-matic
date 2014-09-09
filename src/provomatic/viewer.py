from builder import get_graph
from rdflib import Graph

from IPython.display import HTML
import hashlib
import requests
import os 

#_PROVOVIZ_SERVICE = "http://semweb.cs.vu.nl/provoviz/service"
#_PROVOVIZ_SERVICE = "http://provoviz.org/service"
_PROVOVIZ_SERVICE = "http://localhost:5000/service"

def set_provoviz_url(url='http://localhost:5000/service'):
    _PROVOVIZ_SERVICE = url
    return "PROV-O-Viz service URL now set to '{}'".format(_PROVOVIZ_SERVICE)

def view_prov():
    graph = get_graph()
    
    graph_ttl = graph.serialize(format='turtle')
    
    digest = hashlib.md5(graph_ttl).hexdigest()
    
    graph_uri = "http://provomatic.org/export/{}".format(digest)
    
    payload = {'graph_uri': graph_uri, 'data': graph_ttl}
    print "Posting to {}".format(_PROVOVIZ_SERVICE)
    response = requests.post(_PROVOVIZ_SERVICE, data=payload)
    
    html_filename = '{}_provoviz.html'.format(digest)
    html_file = open(html_filename,'w')
    html_file.write(response.text)
    html_file.close()
    
    iframe = "<iframe width='100%' height='450px' src='http://localhost:8000/{}'></iframe>".format(html_filename)
    
    
    return HTML(iframe)
    
    