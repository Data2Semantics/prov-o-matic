import hashlib
import inspect
import numpy as np
import types

from builder import ProvBuilder





def prov(f):
    """Decorator that generates a wrapper function"""
    def prov_wrapper(*args, **kwargs):
        """Provenance wrapper for arbitrary functions"""
        # print '---\nWRAPPER: function name "{}"\n---'.format(f.__name__)
        
        inputs = inspect.getcallargs(f, *args, **kwargs)
        
        outputs = f(*args, **kwargs)
        
        pb = ProvBuilder()
        
        pb.add_activity(f.__name__, prov_wrapper.source, inputs, outputs)
        
        prov_wrapper.prov = pb.get_graph()
        # prov_wrapper.prov_ttl = pb.get_graph().serialize(format='turtle')
        
        return outputs

    prov_wrapper.source = inspect.getsource(f)
    return prov_wrapper
    
def replace(f, *args, **kwargs):
    """Provenance-enabled replacement for arbitrary functions"""
    print '---\nREPLACE: function name "{}"\n---'.format(f.__name__)
    

    
    ## If we're dealing with a 'ufunc' (i.e. numpy universal function)
    if isinstance(f,np.ufunc):
        # print "ufunc", f, args, kwargs
        inputs = {'x{}'.format(n) : args[n-1] for n in range(1,f.nin+1) }
        # print inputs
        source = f.__doc__
    ## If we're deling with a 'wrapper_descriptor' (i.e. a wrapper around a C-function)
    elif isinstance(f,types.TypeType):
        print "type", f, args, kwargs
        inputs = {'x{}'.format(n) : args[n-1] for n in range(1,len(args)+1) }
        source = f.__name__
    ## If we're dealing with a 'classobj' (i.e. an expression that instantiates a object of a class, or something... whatever.)
    elif inspect.isclass(f):
        print "func", f, args, kwargs
        
        inputs = inspect.getcallargs(f.__init__, f, *args, **kwargs)
        # print inputs
        source = inspect.getsource(f)
    ## If we're dealing with a builtin function
    elif isinstance(f,types.BuiltinFunctionType):
        print "bultin_function_or_method", f, args, kwargs
        inputs = {}
        source = f.__name__
    elif f.__name__ == 'get_ipython':
        print "get_ipython() takes no input: otherwise we'll end up with a cycle"
        inputs = {}
        source = inspect.getsource(f)
        
    ## If we're dealing with any other function
    else :
        # print "func", f, args, kwargs
        
        inputs = inspect.getcallargs(f, *args, **kwargs)
        # print inputs
        source = inspect.getsource(f)
    
    outputs = f(*args, **kwargs)
    
    pb = ProvBuilder()
    
    pb.add_activity(f.__name__, source, inputs, outputs)
    
    replace.prov = pb.get_graph()
    
    # prov_wrapper.prov_ttl = pb.get_graph().serialize(format='turtle')
    
    return outputs    
    
    
