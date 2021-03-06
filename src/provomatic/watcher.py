from IPython.core.history import HistoryAccessor
from IPython.core.ultratb import VerboseTB

import numpy
import inspect
import hashlib
import collections
from copy import deepcopy
from ast import *

from builder import ProvBuilder

import logging

log = logging.getLogger('provomatic.watcher')
log.setLevel(logging.INFO)

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
        self.pre_ticker = {}

        
        

    def pre_execute(self):
        """Before the code is executed, we reset the list of variables/functions etc. 'used' (as we don't know them yet)."""
        # Reset the used list
        self.used = set()
        
        pb = ProvBuilder()
        self.pre_ticker = deepcopy(pb.get_ticker())


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
            # log.debug("Checking wether " + node + " is a variable or a function")
            try :
                evaluated_node = self.shell.ev(node)
                # log.debug("> Could evaluate {}".format(node) )
                if node in self.environment and not callable(evaluated_node) :
                    # log.debug(">> {} is in environment and not callable (it is a variable)".format(node))
                    # # log.debug("Used global variable {}".format(node))
                    # Set the input of the node to the value that it had prior to executing the code (if available)
                    if node in self.environment:
                        # log.debug("Global variable existed before, adding to inputs")
                        inputs[node] = self.environment[node]
                    # Otherwise, we do nothing, since the variable may have been used, but was first introduced in the code.
                    else :
                        # log.debug("Global variable was introduced here, not doing anything")
                        pass
               
                elif callable(evaluated_node):
                    # log.debug(">> {} is a function, adding to dependencies.".format(node))
                    try :
                        dependencies[node] = inspect.getsource(evaluated_node)
                    except Exception as e:
                        # print e
                        dependencies[node] = unicode(evaluated_node)
                else :
                    # log.debug(">> {} is not callable, and not in environment... it was a variable that was newly introduced here?".format(node))
                    pass
            except :
                ## log.debug("Used local {} variable or function".format(node))
                # log.debug("> Could not evaluate " + node)
                if node in self.environment :
                    # log.debug(">> Node is in environment, we'll use its evaluated value from the environment")
                    evaluated_node = self.environment[node]
                    
                    if not callable(evaluated_node) :
                        # log.debug(">>> {} is a variable".format(node))
                        inputs[node] = evaluated_node
                    else :
                        # log.debug(">>> {} is a function".format(node))
                        dependencies[node] = inspect.getsource(evaluated_node)
                else :
                    # log.debug(">> {} was introduced here, not doing anything".format(node))
                    pass
                
        # We'll loop through all known entities in the user namespace.
        for k,v in self.shell.user_ns.items():
            # Ignore any standard IPython/Python variables in the user namespace
            # if k.startswith('_') or k in ['In','Out','exit','quit','get_ipython'] :
            #     log.debug("'{}' skipped, because it is in ['In','Out','exit','quit','get_ipython'] or starts with '_'".format(k))
            #     pass
            
            # TEMPORARY: Test what happens if we don't exclude 'Out'
            if k.startswith('_') or k in ['In','exit','quit','get_ipython'] :
                # log.debug("'{}' skipped, because it is in ['In','exit','quit','get_ipython'] or starts with '_'".format(k))
                continue
                
            # For all other variables, see whether they were changed, and add them to the outputs
            ## This compares the value of the variable with the value it had previously, or
            ## checks that the variable did not exist previously.  
            # Need to do some exception handling to deal with ValueErrors for objects that have ambiguous truth values
            try :
                # if (k in self.environment and not ((numpy.array_equal(v,self.environment[k]) or v == self.environment[k]) and self.pre_ticker.setdefault(k,0) == pb.get_tick(k))) or (not k in self.environment) or k == 'Out':
                if (k in self.environment and not (v == self.environment[k] and self.pre_ticker.setdefault(k,0) == pb.get_tick(k))) or (not k in self.environment) or k == 'Out':
                    changed = True
                else:
                    changed = False
            except Exception as e:
                log.debug("Caught numpy array comparison exception")
                ## Special handling of Numpy silliness
                if k in self.environment:
                    if not numpy.asarray(v == self.environment[k]).all():
                        log.debug("Not the same (value-comparison)")
                        changed = True
                    elif self.pre_ticker.setdefault(k,0) == pb.get_tick(k):
                        log.debug("Not the same (tick-comparison)")
                        changed = True
                    else :
                        changed = False
                elif not k in self.environment :
                    log.debug("Newly added variable")
                    changed = True
                elif k == 'Out' :
                    log.debug("Out value")
                    changed = True
                else :
                    log.debug("Not changed")
                    changed = False
                
            
            if changed:
                log.debug("{} changed or was added".format(k))
                
                
                
                # If the object is not a function, we'll use the value as output value.
                if not callable(v):
                    # log.debug("{} is not a function, adding to outputs as value".format(k))
                    if k == 'Out':
                        if len(v) == 0:
                            log.debug("Output value is empty: skipping...")
                            continue
                            
                        kname = 'Out [{}]'.format(position)
                        log.debug("{}: {}".format(kname,v))
                    else :
                        kname = k
                    outputs[kname] = v
                    
                    # Increase the tick of the variable with name 'k'
                    # self.tick(k)
                    
                # If it is a PROV wrapped function, we'll retrieve its source and use it as output value.
                elif callable(v) and hasattr(v,'source') :
                    # log.debug("{} is a PROV wrapped function, its source is an output value".format(k))
                    outputs[k] = v.source
                # Otherwise (this shouldn't be the case, but anyway) we'll use its source directly.
                elif callable(v) :
                    # log.debug("{} is callable, but not wrapped... we'll try to retrieve its source and add it as an output".format(k))
                    try :
                        outputs[k] = inspect.getsource(v)
                    except:
                        # log.debug("could not get source of {}, just taking its value as an output".format(k))
                        outputs[k] = v
                # Finally, this is probably not were we'll end up anyway... we'll do nothing 
                else :
                    # log.debug("Unexpected!")
                    pass
                
                # log.debug("Just visited {}".format(k))
                self.environment[k] = v
            else :
                log.debug("'{}' skipped because it did not change (ticks: {} and {}).".format(k,self.pre_ticker[k],pb.get_tick(k)))
                
        
        # print dependencies.keys()
        pb.add_activity(name, description, inputs, outputs, dependencies, input_names=inputs.keys(), output_names=outputs.keys(), expand_output_dict=True, pre_ticker=self.pre_ticker)
        


            
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
        tl = List()
        tl.elts = []
        tl.ctx = Load()
        self.targets = tl
        
        il = List()
        il.elts = []
        il.ctx = Load()
        self.input_args = il
        
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
        try :
            if isinstance(node.func,Name) :
                func_id = node.func.id
            elif isinstance(node.func,Attribute) and isinstance(node.func.value,Call):
                func_id = node.func.value.func.id
            elif isinstance(node.func,Attribute) and isinstance(node.func.value,Name):
                func_id = node.func.value.id
            else :
                return None
        
            return func_id
        except Exception as e:
            log.warning('Could not retrieve function name')
            log.debug(dump(node))
            return None

    def visit_Call(self, node):
        self.generic_visit(node)
        fix_missing_locations(node)
        #self.nw.register_usage(node)

        log.debug("> call")
        log.debug(dump(node))
        
        func_id = self.get_func_id(node)
        
        if not func_id:
            # log.debug("Unknown function type")
            # log.debug("===")
            return node
        
        # print func_id
        if func_id == 'replace':
            # log.debug("Skipping {}, already replaced".format(dump(node.func)))
            # print dump(node)
            # log.debug("===")
            return node
            
        # log.debug("Not skipping")
        
        try :
            
            # First we add the name of the function
            new_args = [node.func]
            
            # Then we'll add the input argument names
            if self.input_args:
                ## Use the targets
                new_args.append(self.input_args)
                ## And reset them, to avoid propagation of target variable names to nested function calls.
                l = List()
                l.elts = []
                l.ctx = Load()
                self.input_args = l
            else :
                # log.debug("no targets")
                l = Lists()
                l.elts = []
                l.ctx = Load()
                new_args.append(l)
            
            # Then we'll add the output names (the targets)
            if self.targets:
                ## Use the targets
                new_args.append(self.targets)
                ## And reset them, to avoid propagation of target variable names to nested function calls.
                l = List()
                l.elts = []
                l.ctx = Load()
                self.targets = l
            else :
                # log.debug("no targets")
                l = Lists()
                l.elts = []
                l.ctx = Load()
                new_args.append(l)
                
                

            
            new_args.extend(node.args)
            # log.debug("New Args:", [dump(a) for a in new_args])
            new_call = Call(Name('replace',Load()),new_args,node.keywords,node.starargs,node.kwargs)
            copy_location(new_call,node)
            fix_missing_locations(new_call)
            
            # log.debug("New")
            # print dump(new_call)
            
        except Exception as e:
            log.debug("Whoops!")
            print dump(node)
            print e
            return node
            
        # log.debug("===")
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
    #             # log.debug("Already wrapped or in exclusion list")
    #         else :
    #             # log.debug("Inserting prov wrapper")
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
    #             # # log.debug("Adding PROV Wrapper to {}".format(node.name))
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
        # log.debug("> augassign")
        # print dump(node)
        return self.generic_visit(node)
        
    def visit_Assign(self, node):
        # TODO Capture the assignment itself
        # This just captures the outputs expected from a function
        
        log.debug("> assign")
        log.debug(dump(node))
        # log.debug("Resetting targets")
        tl = List()
        tl.elts = []
        tl.ctx = Load()
        self.targets = tl
        
        al = List()
        al.elts = []
        al.ctx = Load()
        self.input_args = al
        
        if isinstance(node.value,Call):
            # log.debug("We're assigning the output of a function call to the targets")
            input_args = []
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
                # log.debug("Found the following target variables",targets)
                
                target_l = List()
                target_l.elts = []
                target_l.ctx = Load()
                for t in targets:
                    e = Str()
                    e.s = t
                    target_l.elts.append(e)
                    
                    
                # We'll do something similar for the names of the input arguments!
                for arg in node.value.args :
                    if isinstance(arg,Name):
                        input_args.append(arg.id)
                        
                        
                input_args_l = List()
                input_args_l.elts = []
                input_args_l.ctx = Load()
                for arg in input_args:
                    e = Str()
                    e.s = arg
                    input_args_l.elts.append(e)
                    

                self.targets = target_l
                self.input_args = input_args_l
                
            except Exception as e:
                print dump(node)
                print e
        
        self.generic_visit(node)
        return node
                
    # def visit_Assign(self, node):
    #     
    #     if isinstance(node.value,Call):
    #         try :
    #             # log.debug("===\nAssignment with Function Call")
    #             # log.debug("Old: ", dump(node))
    #         
    #         
    #             # Replace Store() context with Load() context
    #             # This is easiest with a string replace, but potentially very very very buggy
    #             targets = []
    #             for t in node.targets:
    #                 new_t = eval(dump(t, annotate_fields = False).replace('Store()','Load()'))
    #                 targets.append(new_t)
    # 
    #             # log.debug("Targets: ", [dump(t) for t in targets])
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
    #             # log.debug("New KW: ", [dump(k) for k in new_keywords])
    #             new_call = Call(node.value.func,node.value.args,new_keywords,node.value.starargs,node.value.kwargs)
    #             
    #             # log.debug("New Call: ", dump(new_call))
    #             new_assignment = Assign(node.targets,new_call)
    #             
    #             # log.debug("New: ", dump(new_assignment))
    # 
    #             fix_missing_locations(new_assignment)
    #             self.generic_visit(new_assignment)
    #             fix_missing_locations(new_assignment)
    #             copy_location(new_assignment,node)
    #             fix_missing_locations(new_assignment)
    #             # log.debug("==="            )
    #             
    # 
    #             return new_assignment
    #         except:
    #             # log.debug("Whoops")
    #             # print e
    #             # log.debug("===")
    #             self.generic_visit(node)
    #             
    #             return node
    #     else:
    #         # log.debug("===")
    #         self.generic_visit(node)
    #         fix_missing_locations(node)
    #         return node        
