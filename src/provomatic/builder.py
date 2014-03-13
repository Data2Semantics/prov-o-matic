import datetime
import hashlib

from rdflib import Graph, Dataset, URIRef, Literal, Namespace, RDF, RDFS


    
# Global variable holding the dataset that accumulates all provenance graphs
_ds = Dataset()


def get_dataset():
    return _ds

class ProvBuilder(object):
    PROV = Namespace('http://www.w3.org/ns/prov#')
    PROVOMATIC = Namespace('http://provomatic.org/resource/')
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')


    def add_activity(self, name, description, inputs, outputs, dependencies={}, expand_output_dict=False):
        """Adds an activity to the graph. Inputs should be a dictionary of inputs & values, outputs a list or tuple of just values"""
        
        description, digest = self.get_value(description)
        
        # Determine the plan and activity URI based on a digest of the source code of the function.
        plan_uri = self.PROVOMATIC[digest]
        activity_uri = self.PROVOMATIC[digest + "/" + self.now()]
        
        # Initialise a graph with the same identifier as the activity uri
        self.g = _ds.graph(identifier=activity_uri)
        
        # Bind namespaces to prefixes
        self.g.bind('prov',self.PROV)
        self.g.bind('provomatic',self.PROVOMATIC)
        self.g.bind('skos',self.SKOS)
        
        
        self.g.add((plan_uri, RDF.type, self.PROV['Plan']))
        self.g.add((plan_uri, RDFS.label, Literal("{} Plan".format(name))))
        self.g.add((plan_uri,self.SKOS.note,Literal(description)))
        
    
        self.g.add((activity_uri,RDF.type,self.PROV['Activity']))
        self.g.add((activity_uri,RDFS.label,Literal(name)))
        self.g.add((activity_uri,self.PROV['used'],plan_uri))
        self.g.add((activity_uri,self.SKOS.note,Literal(description)))
    
        # For each input, create a 'used' relation
        for iname, value in inputs.items():
            value, vdigest = self.get_value(value)
            
            input_uri = self.add_entity(iname, vdigest, value)
        
            self.g.add((activity_uri, self.PROV['used'], input_uri))
        
        # For each output, create a 'generated' relation
        # Always expand tuples, to capture the variables separately.
        if isinstance(outputs, tuple) :
            count = 0
            for value in outputs:
                count += 1
            
                value, vdigest = self.get_value(value)
        
                output_uri = self.add_entity("{} output {}".format(name,count),vdigest,value)
            
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
        # Only expand dictionaries when explicitly told to do so
        elif expand_output_dict and isinstance(outputs,dict):
            for oname, value in outputs.items() :
                value, vdigest = self.get_value(value)
                
                output_uri = self.add_entity(oname, vdigest, value)
                
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
        # Otherwise we'll take the value at 'face value'
        else :
            value, vdigest = self.get_value(outputs)
        
            output_uri = self.add_entity("{} output".format(name), vdigest, value)
        
            self.g.add((activity_uri, self.PROV['generated'], output_uri))
            
        # For each dependency, create a 'wasInformedBy' relation
        for dname, value in dependencies.items():
            value, vdigest = self.get_value(value)
            
            dependency_uri = self.add_entity(dname, vdigest, value)
            
            self.g.add((activity_uri, self.PROV['wasInformedBy'], dependency_uri))
        
        return activity_uri

    def add_entity(self, name, digest, description):
        entity_uri = self.PROVOMATIC[digest]
    
        self.g.add((entity_uri,RDF.type,self.PROV['Entity']))
        self.g.add((entity_uri,RDFS.label,Literal(name)))
        self.g.add((entity_uri,self.SKOS['note'],Literal(description)))
    
        return entity_uri
    
    def get_value(self, io):
        """We'll just use the __unicode__ representation as source for the hash digest"""
        value = unicode(io)
        vdigest = hashlib.md5(unicode(value)).hexdigest()

        if len(value) > 200:
            value = value[:99] + u"..." + value[-100:]
    
        return value, vdigest

    def get_graph(self):
        return self.g
        
    def now(self):
        return datetime.datetime.now().isoformat()