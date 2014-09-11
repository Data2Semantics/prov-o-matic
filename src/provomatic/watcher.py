from IPython.core.history import HistoryAccessor
from IPython.core.ultratb import VerboseTB

import numpy
import inspect
import hashlib
import collections

from ast import *

class NotebookWatcher(object):
    """The NotebookWatcher listens to execution events in the IPython Notebook, and generates the relevant provenance based on an analysis of the code being executed."""
    environment = {}
    used = set()
    
    
    def __init__(self, ip):
        """Takes an InteractiveShell instance as input."""
        self.shell = ip
        # The HistoryAccessor allows us to... eh, access the history of the Python interpreter.
        self.hist = HistoryAccessor()
        self.last_x = None

    def pre_execute(self):
        """Before the code is executed, we reset the list of variables/functions etc. 'used' (as we don't know them yet)."""
        # Reset the used list
        self.used = set()


    def post_execute(self):
        """This will build the provenance for the execution of the code block in the IPython Notebook"""
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
            # print "Checking wether " + node + " is a variable or a function"
            try :
                evaluated_node = self.shell.ev(node)
                # print "> Could evaluate " + node 
                if node in self.environment and not callable(evaluated_node) :
                    # print ">> " + node + " is in environment and not callable"
                    # # print "Used global variable {}".format(node)
                    # Set the input of the node to the value that it had prior to executing the code (if available)
                    if node in self.environment:
                        ## print "Global variable existed before, adding to inputs"
                        inputs[node] = self.environment[node]
                    # Otherwise, we do nothing, since the variable may have been used, but was first introduced in the code.
                    else :
                        # # print "Global variable was introduced here, ignoring"
                        pass
               
                elif callable(evaluated_node):
                    # print ">> Used function {}".format(node)
                    try :
                        dependencies[node] = inspect.getsource(evaluated_node)
                    except Exception as e:
                        # print e
                        dependencies[node] = unicode(evaluated_node)
            except :
                ## print "Used local {} variable or function".format(node)
                # print "> Could not evaluate " + node
                if node in self.environment :
                    # print ">> Node is in environment"
                    evaluated_node = self.environment[node]
                    
                    if not callable(evaluated_node) :
                        # print ">>> Node is a variable"
                        inputs[node] = evaluated_node
                    else :
                        # print ">>> Node is a function"
                        dependencies[node] = inspect.getsource(evaluated_node)
                else :
                    pass
                    # print ">> Node was introduced here"
                
        
        for k,v in self.shell.user_ns.items():
            # Ignore any standard IPython/Python variables in the user namespace
            if k.startswith('_') or k in ['In','Out','exit','quit','get_ipython'] :
                pass
            # For all other variables, see whether they were changed, and add them to the outputs
            else :
                
                    
                if (k in self.environment and not numpy.array_equal(v,self.environment[k])) or (not k in self.environment):
                    # # print "{} changed or was added".format(k)
                    
                    # If the object is not a function, we'll use the value as output value.
                    if not callable(v):
                        outputs[k] = v
                    # If it is a PROV wrapped function, we'll retrieve its source and use it as output value.
                    elif callable(v) and hasattr(v,'source') :
                        outputs[k] = v.source
                    # Otherwise (this shouldn't be the case, but anyway) we'll use its source directly.
                    elif callable(v) :
                        try :
                            outputs[k] = inspect.getsource(v)
                        except:
                            outputs[k] = v
                    # Finally, this is probably not were we'll end up anyway... we'll do nothing 
                    else :
                        pass
                    
                    self.environment[k] = v
        
        # print dependencies.keys()
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
        """This function is called by a CodeVisitor instance whenever a node (i.e. a variable/function name appears in the code)"""
        self.used.add(node)




PROV_WRAPPER_AST_CALL = "Name('prov', Load())"


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