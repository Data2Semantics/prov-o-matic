from watcher import NotebookWatcher, CodeVisitor
from wrapper import prov, replace
from builder import get_dataset, save_prov, clear_dataset
from viewer import Viewer

from ducktape import Ducktape







        







def load_ipython_extension(ip):
    # Push the prov and replace wrapper functions
    ip.push('prov')
    ip.push('replace')
    
    # Push the save_prov function (for saving the generated provenance trace to a file)    
    ip.push('save_prov')
    
    # Clear the provenance graph
    # clear_dataset()
    
    ## Initialize the PROV-O-Viz adapter
    viewer = Viewer()
    set_provoviz_url = viewer.set_provoviz_url
    view_prov = viewer.view_prov
    # Push the functions to the IPython Notebook
    ip.push('set_provoviz_url')
    ip.push('view_prov')
    
    ## Initialize the Ducktape loader
    ducktape = Ducktape(ip)
    load_ducktape = ducktape.load
    ip.push('load_ducktape')
    
    ## Initialize the notebookwatcher and code visitor.
    nw = NotebookWatcher(ip)
    cv = CodeVisitor(nw)
    
    ip.events.register('pre_execute', nw.pre_execute)
    ip.events.register('post_execute', nw.post_execute)
    ip.ast_transformers.append(cv)
    
    

