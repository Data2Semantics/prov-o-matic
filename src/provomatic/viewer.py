from builder import get_graph, get_dataset, list_entities, list_activities
from rdflib import Graph, ConjunctiveGraph

from IPython.display import HTML
import hashlib
import requests
import os 

import SimpleHTTPServer
import SocketServer
import threading
import json
import logging

from provoviz.views import generate_graphs
from jinja2 import Environment, PackageLoader

log = logging.getLogger('provomatic.viewer')
log.setLevel(logging.INFO)


class Viewer(object):
    """Adapter for the PROV-O-Viz service"""
    
    #_PROVOVIZ_SERVICE = "http://semweb.cs.vu.nl/provoviz/service"
    #_PROVOVIZ_SERVICE = "http://provoviz.org/service"
    _PROVOVIZ_SERVICE = "http://localhost:5000/service"

    _PORT = 8000

    def __init__(self, provoviz_service_url=_PROVOVIZ_SERVICE, http_port=_PORT):
        self._PORT = http_port
        self.set_provoviz_url(provoviz_service_url)
        self.start_http_server()
        
        
        
    def start_http_server(self):
        """Starts a simple HTTP server in a separate thread.\n
        
        The PROV-O-Viz service returns a self-contained HTML file, which is then served from this HTTP\n
        server to the IPython notebook via an IFrame.
        """
        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

        try :
            httpd = SocketServer.TCPServer(("", self._PORT), Handler)

            httpd_thread = threading.Thread(target=httpd.serve_forever)
            httpd_thread.setDaemon(True)
            httpd_thread.start()
            
            log.info("HTTP Server running at http://localhost:{}".format(self._PORT))
        except Exception as e:
            log.error("HTTP Server failed to start (is it already running?)")
            log.debug(e)
            
        if not os.path.exists('www'):
            log.debug("Created 'www' directory for storing generated HTML files")
            os.makedirs('www')
            

    def view_prov(self, name = None):
        """Generate the provenance graph locally using a submodule version of PROV-O-Viz"""
        env = Environment(loader=PackageLoader('provomatic','templates'))
        template = env.get_template('service_response_local.html')
        
        
        if name :
            entities = list_entities()
            activities = list_activities()
        
        
            if name in entities:
                resources = [{'id': e['uri'], 'text': e['name']} for e in entities[name]]
            elif name in activities :
                resources = [{'id': a['uri'], 'text': a['name']} for a in activities[name]]
            else :
                resources = None
        else :
            resource = None
            
        log.debug(resources)
        
        dataset = get_dataset()
        data_hash = dataset.md5_term_hash()
        
        response = generate_graphs(ConjunctiveGraph(dataset.store), resources=resources)
        
        json_response = json.dumps(response)
        
        visualization_html = template.render(response=json_response, data_hash=data_hash)
        
        html = self.generate_iframe(visualization_html, data_hash)
        
        return HTML(html)





    def set_provoviz_url(self, provoviz_service_url='http://localhost:5000/service'):
        """Sets the URL to which the provenance trace should be posted to obtain the visualization"""
        
        self._PROVOVIZ_SERVICE = provoviz_service_url
        return "PROV-O-Viz service URL now set to '{}'".format(self._PROVOVIZ_SERVICE)

    def view_prov_service(self):
        """Posts the provenance graph to the PROV-O-Viz service URL, and returns an HTML object with an IFrame to the HTML page returned"""
        graph = get_graph()
    
        graph_ttl = graph.serialize(format='turtle')
    
        digest = hashlib.md5(graph_ttl).hexdigest()
    
        graph_uri = "http://provomatic.org/export/{}".format(digest)
    
        payload = {'graph_uri': graph_uri, 'data': graph_ttl}
        log.debug("Posting to {}".format(self._PROVOVIZ_SERVICE))
        response = requests.post(self._PROVOVIZ_SERVICE, data=payload)
    
        if response.status_code == 200 :
            html = self.generate_iframe(response.text, digest)
        else :
            html = """<p><strong>Error</strong> communicating with PROV-O-Viz service at {}, response status {}.<p>""".format(self._PROVOVIZ_SERVICE,response.status_code)
    
    
        return HTML(html)
    
    def generate_iframe(self, visualization_html, digest):
        html_filename = 'www/{}_provoviz.html'.format(digest)
        html_file = open(html_filename,'w')
        html_file.write(visualization_html)
        html_file.close()

        html = """<iframe width='100%' height='450px' src='http://localhost:8000/{}'></iframe>""".format(html_filename)
        
        return html