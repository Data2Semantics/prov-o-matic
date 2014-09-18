from IPython.core.history import HistoryAccessor
from IPython.core.ultratb import VerboseTB

import numpy
import inspect
import hashlib
import collections

from ast import *

from builder import ProvBuilder


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
                # print "> Could evaluate {}".format(node) 
                if node in self.environment and not callable(evaluated_node) :
                    # print ">> {} is in environment and not callable (it is a variable)".format(node)
                    # # print "Used global variable {}".format(node)
                    # Set the input of the node to the value that it had prior to executing the code (if available)
                    if node in self.environment:
                        # print "Global variable existed before, adding to inputs"
                        inputs[node] = self.environment[node]
                    # Otherwise, we do nothing, since the variable may have been used, but was first introduced in the code.
                    else :
                        # print "Global variable was introduced here, not doing anything"
                        pass
               
                elif callable(evaluated_node):
                    # print ">> {} is a function, adding to dependencies.".format(node)
                    try :
                        dependencies[node] = inspect.getsource(evaluated_node)
                    except Exception as e:
                        # print e
                        dependencies[node] = unicode(evaluated_node)
                else :
                    # print ">> {} is not callable, and not in environment... it was a variable that was newly introduced here?".format(node)
                    pass
            except :
                ## print "Used local {} variable or function".format(node)
                # print "> Could not evaluate " + node
                if node in self.environment :
                    # print ">> Node is in environment, we'll use its evaluated value from the environment"
                    evaluated_node = self.environment[node]
                    
                    if not callable(evaluated_node) :
                        # print ">>> {} is a variable".format(node)
                        inputs[node] = evaluated_node
                    else :
                        # print ">>> {} is a function".format(node)
                        dependencies[node] = inspect.getsource(evaluated_node)
                else :
                    # print ">> {} was introduced here, not doing anything".format(node)
                    pass
                
        # We'll loop through all known entities in the user namespace.
        for k,v in self.shell.user_ns.items():
            # Ignore any standard IPython/Python variables in the user namespace
            # if k.startswith('_') or k in ['In','Out','exit','quit','get_ipython'] :
            #     print "'{}' skipped, because it is in ['In','Out','exit','quit','get_ipython'] or starts with '_'".format(k)
            #     pass
            
            # TEMPORARY: Test what happens if we don't exclude 'Out'
            if k.startswith('_') or k in ['In','exit','quit','get_ipython'] :
                # print "'{}' skipped, because it is in ['In','exit','quit','get_ipython'] or starts with '_'".format(k)
                pass
                
            # For all other variables, see whether they were changed, and add them to the outputs
            ## This compares the value of the variable with the value it had previously, or
            ## checks that the variable did not exist previously.  
            
            elif (k in self.environment and not (numpy.array_equal(v,self.environment[k]) or v == self.environment[k])) or (not k in self.environment) or k == 'Out':
                
                
                # print "{} changed or was added".format(k)
                # OLD: This performed the check now included in the elif statement. Removed because of the addition of "k = 'Out'" (we're capturing everythin posted to Out)
                # if k in self.environment and v == self.environment[k]:
                #     print "Problem with {}".format(k)
                
                # If the object is not a function, we'll use the value as output value.
                if not callable(v):
                    # print "{} is not a function, adding to outputs as value".format(k)
                    outputs[k] = v
                    
                    # Increase the tick of the variable with name 'k'
                    # self.tick(k)
                    
                # If it is a PROV wrapped function, we'll retrieve its source and use it as output value.
                elif callable(v) and hasattr(v,'source') :
                    # print "{} is a PROV wrapped function, its source is an output value".format(k)
                    outputs[k] = v.source
                # Otherwise (this shouldn't be the case, but anyway) we'll use its source directly.
                elif callable(v) :
                    # print "{} is callable, but not wrapped... we'll try to retrieve its source and add it as an output".format(k)
                    try :
                        outputs[k] = inspect.getsource(v)
                    except:
                        # print "could not get source of {}, just taking its value as an output".format(k)
                        outputs[k] = v
                # Finally, this is probably not were we'll end up anyway... we'll do nothing 
                else :
                    # print "Unexpected!"
                    pass
                
                # print "Just visited {}".format(k)
                self.environment[k] = v
            else :
                # print "'{}' skipped because it did not change.".format(k)
                pass
        
        # print dependencies.keys()
        pb.add_activity(name, description, inputs, outputs, dependencies, expand_output_dict=True)
        


            
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
        l = List()
        l.elts = []
        l.ctx = Load()
        self.targets = l
        
        self.nw = notebookwatcher
        self.functions = set()



    def visit_Name(self, node):
        self.generic_visit(node)
        # print dump(node)
        self.nw.register_usage(node.id)
        return node
    

    
    def visit_Attribute(self, node):
        self.generic_visit(node)
        
        if isinstance(node.value,Name):
            # print node.value.id, node.attr
            self.nw.register_usage(node.value.id + '.' + node.attr)
            
        return node


    def get_func_id(self, node):
        if isinstance(node.func,Name) :
            func_id = node.func.id
        elif isinstance(node.func,Attribute) and isinstance(node.func.value,Call):
            func_id = node.func.value.func.id
        elif isinstance(node.func,Attribute) and isinstance(node.func.value,Name):
            func_id = node.func.value.id
        else :
            return None
        
        return func_id

    def visit_Call(self, node):
        self.generic_visit(node)
        fix_missing_locations(node)
        #self.nw.register_usage(node)

        # print "> call"
        # print dump(node)
        
        func_id = self.get_func_id(node)
        
        if not func_id:
            # print "Unknown function type"
            # print "==="
            return node
        
        # print func_id
        if func_id == 'replace':
            print "Skipping {}, already replaced".format(dump(node.func))
            # print dump(node)
            # print "==="
            return node
            
        # print "Not skipping"
        
        try :
            new_args = [node.func]
            
            if self.targets:
                
                # print 'targets', dump(self.targets)
                ## Use the targets
                new_args.append(self.targets)
                ## And reset them, to avoid propagation of target variable names to nested function calls.
                l = List()
                l.elts = []
                l.ctx = Load()
                self.targets = l
            else :
                # print "no targets"
                l = Lists()
                l.elts = []
                l.ctx = Load()
                new_args.append(l)
            
            new_args.extend(node.args)
            # print "New Args:", [dump(a) for a in new_args]
            new_call = Call(Name('replace',Load()),new_args,node.keywords,node.starargs,node.kwargs)
            copy_location(new_call,node)
            fix_missing_locations(new_call)
            
            # print "New"
            # print dump(new_call)
            
        except Exception as e:
            print "Whoops!"
            print dump(node)
            print e
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
    
    def visit_AugAssign(self,node):
        # TODO Capture augmentation assignments
        # print "> augassign"
        # print dump(node)
        return self.generic_visit(node)
        
    def visit_Assign(self, node):
        # TODO Capture the assignment itself
        # This just captures the outputs expected from a function
        
        # print "> assign"
        # print dump(node)
        # print "Resetting targets"
        l = List()
        l.elts = []
        l.ctx = Load()
        self.targets = l
        self.function = None
        
        if isinstance(node.value,Call):
            # print "We're assigning the output of a function call to the targets"
            
            targets = []
            
            try :
                for t in node.targets :
                    if isinstance(t,Name):
                        # "We're assigning to a single variable"
                        targets.append(t.id)
                    elif isinstance(t,Tuple):
                        # "We're assigning to a tuple of variables"
                        for t in t.elts:
                            if isinstance(t, Name):
                                targets.append(t.id)
                
                # Need to build a list that looks like the below to store the targets
                # List(elts=[Str(s='a'), Str(s='b')], ctx=Load())
                
                print "Found the following target variables",targets
                
                l = List()
                l.elts = []
                l.ctx = Load()
                for t in targets:
                    e = Str()
                    e.s = t
                    l.elts.append(e)
                
                # print dump(l)
                self.targets = l
            except Exception as e:
                print dump(node)
                print e
        
        self.generic_visit(node)
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
