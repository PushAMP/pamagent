#!/bin/bash
set -e -x
ls -lha /io
ls -lha /
# Install rust nightly
mkdir ~/rust-installer
curl -sL https://static.rust-lang.org/rustup.sh -o ~/rust-installer/rustup.sh
sh ~/rust-installer/rustup.sh --prefix=~/rust --spec=nightly -y --disable-sudo

export PATH="$HOME/rust/bin:$PATH"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/rust/lib"
export OPENSSL_LIB_DIR=/usr/local/lib64
export OPENSSL_INCLUDE_DIR=/usr/local/include

# Compile wheels
for PYBIN in /opt/python/cp{35,36}*/bin; do
    export PYTHON_LIB=$(${PYBIN}/python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
    export LIBRARY_PATH="$LIBRARY_PATH:$PYTHON_LIB"
    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$PYTHON_LIB"
    "${PYBIN}/pip" install -U  setuptools setuptools-rust wheel
    "${PYBIN}/pip" wheel /io -w wheelhouse/
done
ls -lha /io
# Remove universal wheels
rm -rf /io/dist/semantic_version*whl
rm -rf /io/dist/setuptools_rust*whl

ls -lha /io/dist/
find /io/dist/*.whl

# Bundle external shared libraries into the wheels
find /io/dist/*.whl | xargs -I NAME auditwheel repair NAME -w /io/wheelhouse/

# Install packages and test
for PYBIN in /opt/python/cp{35,36}*/bin/; do
    "${PYBIN}/pip" install pamagent --no-index -f /io/wheelhouse/
done