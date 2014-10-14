# PROV-O-Matic
## Python Provenance Tracer

**Author:** Rinke Hoekstra, VU University Amsterdam, <mailto:rinke.hoekstra@vu.nl>/<mailto:hoekstra@uva.nl>

Provenance is key in improving the transparency of scientific data publishing. But most people use multiple very different systems to manipulate and analyse data. The goal of the [Data2Semantics](http://www.data2semantics) [COMMIT/](http://www.commit-nl.nl) project is to use the [W3C PROV Standard](http://www.w3.org/TR/prov-overview/), that we helped develop, to integrate provenance tracking within and across these systems. 

PROV-O-Matic is a library that integrates with the [IPython interpreter](http://ipython.org/), an interpreter that works with all Python programs, and in particular the [IPython Notebook](http://ipython.org/notebook.html) environment. IPython notebook is a popular data science environment, similar to R.

PROV-O-Matic does the following:

* It wraps Python functions and methods using a decorator, that builds an RDF PROV-O representation of the inputs and outputs of the respective function. The provenance trace is persistent within a Python session. And,
* it integrates provenance tracing in IPython Notebook, a tool frequently used by scientists for analysing data, and reporting on it. All functions defined in the notebook are automatically decorated, and all executions of steps in the notebook are recorded as well (including changing variable values). And
* it integrates a [PROV-O-Viz](http://provoviz.org) instance for interactive visualization of the provenance graph, and integrates it into IPython notebook.
* Existing provenance traces can be loaded into the notebook, and PROV entities can be *revived* as Python variables. Use and manipulation of these new variables, will build a provenance trace that connects to the previous trace.  

#### Credits

This work is supported by the Dutch national programme COMMIT/ under the Data2Semantics project. See <http://www.data2semantics.org> and <http://www.commit-nl.nl>

## Download

PROV-O-Matic can be downloaded from GitHub at: <https://github.com/Data2Semantics/prov-o-matic>

#### License

PROV-O-Matic is released under the MIT License. See LICENCE.txt for details.

## Installation 

To start, you will need `git`, `Python 2.7`, `pip` and `virtualenv` (MacOS users, please use [Homebrew](http://brew.sh/) to install a clean Python environment). 

Startup your favourite terminal environment (we'll be using forward slashes, sorry Windows users)

##### Cloning PROV-O-Matic

Do a *recursive* clone of the PROV-O-Matic git repository to a directory of your choice, e.g. `/example/provomatic`:

	git clone https://github.com/Data2Semantics/prov-o-matic.git /example/provomatic --recursive

This will create the `/example/provomatic` directory, if needed, and automatically checks out the latest version of PROV-O-Matic, and the git submodule for PROV-O-Viz. 

(Obviously, if you clone to a different directory every occurrence of `/example/provomatic` must be replaced with the proper path)

Enter the directory

	cd /example/provomatic	
	
##### Setup the Virtualenv environment

Initialize a virtual Python environment

	virtualenv .
	
Start your favourite text-editor and open the `activate-replacement` file in the `/example/provomatic` directory. Make the following changes.

**Step 1**:	Set the `VIRTUALENV` variable to point to the root directory of the provomatic installation. In our case, replace the line 

	VIRTUAL_ENV="/absolute/path/to/your/provomatic/clone/directory"
	
with

	VIRTUAL_ENV="/example/provomatic/" 

**Step 2**:	Set the `PYTHONPATH` variable to also point to the `lib/provoviz` directory in the directory of the provomatic installation. In our case, replace the line

	PYTHONPATH="$PYTHONPATH:/absolute/path/to/your/provomatic/clone/directory/lib/provoviz/src"
	
with

	PYTHONPATH="$PYTHONPATH:/example/provomatic/lib/provoviz/src"
	
Save the file, and overwrite the `bin/activate` file with the edited `activate-replacement` file:

	cp activate-replacement bin/activate
	
You can now safely activate the virtual environment:

	source bin/activate
	
##### Install the Necessary Libraries

The `requirements.txt` file lists all required libraries. Use 

	pip -r requirements.txt

from your activated virtualenv to install the dependencies.

The full list of requirements is as follows:

	Jinja2==2.7.3
	MarkupSafe==0.23
	SPARQLWrapper==1.6.4
	backports.ssl-match-hostname==3.4.0.2
	certifi==14.05.14
	chardet==2.3.0
	decorator==3.4.0
	gnureadline==6.3.3
	html5lib==0.999
	ipython==2.3.0
	isodate==0.5.0
	networkx==1.9.1
	numpy==1.9.0
	pandas==0.14.1
	pyparsing==1.5.7
	python-dateutil==2.2
	pytz==2014.7
	pyzmq==14.3.1
	rdfextras==0.4
	rdflib==4.1.2
	requests==2.4.3
	six==1.8.0
	tornado==4.0.2
	wsgiref==0.1.2

##### Ready to go! 

You can now start the IPython notebook by entering the `src` directory

	cd src
	
and running 

	ipython notebook
	
This should open your browser at the address `http://127.0.0.1:8888/tree

Open the `PROV-O-Matic Examples` notebook and follow the instructions. This should give you enough information to use PROV-O-Matic in your own notebooks.

Have fun!


