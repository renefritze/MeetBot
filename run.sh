#!/bin/bash
cd $(dirname $0)

while [ 1 ] ; do
nice ./main.py
sleep 1
done
