#!/bin/bash

cd "${0%/*}"
cd ..
cp ./*.adoc ./docs
asciidoctor ./docs/*.adoc