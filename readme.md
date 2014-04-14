# PROV-O-Matic
### Python Provenance Tracer

Provenance is key in improving the transparency of scientific data publishing. 

PROV-O-Matic provides three things:

* a **decorator** for functions and methods that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values). And
* it connects to [PROV-O-Viz](http://provoviz.org) for interactive visualization of the provenance graph, and integrates it into IPython notebook.

### Requirements

* RDFLib >= v4.2-dev
* IPython >= 2.0.0-dev
* A local PROV-O-Viz running on port 5000
* A simple HTTPServer running from the same directory the root of the PROV-O-Matic source tree.

This is all still quite experimental. You're probably safest off if you set everything up in a separate virtualenv, running PROV-O-Matic directly from the source distribution.

### Usage

Load the IPython extension in the usual way (provided that `provomatic.extension` is in your python path), by typing the following in your IPython Notebook:

```%load_ext provomatic.extension```

The visualization connection expects a HTTP server to be running on port 8000 with the current working directory as document root.

Provenance tracking is automatic once you load the extension.

You can visualize using [PROV-O-Viz](http://provoviz.org) by calling `view_prov()`

### Credits

This work is supported by the Dutch national programme COMMIT/ under the Data2Semantics project. See <http://www.data2semantics.org> and <http://www.commit-nl.nl>
