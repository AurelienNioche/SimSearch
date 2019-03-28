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
 
 
* Execute the Makefile (create virtual environment, install dependencies, create models) [Inside project folder] 
 
        make
        
* Active virtual environment [Inside project folder] 

        source env/bin/activate
        

## Run

Run locally [Inside project folder and after activation of the virtual environment]

        python simsearch.py

