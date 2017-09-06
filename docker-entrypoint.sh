#!/bin/sh

#the default wkhtml on DEBIAN doesn't have the QT patches, we need to overwrite the binary with a precompiled one
cd ./bin
tar -xJf wkhtmltox-0.12.4_linux-generic-amd64.tar.xz
cd wkhtmltox/
chown root:root bin/wkhtmltopdf
cp -r * /usr/
