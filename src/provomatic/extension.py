
from IPython.core.history import HistoryAccessor
from IPython.core.ultratb import VerboseTB

import inspect
import hashlib
import collections

from wrapper import prov, CodeVisitor
from builder import ProvBuilder, get_dataset

from rdflib import Graph





class NotebookWatcher(object):
    
    environment = {}
    used = set()
    
    
    def __init__(self, ip):
        self.shell = ip
        self.hist = HistoryAccessor()
        self.last_x = None

    def pre_execute(self):
        # Reset the used list
        self.used = set()


    def post_execute(self):
        # Initialize a provenance builder
        pb = ProvBuilder()
        
        # Get the description (i.e. the code) from the code we just executed
        description = self.hist_to_string(1) 
        position = len(get_ipython().user_ns.get('_ih')) -1
        name = "In [{}]".format(position)
        
        # Initialize inputs, outputs and dependencies dictionaries for activity generator in ProvBuilder
        inputs = {}
        outputs = {}
        dependencies = {}
        
        # For all nodes (variables/functions) that were recognized by the CodeVisitor
        # If the node is a *global* variable, add it to the inputs
        # If the node is a *function* name, add it to the dependencies
        for node in self.used:    
            try :
                evaluated_node = eval(node)
            
                if node in self.environment and not callable(evaluated_node) :
                    # print "Used global variable {}".format(node)
                    # Set the input of the node to the value that it had prior to executing the code (if available)
                    if node in self.environment:
                        #print "Global variable existed before, adding to inputs"
                        inputs[node] = self.environment[node]
                    # Otherwise, we do nothing, since the variable may have been used, but was first introduced in the code.
                    else :
                        #print "Global variable was introduced here, ignoring"
                        pass
               
                elif callable(evaluated_node):
                    #print "Used function {}".format(node)
                    dependencies[node] = inspect.getsource(evaluated_node)
            except :
                #print "Used local {} variable or function".format(node)
                #print "Value not accessible"
                if node in self.environment :
                    evaluated_node = self.environment[node]
                    
                    if not callable(evaluated_node) :
                        inputs[node] = evaluated_node
                    else :
                        dependencies[node] = inspect.getsource(evaluated_node)
                
        
        for k,v in self.shell.user_ns.items():
            # Ignore any standard IPython/Python variables in the user namespace
            if k.startswith('_') or k in ['In','Out','exit','quit','get_ipython'] :
                pass
            # For all other variables, see whether they were changed, and add them to the outputs
            else :
                if (k in self.environment and v != self.environment[k]) or (not k in self.environment):
                    # print "{} changed or was added".format(k)
                    
                    # If the object is not a function, we'll use the value as output value.
                    if not callable(v):
                        outputs[k] = v
                    # If it is a PROV wrapped function, we'll retrieve its source and use it as output value.
                    elif callable(v) and hasattr(v,'source') :
                        outputs[k] = v.source
                    # Otherwise (this shouldn't be the case, but anyway) we'll use its source directly.
                    elif callable(v) :
                        outputs[k] = inspect.getsource(v)
                    # Finally, this is probably not were we'll end up anyway... we'll do nothing 
                    else :
                        pass
                    
                    self.environment[k] = v
        
        pb.add_activity(name, description, inputs, outputs, dependencies, True)
        


            
    def hist_to_string(self, n=1):
        hist = self.shell.user_ns.get('_ih',[])
        out = ""
        if len(hist) > n :
            start = len(hist) - n
        else :
            start = 0
        for idx,val in enumerate(hist[start:]) :
            out += "{}: \n{}\n".format(idx+start,val)
            
        return out

    def register_usage(self, node):
        self.used.add(node)

        


def load_ipython_extension(ip):
    nw = NotebookWatcher(ip)
    cv = CodeVisitor(nw)
    ip.events.register('pre_execute', nw.pre_execute)
    ip.events.register('post_execute', nw.post_execute)
    ip.ast_transformers.append(cv)