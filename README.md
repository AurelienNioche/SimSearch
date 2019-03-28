# SimSearch 1.0.0


Initially developed by Lars Yencken (https://github.com/larsyencken/simsearch).

## Dependencies

* Python2 

* Virtual env

        pip install virtualenv

* MongoDB

      brew install mongodb

 
## Configuration

* Ensure that a mongodb server is running
        
        brew services start mongodb

* Create a virtual environment

        virtualenv ss-env
 
 
* Execute the Makefile
 
        bash Makefile
 
* Compute similarity / nodes

        python -m simsearch.models
        

## Run

Run locally

        python simsearch.py

