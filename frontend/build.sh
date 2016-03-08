#!/bin/bash

npm prune && npm install --production

bower install --allow-root --config.interactive=false

gulp buildFront:partner
gulp buildFront:management