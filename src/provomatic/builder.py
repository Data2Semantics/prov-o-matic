import datetime
import hashlib
import chardet
import types
from rdflib import Graph, Dataset, URIRef, Literal, Namespace, RDF, RDFS, XSD
from rdflib.term import bind
import logging
import pandas as pd
from StringIO import StringIO
import re

log = logging.getLogger('provomatic.builder')
log.setLevel(logging.INFO)
    
# Global variable holding the dataset that accumulates all provenance graphs
_ds = Dataset()

PROV = Namespace('http://www.w3.org/ns/prov#')
PROVOMATIC = Namespace('http://provomatic.org/resource/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
DCT = Namespace('http://purl.org/dc/terms/')

def get_decoded_value(io):
    try :
        value = unicode(io)
    except :
        encoding = chardet.detect(io)['encoding']
        if encoding == None :
            value = io.encode('string-escape').decode('utf-8')
        else :
            value = io.decode(encoding)
            
    return value

# def construct_dataframe(csv):
#     df = pd.DataFrame.from_csv(csv)
#     return df
#
# def lexicalize_dataframe(df):
#     csv = StringIO()
#
#     df.to_csv(csv)
#     csv_value = get_decoded_value(csv.getvalue())
#
#     return csv_value
#
# bind(PROVOMATIC['DataFrame'],pd.DataFrame,constructor=construct_dataframe,lexicalizer=lexicalize_dataframe)


def clear_dataset():
    _ds = Dataset()

def get_dataset():
    return _ds
    

def get_graph():
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
        log.info("File saved to {}".format(trail_filename))
    except:
        log.warning("Problem writing to {}".format(trail_filename))
    
    return
    
def add_prov(uri, prov=None,url=None):
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
    
    if prov :
        graph.parse(data=prov,format='turtle')
    elif url :
        try :
            graph.parse(url,format='turtle')
        except Exception as e:
            log.error(e)
            return
    else :
        log.error("Should provide either provenance data or a URL where I can fetch some")
        return
    
    log.debug("Loaded provenance graph with id {}".format(uri))
    return 

def list_entities():
    # This query retrieves all entities
    
    q = """
        SELECT DISTINCT ?entity ?label ?time ?tick WHERE {
            GRAPH ?g {
                {{ ?entity a prov:Entity . }} UNION {{ ?entity prov:wasGeneratedBy ?a .}} 
                ?entity rdfs:label ?label .
                ?entity rdf:value ?v .
                OPTIONAL {
                    ?entity provomatic:tick ?tick 
                }
                OPTIONAL {
                    ?entity prov:wasGeneratedAtTime ?time 
                }
            }
        } ORDER BY DESC(?time) DESC(?tick)
    """
    ds = get_dataset()
    results = ds.query(q)
    
    entities = {}
    
    for result in results:
        uri = result['entity'].__str__()
        label = result['label'].value
        
        tick = None
        if result['tick']:
            tick = result['tick'].value
        
        time = None
        if result['time']:
            time = result['time'].value
        
        
        
        entities.setdefault(label,[]).append({'uri': uri, 'name': label, 'tick': tick, 'time': time})
        
    return entities
    
def list_activities():
    # This query retrieves all activities
    
    q = """
        SELECT DISTINCT ?activity ?label WHERE {
            GRAPH ?g {
                ?activity a prov:Activity . 
                ?activity rdfs:label ?label .
            }
        } 
    """
    ds = get_dataset()
    results = ds.query(q)
    
    activities = {}
    
    for result in results:
        uri = result['activity'].__str__()
        label = result['label'].value

        activities.setdefault(label,[]).append({'uri': uri, 'name': label})
        
    return activities


def revive(name, uri = None, tick = None):
    
    if not uri and not tick :
        # This query retrieves all entities with a certain name, ordered by date
        q = """
            SELECT DISTINCT ?entity ?value ?time ?tick WHERE {{ 
                GRAPH ?g {{
                    {{ ?entity a prov:Entity . }} UNION {{ ?entity prov:wasGeneratedBy ?a .}}
                    ?entity rdfs:label ?label .
                    ?entity rdf:value ?value .
                    OPTIONAL {{ 
                        ?entity prov:wasGeneratedAtTime ?time .
                    }}
                    OPTIONAL {{
                        ?entity provomatic:tick ?tick .
                    }}
                    FILTER (str(?label) = "{}")
                }}
            }} ORDER BY DESC(?time) DESC(?tick)""".format(name)
    elif uri :
        # This query retrieves the entity with the specified uri
        q = """
            SELECT DISTINCT ?entity ?value ?time ?tick WHERE {{ 
                GRAPH ?g {{
                    {{ <{0}> a prov:Entity . }} UNION {{ <{0}> prov:wasGeneratedBy ?a .}}
                    <{0}> rdf:value ?value .
                    OPTIONAL {{ 
                        <{0}> prov:wasGeneratedAtTime ?time .
                    }}
                    OPTIONAL {{
                        <{0}> provomatic:tick ?tick .
                    }}
                }}
                BIND (<{0}> as ?entity )
            }} ORDER BY DESC(?time) DESC(?tick)""".format(uri)        
    elif tick :
        # This query retrieves all entities with a certain name, that have the specified tick, ordered by date
        q = """
            SELECT ?entity ?value ?time ?tick WHERE {{ 
                GRAPH ?g {{
                    {{ ?entity a prov:Entity . }} UNION {{ ?entity prov:wasGeneratedBy ?a .}} 
                    ?entity rdfs:label ?label .
                    ?entity rdf:value ?value .
                    OPTIONAL {{ 
                        ?entity prov:wasGeneratedAtTime ?time .
                    }}
                    ?entity provomatic:tick ?tick.
                    FILTER (str(?label) = "{}")
                    FILTER (str(?tick) = "{}")
                }}
            }} ORDER BY DESC(?time) DESC(?tick)""".format(name, tick)

    log.debug(q)        
    ds = get_dataset()
    results = ds.query(q)


    
    entity = None
    value = None
    for result in results :
        log.debug(result)
        entity = result['entity'].__str__()
        value = result['value'].value
        
        etick = None
        if result['tick']:
            etick = result['tick'].value
            
        time = None
        if result['time']:
            time = result['time'].value
        
        if not result['time'] and not result['tick'] and not uri:
            log.warning('No ordering information in provenance graph... picking arbitrary entity value') 
        
        # We only pick the first result (the last generated entity)
        break
    
    if entity :
        log.info("Entity imported as variable of type '{}'".format(type(value)))
        log.info("URI:\t{}".format(entity))
        if time :
            log.info("Time:\t{}".format(time.isoformat()))
        if tick :
            log.info("Tick:\t{}".format(etick))
        
        
        pb = ProvBuilder()
        g = _ds.graph(identifier=entity)
        pb.set_graph(g)
        
        if etick :
            new_tick = pb.set_tick(name, etick)
        else :
            new_tick = pb.get_tick(name)
        
        log.info("Imported value has tick {}".format(new_tick))
        unicodevalue, vdigest = pb.get_value(value)
        entity_uri = pb.add_entity(name, vdigest, unicodevalue, value=value, timestamp = pb.now())
        
        g.add((entity_uri,PROV['wasDerivedFrom'],URIRef(entity)))
        
        
        
        return value
    else :
        log.warning("No entity with that name found, or entity has no value for 'rdf:value'")
        return None
    

class ProvBuilder(object):
    PROV = Namespace('http://www.w3.org/ns/prov#')
    PROVOMATIC = Namespace('http://provomatic.org/resource/')
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
    DCT = Namespace('http://purl.org/dc/terms/')

    # The variable ticker keeps the latest version of the value of a variable, to make sure that no cycles occur in the provenance graph.
    # This is a class variable, that persists across all instances of the ProvBuilder class.
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
        
    def get_ticker(self):
        return self.variable_ticker
        
    def get_tick(self, variable):
        if variable in self.variable_ticker:
            return self.variable_ticker[variable]
        else :
            return self.tick(variable)
            
    def set_tick(self, variable, tick):
        if variable in self.variable_ticker:
            if tick > self.variable_ticker[variable] :
                self.variable_ticker[variable] = tick + 1
            else :
                self.variable_ticker[variable] += 1
        else :
            self.variable_ticker[variable] = tick + 1
        
        return self.variable_ticker[variable]
        
    def add_activity(self, name, description, inputs, outputs, dependencies={}, input_names=[], output_names=[], expand_output_dict=False, source=None, pre_ticker = None):
        """Adds an activity to the graph. Inputs should be a dictionary of inputs & values, outputs a list or tuple of just values
        
           If expand_output_dict is set, the keys of the dictionary are used to generate individual outputs, otherwise the output dictionary is a single output.
           
        """
        log.debug(name)
        
        if not source:
            source = description
            
        source, digest = self.get_value(source)
        
        
        description = unicode(description)
        
        ts = self.now()
        
        formatted_timestamp = ts.strftime('%H:%M:%S')
        timestamp = ts.isoformat()
        
        # Determine the plan and activity URI based on a digest of the source code of the function.
        plan_uri = self.PROVOMATIC['id-'+digest]
        activity_uri = self.PROVOMATIC['id-'+digest + "/" + timestamp]
        
        # log.debug("Adding activity with name '{}'".format(name))
        # Initialise a graph with the same identifier as the activity uri
        self.g = _ds.graph(identifier=activity_uri)
        
        # Bind namespaces to prefixes
        self.g.bind('prov',self.PROV)
        self.g.bind('provomatic',self.PROVOMATIC)
        self.g.bind('skos',self.SKOS)
        self.g.bind('dcterms',self.DCT)
        
        # TODO: The PLAN part should be a qualified association
        self.g.add((plan_uri, RDF.type, self.PROV['Plan']))
        # self.g.add((plan_uri, RDF.type, self.PROV['Entity']))
        self.g.add((plan_uri, RDFS.label, Literal(name)))
        self.g.add((plan_uri, self.DCT.description, Literal(description)))
        self.g.add((plan_uri,self.SKOS.note,Literal(source)))
        
        
        
        # log.debug("Relating Activity '{} ({})' to Plan '{}'".format(name, timestamp, name))
        self.g.add((activity_uri,RDF.type,self.PROV['Activity']))
        self.g.add((activity_uri,RDFS.label,Literal("{} ({})".format(name, formatted_timestamp))))
        
        self.g.add((activity_uri,self.PROV['used'],plan_uri))
        self.g.add((activity_uri,self.DCT.description,Literal(description)))
    
        log.debug("input names: {}".format(input_names))
        log.debug("inputs: {}".format(inputs))
        
        # For each input, create a 'used' relation
        for iname, value in inputs.items():
            unicodevalue, vdigest = self.get_value(value)
            
            if input_names != []:
                # Get the first external input name, and remove from the list
                external_iname = input_names.pop(0)
                
                input_uri = self.add_entity(external_iname,vdigest,unicodevalue,value=value, ticker=pre_ticker)
            else :
                input_uri = self.add_entity(iname, vdigest, unicodevalue,value=value, ticker=pre_ticker)
        
            # log.debug("Relating Activity '{} ({})' to input Entity '{}'".format(name, timestamp, input_uri))
            self.g.add((activity_uri, self.PROV['used'], input_uri))
            
            
        log.debug("names: {}".format(output_names))
        log.debug("outputs: {}".format(outputs))
           
        # For each output, create a 'generated' relation
        # Always expand tuples, to capture the variables separately.
        if isinstance(outputs, tuple) and len(outputs) == len(output_names):
            count = 0

            for value in outputs:
                
                unicodevalue, vdigest = self.get_value(value)
                
                # If we know the output names (captured e.g. by 'replace'), we can also use them to generate nice names
                # Otherwise we create a nameless output
                # print count
                if output_names != [] :
                    # log.debug("Generating entity for {}".format(output_names[count]))
                    output_uri = self.tick_and_add_entity(output_names[count],vdigest,unicodevalue, value=value, timestamp = ts)
                else :
                    output_uri = self.add_entity("{} output {}".format(name,count),vdigest,unicodevalue, value=value, timestamp = ts)
            
                # log.debug("Relating Activity '{} ({})' to output Entity '{}'".format(name, timestamp, output_uri))
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
                
                count += 1
        # Only expand dictionaries when explicitly told to do so
        elif expand_output_dict and isinstance(outputs,dict):
            for oname, value in outputs.items() :
                unicodevalue, vdigest = self.get_value(value)
                
                output_uri = self.tick_and_add_entity(oname, vdigest, unicodevalue, value=value, timestamp=ts)
                
                # log.debug("Relating Activity '{}' to output Entity '{}'".format(name, output_uri))
                self.g.add((activity_uri, self.PROV['generated'], output_uri))
        # Otherwise we'll take the value at 'face value'
        else :
            unicodevalue, vdigest = self.get_value(outputs)
            
            # If we know the output name (captured e.g. by 'replace'), we can also use them to generate nice names
            # Otherwise we create a nameless output
            if output_names != []:
                # log.debug("Generating entity for {}".format(output_names[0]))
                output_uri = self.tick_and_add_entity(output_names[0],vdigest,unicodevalue, value=outputs, timestamp=ts)
            else :
                output_uri = self.add_entity("{} output".format(name), vdigest, unicodevalue, value=outputs, timestamp=ts)
            
        
            # log.debug("Relating Activity '{} ({})' to output Entity '{}'".format(name, timestamp, output_uri))
            self.g.add((activity_uri, self.PROV['generated'], output_uri))
            
        # For each dependency, create a 'wasInformedBy' relation
        for dname, value in dependencies.items():
            unicodevalue, vdigest = self.get_value(value)

            dependency_uri = self.PROVOMATIC['id-'+vdigest]

            self.g.add((dependency_uri,RDF.type,self.PROV['Plan']))
            # self.g.add((dependency_uri,RDFS.label,Literal(dname)))
            self.g.add((dependency_uri,self.SKOS.note,Literal(unicodevalue)))

            self.g.add((activity_uri, self.PROV['wasInformedBy'], dependency_uri))
        
        return activity_uri


    def tick_and_add_entity(self, variable, digest, description, value=None, timestamp = None):
        # We increment the re-use of the variable by 1, and create a dependency
        if variable in self.variable_ticker:
            old_entity_uri = self.add_entity(variable, digest, description, value=value)
            
            self.tick(variable)
            
            entity_uri = self.add_entity(variable, digest, description, value=value, timestamp=timestamp)
            
            log.debug("Adding prov:wasDerivedFrom between {} and {}".format(entity_uri, old_entity_uri))
            self.g.add((entity_uri,self.PROV['wasDerivedFrom'],old_entity_uri))
        else :
            self.tick(variable)
            entity_uri = self.add_entity(variable, digest, description, value=value, timestamp=timestamp)
            
             
        return entity_uri
        
    def add_entity(self, name, digest, description, value=None, ticker=None, timestamp = None):
        # Make sure to use the old ticks, if provided.
        if ticker:
            try :
                # Get the pre-tick from the pre_ticker
                tick = ticker[name]
            except :
                # If the ticker does not contain the variable, just go the normal route
                tick = self.get_tick(name)
        else :
            tick = self.get_tick(name)
            
        log.debug("Adding {} ({})".format(name, tick))
        
        entity_uri = self.PROVOMATIC['{}/{}/{}'.format(name.replace(' ','_').replace('%','_'),tick,digest)]
    
        # log.debug("Adding Entity with label '{}' ({})".format(name,entity_uri))
        
        # log.debug("Adding tick to Entity name")
        # name = "{} ({})".format(name,tick)
    
        self.g.add((entity_uri,RDF.type,self.PROV['Entity']))
        self.g.add((entity_uri,RDFS.label,Literal(name)))
        self.g.add((entity_uri,self.SKOS['note'],Literal(description)))
        self.g.add((entity_uri,PROVOMATIC['tick'],Literal(tick)))
        
        if timestamp:
            self.g.add((entity_uri,PROV['wasGeneratedAtTime'],Literal(timestamp)))
        
        
        if not value is None or not isinstance(value, types.NoneType):
            # Add the actual value, with the appropriate datatype, if known.
            self.g.add((entity_uri,RDF.value,Literal(value)))
    
        return entity_uri
    

    
    def get_value(self, io):
        """We'll just use the __unicode__ representation as source for the hash digest"""
        
        
        value = get_decoded_value(io)
            
        
        vdigest = hashlib.md5(value.encode('utf-8')).hexdigest()

        if len(value) > 200:
            value = value[:99] + u"..." + value[-100:]
    
        return value, vdigest

    def get_graph(self):
        return self.g
        
    def set_graph(self, g):
        self.g = g
        return
        
    def now(self):
        return datetime.datetime.now()