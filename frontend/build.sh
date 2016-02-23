#!/bin/bash

npm install

bower install --allow-root --config.interactive=false

gulp buildFront:partner
gulp buildFront:management