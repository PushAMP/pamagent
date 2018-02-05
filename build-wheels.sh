#!/bin/bash
set -e -x
## Install rust nightly
#mkdir ~/rust-installer
#curl -sL https://static.rust-lang.org/rustup.sh -o ~/rust-installer/rustup.sh
#sh ~/rust-installer/rustup.sh --prefix=~/rust --spec=nightly -y --disable-sudo
#
#export PATH="$HOME/rust/bin:$PATH"
#export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/rust/lib"

# Compile wheels
for PYBIN in /opt/python/cp{35,36}*/bin; do
    export PYTHON_LIB=$(${PYBIN}/python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
    export LIBRARY_PATH="$LIBRARY_PATH:$PYTHON_LIB"
    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$PYTHON_LIB"
    "${PYBIN}/pip" install -U  setuptools setuptools-rust wheel
    "${PYBIN}/pip" wheel /io -w /io/dist/
done

# Remove universal wheels
rm -rf /io/dist/semantic_version*whl
rm -rf /io/dist/setuptools_rust*whl

find /io/dist/*.whl

# Bundle external shared libraries into the wheels
find /io/dist/*.whl | xargs -I NAME auditwheel repair NAME -w /io/wheelhouse/

# Install packages and test
for PYBIN in /opt/python/cp{35,36}*/bin/; do
    "${PYBIN}/pip" install pamagent --no-index -f /io/wheelhouse/
done