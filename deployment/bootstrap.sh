#!/bin/bash -x

set -e

# Updating and Upgrading dependencies
sudo apt-get update -y -qq > /dev/null
sudo apt-get upgrade -y -qq > /dev/null

# Install necessary libraries for guest additions and Vagrant NFS Share
sudo apt-get -y -q install linux-headers-$(uname -r) build-essential dkms nfs-common

# Install necessary dependencies
sudo apt-get install -y sudo python-dev python-apt python-pycurl python-pip python-virtualenv
sudo pip install -U ansible==1.4.5

