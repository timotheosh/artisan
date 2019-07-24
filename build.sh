#!/bin/bash

rm -rf target
mkdir target
cd target
nuitka3 ../artisan.py -o artisan
cd ..
