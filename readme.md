# Prov-O-Matic
### Python Provenance Tracer

Provenance is key in improving the transparency of scientific data publishing. 

Prov-O-Matic provides three things:

* a **decorator** for functions and methods that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values).
* it connects to Prov-O-Viz for interactive visualization of the provenance graph, and integrates it into IPython notebook.
