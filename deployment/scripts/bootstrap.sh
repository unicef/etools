#!/bin/bash -x

set -e

sudo echo deb http://us.archive.ubuntu.com/ubuntu/ precise main restricted universe multiverse > /etc/apt/sources.list
sudo echo deb http://us.archive.ubuntu.com/ubuntu/ precise-security main restricted universe multiverse >> /etc/apt/sources.list
sudo echo deb http://us.archive.ubuntu.com/ubuntu/ precise-updates main restricted universe multiverse >> /etc/apt/sources.list

# Updating and Upgrading dependencies
sudo apt-get update -y -qq > /dev/null
sudo apt-get upgrade -y -qq > /dev/null

# Install necessary libraries for guest additions and Vagrant NFS Share
sudo apt-get -y -q install linux-headers-$(uname -r) build-essential dkms nfs-common

# Install necessary dependencies
sudo apt-get install -y sudo python-dev python-apt python-pycurl python-pip python-virtualenv
sudo pip install -U ansible==1.4.5

