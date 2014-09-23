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
    
def replace(f, output_names, *args, **kwargs):
    """Provenance-enabled replacement for arbitrary functions"""
    
    # Inputs is a dictionary of argument names and values
    # Outputs is whatever the wrapped function returns
    # Source is the source code of the function, or its docstring.
    
    
    ## If we're dealing with a 'ufunc' (i.e. numpy universal function)
    if isinstance(f,np.ufunc):
        inputs = {'x{}'.format(n) : args[n-1] for n in range(1,f.nin+1) if (args[n-1] != None)}
        source = f.__doc__
        
    ## If we're dealing with a 'wrapper_descriptor' (i.e. a wrapper around a C-function) we cannot retrieve the argument names
    elif isinstance(f,types.TypeType):
        inputs = {'x{}'.format(n) : args[n-1] for n in range(1,len(args)+1) if (args[n-1] != None)}
        source = f.__doc__
        
    ## If we're dealing with a 'classobj' (i.e. an expression that instantiates a object of a class, or something... whatever.)
    elif inspect.isclass(f):
        inputs = inspect.getcallargs(f.__init__, f, *args, **kwargs)
        # Only use those inputs that have a value
        inputs = {k:v for k,v in inputs.items() if (v != None)}
        source = inspect.getsource(f)
        
    ## If we're dealing with a builtin function
    elif isinstance(f,types.BuiltinFunctionType):
        inputs = {}
        source = f.__name__
        
    # If we're dealing with the 'get_ipython' function, we need to take some extra care, otherwise we introduce a cycle in the provenance graph.
    elif f.__name__ == 'get_ipython':
        inputs = {}
        source = inspect.getsource(f)
        
    ## If we're dealing with any other function, we just get all args and kwargs as inputs as a dictionary.
    else :
        inputs = inspect.getcallargs(f, *args, **kwargs)
        # Only use those inputs that have a value
        inputs = {k:v for k,v in inputs.items() if (v != None)}
        source = inspect.getsource(f)
    
    outputs = f(*args, **kwargs)
    
    pb = ProvBuilder()
    
    pb.add_activity(f.__name__, source, inputs, outputs, output_names=output_names)
    
    replace.prov = pb.get_graph()
    
    # prov_wrapper.prov_ttl = pb.get_graph().serialize(format='turtle')
    
    return outputs    
    
    
