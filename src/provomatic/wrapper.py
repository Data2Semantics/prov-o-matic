import hashlib
import inspect
from ast import *
from builder import ProvBuilder
import numpy as np




PROV_WRAPPER_AST_CALL = "Name('prov', Load())"
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
    # print '---\nREPLACE: function name "{}"\n---'.format(f.__name__)
    
    ## If we're dealing with a 'ufunc' (i.e. numpy universal function)
    if isinstance(f,np.ufunc):
        # print "ufunc", f, args, kwargs
        inputs = {'x{}'.format(n) : args[n-1] for n in range(1,f.nin+1) }
        # print inputs
        source = f.__doc__
    ## If we're dealing with a 'classobj' (i.e. an expression that instantiates a object of a class, or something... whatever.)
    elif inspect.isclass(f):
        print "func", f, args, kwargs
        
        inputs = inspect.getcallargs(f.__init__, f, *args, **kwargs)
        # print inputs
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
    
    
class CodeVisitor(NodeTransformer):
    """Adds a PROV decorator to all function definitions"""
    
    def __init__(self, notebookwatcher):
        self.nw = notebookwatcher
        self.functions = set()


    # ====
    # No longer used as we dynamically wrap *any* function call, regardless of whether it is imported or defined.
    # TODO: Rewrite this to a function creation activity (now that would be cool)
    # ====
    
    # def visit_FunctionDef(self, node):
    #     try :
    #         decorators = [dump(e,annotate_fields=False) for e in node.decorator_list]
    #     except Exception as e:
    #         # print e
    #         
    #     try :
    #         if not(PROV_WRAPPER_AST_CALL in decorators):
    #             # # print "Adding PROV Wrapper to {}".format(node.name)
    #             prov_decorator = eval(PROV_WRAPPER_AST_CALL)
    #             node.decorator_list.append(prov_decorator)
    #     except Exception as e:
    #         # print e
    #     
    #     try :
    #         self.generic_visit(node)
    #     except Exception as e:
    #         # print e
    #     return node
        
    def visit_Name(self, node):
        self.generic_visit(node)
        # print dump(node)
        self.nw.register_usage(node.id)
        return node
    
    # def visit_Assign(self, node):
    #     
    #     if isinstance(node.value,Call):
    #         try :
    #             # print "===\nAssignment with Function Call"
    #             # print "Old: ", dump(node)
    #         
    #         
    #             # Replace Store() context with Load() context
    #             # This is easiest with a string replace, but potentially very very very buggy
    #             targets = []
    #             for t in node.targets:
    #                 new_t = eval(dump(t, annotate_fields = False).replace('Store()','Load()'))
    #                 targets.append(new_t)
    # 
    #             # print "Targets: ", [dump(t) for t in targets]
    #             prov_target_kw = keyword('prov_targets',targets)
    #             
    #             if node.value.keywords :
    #                 new_keywords = node.value.keywords.append(prov_target_kw)  
    #             else :
    #                 new_keywords = [prov_target_kw]
    #             
    #             
    #                 
    #             # For testing purposes only:
    #             # new_keywords = node.value.keywords
    #             
    #             
    #             # print "New KW: ", [dump(k) for k in new_keywords]
    #             new_call = Call(node.value.func,node.value.args,new_keywords,node.value.starargs,node.value.kwargs)
    #             
    #             # print "New Call: ", dump(new_call)
    #             new_assignment = Assign(node.targets,new_call)
    #             
    #             # print "New: ", dump(new_assignment)
    # 
    #             fix_missing_locations(new_assignment)
    #             self.generic_visit(new_assignment)
    #             fix_missing_locations(new_assignment)
    #             copy_location(new_assignment,node)
    #             fix_missing_locations(new_assignment)
    #             # print "==="            
    #             
    # 
    #             return new_assignment
    #         except:
    #             # print "Whoops"
    #             # print e
    #             # print "==="
    #             self.generic_visit(node)
    #             
    #             return node
    #     else:
    #         # print "==="
    #         self.generic_visit(node)
    #         fix_missing_locations(node)
    #         return node
    
    def visit_Attribute(self, node):
        self.generic_visit(node)
        
        if isinstance(node.value,Name):
            # print node.value.id, node.attr
            self.nw.register_usage(node.value.id + '.' + node.attr)
            
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        fix_missing_locations(node)
        #self.nw.register_usage(node)

        # print "===\nCall\nOld: ", dump(node)
        
        if isinstance(node.func,Name) :
            func_id = node.func.id
        elif isinstance(node.func,Attribute) and isinstance(node.func.value,Call):
            func_id = node.func.value.func.id
        elif isinstance(node.func,Attribute) and isinstance(node.func.value,Name):
            func_id = node.func.value.id
        else :
            # print "Unknown function type"
            # print "==="
            return node
        
        if func_id == 'replace':
            # print "Skipping {}, already replaced".format(dump(node.func))
            # print "==="
            return node

            
        # print "Not skipping"
        
        try :
            new_args = [node.func]
            new_args.extend(node.args)
            # print "New Args:", [dump(a) for a in new_args]
            new_call = Call(Name('replace',Load()),new_args,node.keywords,node.starargs,node.kwargs)
            copy_location(new_call,node)
            fix_missing_locations(new_call)
            
            # print "New: ", dump(new_call)
            
        except Exception as e:
            # print "Whoops!"
            # print e
            return node
            
        # print "==="
        return new_call

    def visit_Module(self, node):
        self.generic_visit(node)
        fix_missing_locations(node)
        return node
        
    # def visit_Module(self,node):
    #     self.functions=set()
    #     # print dump(node)
    #     self.generic_visit(node)
    #     
    #     body = node.body
    #     for f in self.functions:
    #         if f == 'prov' or 'view_prov':
    #             # print "Already wrapped or in exclusion list"
    #         else :
    #             # print "Inserting prov wrapper"
    #             body.insert(0,parse("{} = prov({})".format(f,f)))
    #     
    #     fix_missing_locations(node)
    #     return node
            
        

    
        
        
# class CodeVisitor2(NodeTransformer):
#     def visit_Module(self, node):
#         # print dump(node)
#         
#         self.functions = []
#         self.generic_visit(node)
#         
#         for f in self.functions :
#             # print ast.dump(f)
#         
#         
#     def visit_Call(self, node):
#         self.functions.append(node)
# 
#         return node