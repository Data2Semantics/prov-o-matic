import hashlib
import inspect
from ast import *
from builder import ProvBuilder


PROV_WRAPPER_AST_CALL = "Name('prov', Load())"
def prov(f):
    """Decorator that generates a wrapper function"""
    def prov_wrapper(*args, **kwargs):
        """Provenance wrapper for arbitrary functions"""
        # print 'function name "{}"'.format(f.__name__)
        
        inputs = inspect.getcallargs(f, *args, **kwargs)
        
        outputs = f(*args, **kwargs)
        
        pb = ProvBuilder()
        
        pb.add_activity(f.__name__, prov_wrapper.source, inputs, outputs)
        
        prov_wrapper.prov = pb.get_graph()
        # prov_wrapper.prov_ttl = pb.get_graph().serialize(format='turtle')
        
        return outputs

    prov_wrapper.source = inspect.getsource(f)
    return prov_wrapper
    
    
class CodeVisitor(NodeTransformer):
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
                # print "Adding PROV Wrapper to {}".format(node.name)
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
        
    def visit_Call(self, node):
        self.generic_visit(node)
        # print dump(node,annotate_fields=False)
        return node