#!/bin/bash -x

USER=$1
DIST=0.6.0_linux_amd64.zip
DIRECTORY=packer

cd /home/$USER

if [ ! -d "$DIRECTORY" ]; then
    mkdir $DIRECTORY

    cd $DIRECTORY

    wget https://dl.bintray.com/mitchellh/packer/$DIST

    sudo apt-get install unzip

    sudo unzip $DIST

    sudo chown $USER:$USER *

    echo "export PATH=$PATH:/home/$USER/$DIRECTORY/" >> /home/$USER/.bashrc

    source /home/$USER/.bashrc
fi


