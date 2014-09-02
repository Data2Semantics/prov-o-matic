# PROV-O-Matic
### Python Provenance Tracer
** Author: ** Rinke Hoekstra, VU University Amsterdam, <rinke.hoekstra@vu.nl>

Provenance is key in improving the transparency of scientific data publishing. 

PROV-O-Matic provides three things:

* a **decorator** for functions and methods that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values). And
* it connects to [PROV-O-Viz](http://provoviz.org) for interactive visualization of the provenance graph, and integrates it into IPython notebook.

### Requirements

* RDFLib >= v4.2-dev
* IPython >= 2.0.0-dev
* An internet connection (for connecting to http://provoviz.org/service), or a locally running PROV-O-Viz service.

This is all still quite experimental. You're probably safest off if you set everything up in a separate virtualenv, running PROV-O-Matic directly from the source distribution.

### Usage

Start an IPython notebook from inside the `src` directory of the PROV-O-Matic source distribution.

Load the IPython extension in the usual way (provided that `provomatic.extension` is in your python path), by typing the following in your IPython Notebook:

```%load_ext provomatic.extension```

Provenance tracking is automatic once you load the extension.

You can visualize using [PROV-O-Viz](http://provoviz.org) by calling `view_prov()`

If you want to connect to a locally running PROV-O-Viz service, you can set its URL using `set_provoviz_url()`. 

### Credits

This work is supported by the Dutch national programme COMMIT/ under the Data2Semantics project. See <http://www.data2semantics.org> and <http://www.commit-nl.nl>

### License

See LICENCE.txt
