# Prov-O-Matic
### Python Provenance Tracer

Provenance is key in improving the transparency of scientific data publishing. 

Prov-O-Matic provides three things:

* a **decorator** for functions and methods that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values).
* it connects to Prov-O-Viz for interactive visualization of the provenance graph, and integrates it into IPython notebook.

### Requirements

* RDFLib >= v4.2-dev
* IPython >= 2.0.0-dev
* A local PROV-O-Viz running on port 5000

### Usage

Load the extension in the usual way (provided that `provomatic.extension` is in your python path):

```%load_ext provomatic.extension```

The visualization connection expects a HTTP server to be running on port 8000 with the current working directory as document root.