from builder import get_graph
from rdflib import Graph

from IPython.display import HTML
import hashlib
import requests
import os 

#PROVOVIZ_SERVICE = "http://semweb.cs.vu.nl/provoviz/service"
PROVOVIZ_SERVICE = "http://provoviz.org/service"

def set_provoviz_url(url='http://localhost:5000/service'):
    PROVOVIZ_SERVICE = url
    return "PROV-O-Viz service URL now set to '{}'".format(PROVOVIZ_SERVICE)
    
    return PROVOVIZ_SERVICE

def view_prov():
    graph = get_graph()
    
    graph_ttl = graph.serialize(format='turtle')
    
    digest = hashlib.md5(graph_ttl).hexdigest()
    
    graph_uri = "http://provomatic.org/export/{}".format(digest)
    
    payload = {'graph_uri': graph_uri, 'data': graph_ttl}
    print "Posting to {}".format(PROVOVIZ_SERVICE)
    response = requests.post(PROVOVIZ_SERVICE, data=payload)
    
    html_filename = '{}_provoviz.html'.format(digest)
    html_file = open(html_filename,'w')
    html_file.write(response.text)
    html_file.close()
    
    iframe = "<iframe width='100%' height='450px' src='http://localhost:8000/{}'></iframe>".format(html_filename)
    
    
    return HTML(iframe)
    
    