# PROV-O-Matic
### Python Provenance Tracer

**Author:** Rinke Hoekstra, VU University Amsterdam, <rinke.hoekstra@vu.nl>

Provenance is key in improving the transparency of scientific data publishing. But most people use multiple very different systems to manipulate and analyse data. The goal of the [Data2Semantics](http://www.data2semantics) [COMMIT/](http://www.commit-nl.nl) project is to use the [W3C PROV Standard](http://www.w3.org/TR/prov-overview/), that we helped develop, to integrate provenance tracking within and across these systems. 

PROV-O-Matic is a library that integrates with the [IPython interpreter](http://ipython.org/), an interpreter that works with all Python programs, and in particular the [IPython Notebook](http://ipython.org/notebook.html) environment. IPython notebook is a popular data science environment, similar to R.

PROV-O-Matic does three things:

* It wraps Python functions and methods using a decorator, that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values). And
* it integrates a [PROV-O-Viz](http://provoviz.org) instance for interactive visualization of the provenance graph, and integrates it into IPython notebook.
* Existing provenance traces can be loaded into the notebook, and PROV entities can be *revived* as Python variables. Use and manipulation of these new variables, will build a provenance trace that connects to the previous trace.  

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
