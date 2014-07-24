#!/bin/bash
# -s (or --nocapture) prevents nose capturing output and thus
# doesn't stymie you when putting in pdb.set_trace() in tests

find . -name '*.pyc' -exec rm {} \;

../bin/pybot --outputdir results .

if [ $? -eq 1 ]
then
    exit 1
fi

# try to open the page in chrome, but if not present, don't complain
open results/report.html

