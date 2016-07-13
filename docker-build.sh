#!/bin/bash


pip wheel -r requirements.txt;
rm -rf frontend;

if [ $CIRCLE_BRANCH != "develop" ] && [ $CIRCLE_BRANCH != "staging" ] && [ $CIRCLE_BRANCH != "master" ]; then
        CIRCLE_BRANCH="develop";
fi;


git clone -b $CIRCLE_BRANCH https://github.com/unicef/etools-partner-portal.git frontend;
cp -ar /node_modules frontend/node_modules;

cd frontend; ./build.sh;

cp -ar node_modules /node_modules;

cd ../frontend_build; ./build.sh;