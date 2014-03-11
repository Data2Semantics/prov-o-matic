from pprint import pprint
from IPython.core.history import HistoryAccessor
from IPython.core.ultratb import VerboseTB
from ast import *
from functools import wraps
import inspect
import hashlib
import collections
import datetime

from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS

PROV = Namespace('http://www.w3.org/ns/prov#')
PROVOMATIC = Namespace('http://provomatic.org/resource/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')

g = Graph()

g.bind('prov',PROV)
g.bind('provomatic',PROVOMATIC)
g.bind('skos',SKOS)

def add_activity(name, digest, description, inputs, outputs):
    """Adds an activity to the graph. Inputs should be a dictionary of inputs & values, outputs a list or tuple of just values"""
    plan_uri = PROVOMATIC[digest]
    
    g.add((plan_uri, RDF.type, RDFS['Class']))
    g.add((plan_uri, RDF.type, PROVOMATIC['Method']))
    g.add((plan_uri, RDFS.label, Literal(name)))
    
    activity_uri = PROVOMATIC[digest + "/" + now()]
    
    g.add((activity_uri,RDF.type,PROV['Activity']))
    g.add((activity_uri,RDFS.label,Literal(name)))
    g.add((activity_uri,RDF.type,plan_uri))
    
    for iname, value in inputs.items():
        value, vdigest = get_value(value)
            
        input_uri = add_entity(iname, vdigest, value)
        
        g.add((activity_uri, PROV['used'], input_uri))
        
    if isinstance(outputs, tuple) :
        count = 0
        for value in outputs:
            count += 1
            
            value, vdigest = get_value(value)
        
            output_uri = add_entity("{} output {}".format(name,count),vdigest,value)
            
            g.add((output_uri, PROV['wasGeneratedBy'], activity_uri))
    else :
        value, vdigest = get_value(outputs)
        
        output_uri = add_entity("{} output".format(name), vdigest, value)
        
        g.add((output_uri, PROV['wasGeneratedBy'], activity_uri))
        
    return activity_uri

def add_entity(name, digest, description):
    entity_uri = PROVOMATIC[digest]
    
    g.add((entity_uri,RDF.type,PROV['Entity']))
    g.add((entity_uri,RDFS.label,Literal(name)))
    g.add((entity_uri,SKOS['note'],Literal(description)))
    
    return entity_uri
    
def get_value(io):
    """We'll just use the __unicode__ representation as source for the hash digest"""
    value = unicode(io)
    vdigest = hashlib.md5(unicode(value)).hexdigest()

    if len(value) > 50:
        value = value[:24] + u"..." + value[-25:]
    
    return value, vdigest

def now():
    return datetime.datetime.now().isoformat()


PROV_WRAPPER_AST_CALL = "Name('prov', Load())"
    
def prov(f):
    """Decorator that generates a wrapper function"""
    def prov_wrapper(*args, **kwargs):
        """Provenance wrapper for arbitrary functions"""
        print 'function name "{}"'.format(f.__name__)
        prov_wrapper.source = inspect.getsource(f)
        prov_wrapper.digest = hashlib.md5(inspect.getsource(f)).hexdigest()
        
        inputs = inspect.getcallargs(f, *args, **kwargs)
        
        outputs = f(*args, **kwargs)
        
        add_activity(f.__name__, prov_wrapper.digest, prov_wrapper.source, inputs, outputs)
        
        print "Done"
        return outputs

    return prov_wrapper



class NotebookWatcher(object):
    
    environment = {}
    used = set()
    def __init__(self, ip):
        self.shell = ip
        self.hist = HistoryAccessor()
        self.last_x = None

    def pre_execute(self):
        print "Pre"
        self.used = set()
        # print self.hist_to_string(1)
        self.last_x = self.shell.user_ns.get('x', None)

    def post_execute(self):
        print "Post"
        
        description = self.hist_to_string(1) 
        position = len(get_ipython().user_ns.get('_ih'))
        
        for k,v in self.shell.user_ns.items():
            if k.startswith('_') or k in ['In','Out','exit','quit','get_ipython'] :
                pass
            else :
                print k, v
                if k in self.environment and v != self.environment[k]:
                    print "{} changed!".format(k)
                    self.environment[k] = v
                elif not k in self.environment :
                    print "Adding {} to environment".format(k)
                    self.environment[k] = v
        
        for node in self.used:    
            if node in self.environment:
                print "Used global {}".format(node)
            else :
                print "Used local {}".format(node)

            
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

        
class FunctionWrapper(NodeTransformer):
    """Adds a PROV decorator to all function definitions"""
    
    def __init__(self, notebookwatcher):
        self.nw = notebookwatcher
    
    def visit_FunctionDef(self, node):

        try :
            decorators = [dump(e,annotate_fields=False) for e in node.decorator_list]
        except Exception as e:
            print e
            
        try :
            if not(PROV_WRAPPER_AST_CALL in decorators):
                print "Adding PROV Wrapper to {}".format(node.name)
                prov_decorator = eval(PROV_WRAPPER_AST_CALL)
                node.decorator_list.append(prov_decorator)
        except Exception as e:
            print e
        
        try :
            self.generic_visit(node)
        except Exception as e:
            print e
        return node
        
    def visit_Name(self, node):
        self.generic_visit(node)
        self.nw.register_usage(node.id)
        return node




def load_ipython_extension(ip):
    nw = NotebookWatcher(ip)
    fw = FunctionWrapper(nw)
    ip.events.register('pre_execute', nw.pre_execute)
    ip.events.register('post_execute', nw.post_execute)
    ip.ast_transformers.append(fw)
