from provomatic.watcher import NotebookWatcher, CodeVisitor
from provomatic.wrapper import prov, replace
from provomatic.builder import get_dataset, save_prov, clear_dataset, add_prov, revive, list_entities, list_activities

ip = get_ipython()

## Initialize the notebookwatcher and code visitor.
nw = NotebookWatcher(ip)
cv = CodeVisitor(nw)

ip.events.register('pre_execute', nw.pre_execute)
ip.events.register('post_execute', nw.post_execute)
ip.ast_transformers.append(cv)



def add(x,y):
    return x+y

x = 2
y = 3    
    
z = add(x,y)

z = add(z,5)

save_prov('terminal-prov.ttl')