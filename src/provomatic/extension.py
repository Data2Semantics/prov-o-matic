from watcher import NotebookWatcher, CodeVisitor
from wrapper import prov, replace
from builder import get_dataset, save_prov, clear_dataset, add_prov, revive, list_entities, list_activities
from viewer import Viewer

from ducktape import Ducktape

import logging
import os

log = logging.getLogger('provomatic.extension')
log.setLevel(logging.WARNING)










def load_ipython_extension(ip):
    log.debug("Loading PROV-O-Matic extension")
    # Push the prov and replace wrapper functions
    ip.push('prov')
    ip.push('replace')
    
    # Push the save_prov function (for saving the generated provenance trace to a file)    
    ip.push('save_prov')
    # Push the add_prov function (for adding provenance from external files)
    ip.push('add_prov')
    # Push the revive function (for binding a value from an inported provenance graph to a new variable)
    ip.push('revive')
    ip.push('list_entities')
    ip.push('list_activities')

    
    ## Initialize the PROV-O-Viz adapter
    viewer = Viewer()
    view_prov = viewer.view_prov
    
    set_provoviz_url = viewer.set_provoviz_url
    view_prov_service = viewer.view_prov_service
    # Push the PROV-O-Viz functions to the IPython Notebook
    ip.push('view_prov')
    
    ip.push('set_provoviz_url')
    ip.push('view_prov_service')
    
    ## Initialize the Ducktape loader
    ducktape = Ducktape(ip)
    load_ducktape = ducktape.load
    ip.push('load_ducktape')
    
    # Clear the provenance graph
    clear_dataset()
    try :
        add_prov('http://www.w3.org/ns/prov#',url='http://localhost:8000/datafiles/prov-o.ttl')
    except :
        curwd = os.getcwd()
        provopath = os.path.join(curwd,'datafiles/prov-o.ttl')
        log.warning('Could not load PROV schema from URL, attempting to load from {}'.format(provopath))

        add_prov('http://www.w3.org/ns/prov#',url='file://{}'.format(provopath))
    
    ## Initialize the notebookwatcher and code visitor.
    nw = NotebookWatcher(ip)
    cv = CodeVisitor(nw)
    
    ip.events.register('pre_execute', nw.pre_execute)
    ip.events.register('post_execute', nw.post_execute)
    ip.ast_transformers.append(cv)
    
    
    

