#!/bin/bash

for dirname in cbeta_epub_2021q2/*
do
	if [[ -d $dirname ]]
	then
		output_dirname=cbeta/$(basename $dirname)
		mkdir -p $output_dirname
		for fn in $dirname/*.epub
		do
			basename=$(basename $fn)
			pref=${basename%.*}
			unzip $fn "OEBPS/juans/*" -d $output_dirname
			mkdir -p $output_dirname/$pref
			mv $output_dirname/OEBPS/juans/* $output_dirname/$pref
		done
		rm -r $output_dirname/OEBPS
	fi
done
	
	
