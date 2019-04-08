# SimSearch 1.0.0


Initially developed by Lars Yencken (https://github.com/larsyencken/simsearch).

## Dependencies

* Python3
        
        brew install python3 

* Virtualenv

        pip3 install virtualenv

* MongoDB

      brew install mongodb

 
## Configuration

* Ensure that a mongodb server is running
        
        brew services start mongodb

        
* Create and activate virtual environment [Inside project folder] 
        
        cd SimSearch
        virtualenv -p python3 env 
        source env/bin/activate
        
* Install Cython for the virtualenv Python

        pip install cython
        
* Execute the Makefile (create virtual environment if not already existing, install dependencies, create models) [Inside project folder] 
 
        make
        

## Run

Run locally [Inside project folder and after activation of the virtual environment]

        python simsearch.py
        
        
## Various

To have launchd start mongodb now and restart at login:
    
    brew services start mongodb
Or, if you don't want/need a background service you can just run:

    mongod --config /usr/local/etc/mongod.conf

