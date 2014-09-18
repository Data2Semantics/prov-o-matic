import datetime
import hashlib
import chardet
from rdflib import Graph, Dataset, URIRef, Literal, Namespace, RDF, RDFS


    
# Global variable holding the dataset that accumulates all provenance graphs
_ds = Dataset()


def get_dataset():
    return _ds
    

def get_graph():
    PROV = Namespace('http://www.w3.org/ns/prov#')
    PROVOMATIC = Namespace('http://provomatic.org/resource/')
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
    DCT = Namespace('http://purl.org/dc/terms/')
    
    graph = Graph()
    
    # Bind namespaces to prefixes
    graph.bind('prov',PROV)
    graph.bind('provomatic',PROVOMATIC)
    graph.bind('skos',SKOS)
    graph.bind('dcterms',DCT)
    
    for s,p,o,_ in get_dataset().quads(None) :
        graph.add((s,p,o))
    

    return graph
    
def save_prov(trail_filename='provenance-trail.ttl'):
    graph = get_graph()
    
    try :
        graph.serialize(open(trail_filename,'w'),format='turtle')
        print "File saved to {}".format(trail_filename)
    except:
        print "Problem writing to {}".format(trail_filename)
    
    return
    
def add_prov(uri, prov):
    """
        prov should be a Turtle serialization of an RDF PROV-O graph
        uri is a unique id of the graph
        
        """
    PROV = Namespace('http://www.w3.org/ns/prov#')
    PROVOMATIC = Namespace('http://provomatic.org/resource/')
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
    DCT = Namespace('http://purl.org/dc/terms/')
        
    ds = get_dataset()
    
    graph = ds.graph(URIRef(uri))
    graph.parse(data=prov,format='turtle')
    
    
    
    print "Loaded provenance graph with id {}".format(uri)
    return
    
    

class ProvBuilder(object):
    PROV = Namespace('http://www.w3.org/ns/prov#')
    PROVOMATIC = Namespace('http://provomatic.org/resource/')
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
    DCT = Namespace('http://purl.org/dc/terms/')

    # The variable ticker keeps the latest version of the value of a variable, to make sure that no cycles occur in the provenance graph.
    variable_ticker = {}

    def __init__(self):
        # Bind namespaces to prefixes
        _ds.bind('prov',self.PROV)
        _ds.bind('provomatic',self.PROVOMATIC)
        _ds.bind('skos',self.SKOS)
        _ds.bind('dcterms',self.DCT)
        
        
    def tick(self, variable):
        # We increment the re-use of the variable by 1
        self.variable_ticker[variable] = self.variable_ticker.setdefault(variable,0) + 1 
        return self.variable_ticker[variable]
        
    def get_tick(self, variable):
        if variable in self.variable_ticker:
            return self.variable_ticker[variable]
        else :
            return self.tick(variable)
        
    def add_activity(self, name, description, inputs, outputs, dependencies={}, output_names=[], expand_output_dict=False, source=None):
        """Adds an activity to the graph. Inputs should be a dictionary of inputs & values, outputs a list or tuple of just values
        
           If expand_output_dict is set, the keys of the dictionary are used to generate individual outputs, otherwise the output dictionary is a single output.
           
        """
        
        if not source:
            source = description
            
        source, digest = self.get_value(source)
        
        description = unicode(description)
        
        timestamp = self.now()
        # Determine the plan and activity URI based on a digest of the source code of the function.
        plan_uri = self.PROVOMATIC['id-'+digest]
        activity_uri = self.PROVOMATIC['id-'+digest + "/" + timestamp]
        
        # print "Adding activity with name '{}'".format(name)
        # Initialise a graph with the same identifier as the activity uri
        self.g = _ds.graph(identifier=activity_uri)
        
        # Bind namespaces to prefixes
        self.g.bind('prov',self.PROV)
        self.g.bind('provomatic',self.PROVOMATIC)
        self.g.bind('skos',self.SKOS)
        self.g.bind('dcterms',self.DCT)
        
        # TODO: The PLAN part should be a qualified association
        self.g.add((plan_uri, RDF.type, self.PROV['Plan']))
        self.g.add((plan_uri, RDF.type, self.PROV['Entity']))
        self.g.add((plan_uri, RDFS.label, Literal(name)))
        self.g.add((plan_uri, self.DCT.description, Literal(description)))
        self.g.add((plan_uri,self.SKOS.note,Literal(source)))
        
        
        # print "Relating Activity '{} ({})' to Plan '{}'".format(name, timestamp, name)
        self.g.add((activity_uri,RDF.type,self.PROV['Activity']))
        self.g.add((activity_uri,RDFS.label,Literal("{} ({})".format(name, timestamp))))
        
        self.g.add((activity_uri,self.PROV['used'],plan_uri))
        self.g.add((activity_uri,self.DCT.description,Literal(description)))
    
        # For each input, create a 'used' relation
        for iname, value in inputs.items():
            value, vdigest = self.get_value(value)
            
            input_uri = self.add_entity(iname, vdigest, value)
        
            # print "Relating Activity '{} ({})' to input Entity '{}'".format(name, timestamp, input_uri)
            self.g.add((activity_uri, self.PROV['used'], input_uri))
        
        # For each output, create a 'generated' relation
        # Always expand tuples, to capture the variables separately.
        if isinstance(outputs, tuple) and len(outputs) == len(output_names):
            count = 0
            print "names: ", output_names
            print "outputs: ", outputs
            for value in outputs:
                
                value, vdigest = self.get_value(value)
                
                # If we know the output names (captured e.g. by 'replace'), we can also use them to generate nice names
                # Otherwise we create a nameless output
                print count
                if output_names != [] :
                    print "Generating entity for {}".format(output_names[count])
                    self.tick(output_names[count])
                    output_uri = self.add_entity(output_names[count],vdigest,value)
                else :
                    output_uri = self.add_entity("{} output {}".format(name,count),vdigest,value)
            
                # print "Relating Activity '{} ({})' to output Entity '{}'".format(name, timestamp, output_uri)
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
                
                count += 1
        # Only expand dictionaries when explicitly told to do so
        elif expand_output_dict and isinstance(outputs,dict):
            for oname, value in outputs.items() :
                value, vdigest = self.get_value(value)
                
                output_uri = self.add_entity(oname, vdigest, value)
                
                # print "Relating Activity '{}' to output Entity '{}'".format(name, output_uri)
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
        # Otherwise we'll take the value at 'face value'
        else :
            value, vdigest = self.get_value(outputs)
            
            # If we know the output name (captured e.g. by 'replace'), we can also use them to generate nice names
            # Otherwise we create a nameless output
            if output_names != []:
                print "Generating entity for {}".format(output_names[0])
                self.tick(output_names[0])
                output_uri = self.add_entity(output_names[0],vdigest,value)
            else :
                output_uri = self.add_entity("{} output".format(name), vdigest, value)
            
        
            # print "Relating Activity '{} ({})' to output Entity '{}'".format(name, timestamp, output_uri)
            self.g.add((activity_uri, self.PROV['generated'], output_uri))
            
        # For each dependency, create a 'wasInformedBy' relation
        
        # TODO: SKIPPING THIS FOR NOW
        # for dname, value in dependencies.items():
        #     value, vdigest = self.get_value(value)
        #
        #     dependency_uri = self.PROVOMATIC[vdigest]
        #
        #     self.g.add((dependency_uri,RDF.type,self.PROV['Activity']))
        #     # self.g.add((dependency_uri,RDFS.label,Literal(dname)))
        #     self.g.add((dependency_uri,self.SKOS.note,Literal(value)))
        #
        #     self.g.add((activity_uri, self.PROV['wasInformedBy'], dependency_uri))
        
        return activity_uri



    def add_entity(self, name, digest, description):
        
        tick = self.get_tick(name)
        
        entity_uri = self.PROVOMATIC['{}/{}/{}'.format(name.replace(' ','_').replace('%','_'),tick,digest)]
    
        # print "Adding Entity with label '{}' ({})".format(name,entity_uri)
    
        self.g.add((entity_uri,RDF.type,self.PROV['Entity']))
        self.g.add((entity_uri,RDFS.label,Literal(name)))
        self.g.add((entity_uri,self.SKOS['note'],Literal(description)))
    
        return entity_uri
    
    def get_value(self, io):
        """We'll just use the __unicode__ representation as source for the hash digest"""
        
        
        try :
            value = unicode(io)
        except :
            print "Type: ", type(io)
            print "IO cannot be decoded"
            encoding = chardet.detect(io)['encoding']
            if encoding == None :
                print "No encoding"
                value = io.encode('string-escape').decode('utf-8')
            else :
                print "Encoding: {}".format(encoding)
                value = io.decode(encoding)
            
        
        vdigest = hashlib.md5(value.encode('utf-8')).hexdigest()

        if len(value) > 200:
            value = value[:99] + u"..." + value[-100:]
    
        return value, vdigest

    def get_graph(self):
        return self.g
        
    def now(self):
        return datetime.datetime.now().isoformat()