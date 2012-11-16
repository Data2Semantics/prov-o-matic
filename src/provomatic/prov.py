'''
Created on 16 Jan 2012

@author: hoekstra
'''

from rdflib import ConjunctiveGraph, Graph, Namespace, URIRef, Literal, BNode, RDF, RDFS, OWL, XSD, plugin, query
from subprocess import check_output, call
from datetime import datetime
from urllib import quote
from optparse import OptionParser, OptionValueError
from StringIO import StringIO
import shlex
import logging
import sys
import os
import socket



class Trace(object):
    '''
    classdocs
    '''
    
    def __init__(self, provns = "http://www.example.com/prov/", trailFile = None, logLevel = logging.DEBUG):
        '''
        Constructor
        '''
        
        
        self.trail = {}
        
        # Initialise logger
        
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logLevel)
        
        logHandler = logging.StreamHandler()
        logHandler.setLevel(logging.DEBUG)
        
        logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(logFormatter)
        
        self.log.addHandler(logHandler)
        
        # Initialise graph
        self.log.debug("Initialising graph")
        self.g = ConjunctiveGraph()
        
        self.log.debug("Initialising namespaces")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")
        self.D2S = Namespace("http://aers.data2semantics.org/vocab/provenance/")
        self.FRBR = Namespace("http://purl.org/vocab/frbr/core#")
        self.TIME = Namespace("http://www.w3.org/2006/time#")
        self.PROVNS = Namespace(provns)
        
        self.log.debug("Binding namespace prefixes")
        self.g.bind("prov", self.PROV)
        self.g.bind("d2sprov", self.D2S)
        self.g.bind("frbr", self.FRBR)
        self.g.bind("time", self.TIME)
        self.g.bind("provns", self.PROVNS)
        
        if trailFile :
            try:
                self.log.debug("Loading provenance trail file")
                self.g.parse(trailFile, format='n3')
                self.buildProvenanceTrail()
            except :
                print "Trailfile does not exist yet..."
        

        
        self.log.debug("Initialised")
        
        return
    
    def buildProvenanceTrail(self):
        self.log.debug("Loading provenance trail")
        plugin.register('sparql', query.Processor,
                       'rdfextras.sparql.processor', 'Processor')
        plugin.register('sparql', query.Result,
                       'rdfextras.sparql.query', 'SPARQLQueryResult')
        
#        self.log.debug(self.g.serialize(format='turtle'))

        expressions_works = self.g.query(
    """SELECT DISTINCT ?w ?e
       WHERE {
          ?w rdf:type frbr:Work .
          ?e frbr:realizationOf ?w .
          ?e provo:wasGeneratedAt ?t .
          ?t time:inXSDDateTime ?dt .
       } ORDER BY ?w, ?dt """, initNs=dict(
                                         frbr=Namespace("http://purl.org/vocab/frbr/core#"), 
                                         provo=Namespace("http://www.w3.org/ns/prov-o/"),
                                         time=Namespace("http://www.w3.org/2006/time#")))
#        self.log.debug(expressions_works.result)

        for row in expressions_works.result:
            (work,expression) = row
            
            self.trail.setdefault(work, []).append(expression) 
            
            self.log.debug("Work: %s\nExpression: %s" % (work,expression))


        activities = self.g.query(
    """SELECT DISTINCT ?a
       WHERE {
          ?a rdf:type provo:Activity .
          ?a provo:endedAt ?t .
          ?t time:inXSDDateTime ?dt .
       } ORDER BY ?dt """, initNs=dict(
                                         frbr=Namespace("http://purl.org/vocab/frbr/core#"), 
                                         provo=Namespace("http://www.w3.org/ns/prov-o/"),
                                         time=Namespace("http://www.w3.org/2006/time#")))
        self.log.debug(activities.result)

        for row in activities.result:
            
            
            self.trail.setdefault(self.PROV['Activity'], []).append(row) 
            
            self.log.debug("Activity: %s" % (row))

            
        self.log.debug(self.trail)
#        quit()
        return
    
    
    
    def execute(self, params = [], inputs = [], outputs = [], replace = None, logOutput = True, sandbox=False):
        '''
        Calls a commandline script using subprocess.call, and captures relevant provenance information
            @param params - A list of strings used as arguments to the subprocess.call method
            @param inputs - A list of strings (QNames) for all input resources
            @param outputs - A list of strings (QNames) for all output resources
            @param replace - A string that should not be reported in in the provenance trail (e.g. a password)
            @param logOutput - A boolean option for capturing the output of the shell script in an rdfs:comment field
        '''
        
        commandURI = self.mintActivity(params[0])
        
        # Get & set the starting time
        start = self.mintTime()
        self.g.add((commandURI, self.PROV['startedAt'], start))
        
        
        # Execute the command specified in params
        self.log.debug("Executing {0}".format(params))
        
        if not sandbox :
            output = check_output(params)
        else :
            self.log.debug("Sandbox mode: command not executed, no actual output generated")
            output = "Sandbox mode: command not executed, no actual output generated"
#        self.log.debug("Output:\n{0}".format(output))
        
        # Optionally store the command stdout to a literal value
        if logOutput :
            self.g.add((commandURI, RDFS.comment, Literal(output, datatype=XSD.string)))

            
        # Get & set the end time
        end = self.mintTime()
        self.g.add((commandURI, self.PROV['endedAt'], end))

        # Store all parameters in a new provo:Activity instance
        for p in params[1:] :
            if not (p in inputs or p in outputs) :
                # Optionally replace the 'replace' string with 'HIDDENVALUE' (useful for passwords)
                if replace :
                    pclean = p.replace(replace, 'HIDDENVALUE')
                else :
                    pclean = p            
            
                self.log.debug("Adding literal parameter value: {0}".format(pclean))
                self.g.add((commandURI, self.D2S['parameter'], Literal(pclean)))

        for p in inputs :
            # Optionally replace the 'replace' string with 'HIDDENVALUE' (useful for passwords)
            if replace :
                pclean = p.replace(replace, 'HIDDENVALUE')
            else :
                pclean = p  
            # p is an input to the process, and thus a resource by itself
            # p is a frbr:Expression (version) of a work (e.g. we could generate multiple versions of the same file)

            # If a work & expression for 'p' has already been specified, use the latest one.
            p_work = self.PROVNS[quote(pclean, safe='~/')]
            if p_work in self.trail :
                pExpressionURI = self.trail[p_work][-1]
                self.log.debug("Found previous expression: {0}".format(pExpressionURI))
                # And this means that the current Activity 'wasInformedBy' the process that generated the expression
                for (subj,pred,activity) in self.g.triples((pExpressionURI,self.PROV['wasGeneratedBy'],None)) :
                    self.log.debug("Adding provo:wasInformedBy dependency between {0} and {1}".format(commandURI,activity))
                    self.g.add((commandURI,self.PROV['wasInformedBy'],activity))
                
            # Otherwise create a new expression
            else :
                pExpressionURI = self.mintExpression(pclean)
                self.log.debug("Minted new input expression: {0}".format(pExpressionURI))
                
            self.g.add((commandURI, self.PROV['used'], pExpressionURI))
        
        for p in outputs :
            # Optionally replace the 'replace' string with 'HIDDENVALUE' (useful for passwords)
            if replace :
                pclean = p.replace(replace, 'HIDDENVALUE')
            else :
                pclean = p  
            
            pExpressionURI = self.mintExpression(pclean)
            self.log.debug("Minted new output expression: {0}".format(pExpressionURI))
            
            self.g.add((pExpressionURI, self.PROV['wasGeneratedBy'], commandURI))
            self.g.add((pExpressionURI, self.PROV['wasGeneratedAt'], end))
                
        
        return
    
    
    def mintActivity(self, p):
        porig = p
        p = quote(p, safe='~/')
        p = p.lstrip('./')
        
        commandURI = self.PROVNS["{0}_{1}".format(p, datetime.now().isoformat())]
        commandTypeURI = self.D2S[p.capitalize()]
        
        if self.PROV['Activity'] in self.trail :
            lastActivity = self.trail[self.PROV['Activity']][-1]
            self.log.debug("Adding provo:wasScheduledAfter dependency between {0} and {1}".format(commandURI, lastActivity))
            self.g.add((commandURI, self.PROV['wasScheduledAfter'], lastActivity))
        
        self.g.add((commandTypeURI, RDF.type, self.PROV['Plan']))
        self.g.add((commandURI, self.PROV['hadPlan'], commandTypeURI))
        self.g.add((commandURI, RDF.type, self.PROV['Activity']))
        self.g.add((commandURI, self.D2S['shellCommand'], Literal(porig)))
        
        userURI = URIRef('http://{0}/{1}'.format(socket.gethostname(),os.getlogin()))
        self.g.add((commandURI, self.PROV['wasControlledBy'], userURI))
        
        # Add the activity to the list of activities in the provenance trail
        self.trail.setdefault(self.PROV['Activity'], []).append(commandURI) 
        
        return commandURI
    
    def mintTime(self):
        time = BNode()
        now = datetime.now().isoformat()
        self.g.add((time, RDF.type, self.TIME['Instant']))
        self.g.add((time, self.TIME['inXSDDateTime'], Literal(now, datatype=XSD.dateTime)))
        
        return time
        
    def mintExpression(self, p):
        
        # If the parameter is a URI, just use it, but add a timestamp
        if p.startsWith('http://') :
            pExpressionURI = URIRef("{0}_{1}".format(p, datetime.now().isoformat()))
        # Else mint a new URI within our own namespace
        else :
            p = quote(p, safe='~/')
            p = p.lstrip('./')
            pExpressionURI = self.PROVNS["{0}_{1}".format(p, datetime.now().isoformat())]
        
        # Add the Expression to the trail for its Work
        self.trail.setdefault(self.PROVNS[p], []).append(pExpressionURI) 
        
        self.g.add((self.PROVNS[p], RDF.type, self.FRBR['Work']))
        self.g.add((pExpressionURI, RDF.type, self.FRBR['Expression']))
        self.g.add((pExpressionURI, RDF.type, self.PROV['Entity']))
                
        self.g.add((pExpressionURI, self.FRBR['realizationOf'], self.PROVNS[p]))
        
        return pExpressionURI
    
    
    
    def serialize(self, trailFile = 'out.ttl'):
        f = open(trailFile,"w")
        print "Serializing to {}".format(trailFile)
        return self.g.serialize(f, format='turtle')
        print "Done"
    





def checkNS(option, opt, value, parser):
    if value.endswith('/') or value.endswith('#') :
        setattr(parser.values, option.dest, value)
    else :
        raise OptionValueError("NAMESPACE should end with a / or # character")






if __name__ == '__main__':
    usage = "usage: %prog [options] \"shell-command\""
    parser = OptionParser(usage=usage)
    parser.add_option("--prov-ns", type="string", action="callback", callback=checkNS, metavar="NAMESPACE", dest="provns", help="Where NAMESPACE is the target namespace for generated resources (should end with # or /)")
    parser.add_option("--prov-trail", type="string", metavar="FILE", dest="trail", help="Add the generated provenance information to the existing provenance trail in FILE")
    parser.add_option("--prov-destination", type="string", metavar="FILE", dest="destination", help="Serialize the generated RDF graph to FILE (default is 'out.ttl')", default='out.ttl')
    parser.add_option("--prov-inputs", type="string", metavar="INPUTS", dest="inputs", help="Comma separated list of input resources (QNames) for this activity")
    parser.add_option("--prov-outputs", type="string", metavar="OUTPUTS", dest="outputs", help="Comma separated list of output resources (QNames) for this activity")
    parser.add_option("--prov-hide", type="string", dest="hidden", help="String to hide from provenance record (e.g. passwords)")
    (option,args) = parser.parse_args()
    
#    print option
#    print args
    
    if option.inputs:
        splitter = shlex.shlex(option.inputs, posix=True)
        splitter.whitespace = ','
        splitter.whitespace_split = True
        trace_inputs = list(splitter)
    else :
        trace_inputs = []
    if option.outputs:
        splitter = shlex.shlex(option.outputs, posix=True)
        splitter.whitespace = ','
        splitter.whitespace_split = True
        trace_outputs = list(splitter)
    else :
        trace_outputs = []
    
    if option.provns and option.trail:
        t = Trace(provns=option.provns, trailFile=option.trail)
    elif option.provns :
        t = Trace(provns=option.provns)
    elif option.trail :
        t = Trace(trailFile = option.trail)
    else :
        t = Trace()
    
    for command in args :
        splitter = shlex.shlex(command, posix=True)
        splitter.whitespace = ' '
        splitter.whitespace_split = True
        command_call = list(splitter)
        t.execute(command_call, inputs=trace_inputs, outputs=trace_outputs, replace=option.hidden)
    
    f = open(option.destination, "w")
    t.serialize(file=f)