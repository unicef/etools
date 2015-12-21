#!/bin/bash
# depends on node and npm being installed
# sudo apt-get install nodejs
# sudo apt-get install npm
npm install

echo "npm packages installed"
# depends on bower being installed
# npm install -g bower
bower install

echo "bower packages installed"

gulp

echo "distribution was built in /dist/"