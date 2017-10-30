#!/bin/sh

# this file must have unix newlines (to prevent extraneous errors when running)
# must run sudo on ubuntu

PYTHON=python3.2

# create version with date and a shell file to name output with the date
${PYTHON} buildVersion.py

BUILT64=exe.solaris-2.10-sun4v.64bit-3.2

if [ -d build/${BUILT64} ]
  then
    rm -fR build/${BUILT64}
fi
mkdir build/${BUILT64}

if [ ! -d dist ]
  then
    mkdir dist
fi

# run cx_Freeze setup
${PYTHON} setup.py build
cp arelle/scripts-unix/* build/${BUILT64}

cd build/${BUILT64}

# for now there's no tkinter on solaris sun4 (intended for server only)
# rm arelleGUI

# add missing libraries
cp /usr/local/lib/sparcv9/libintl* .

tar -cf ../../dist/${BUILT64}.tar .
gzip ../../dist/${BUILT64}.tar
cd ../..

# add arelle into SEC XBRL.JAR
cd build
mv ${BUILT64} arelle
cp /export/home/slee/Documents/vm-files/XBRL.JAR ../dist
jar uf ../dist/XBRL.JAR arelle
mv arelle ${BUILT64}
cd ..

/bin/sh buildRenameSol10Sun4.sh
# rm -R build2
