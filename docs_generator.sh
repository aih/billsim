#!/bin/bash

cd "${0%/*}"
cp ./*.adoc ./docs
asciidoctor ./docs/*.adoc
