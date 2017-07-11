from setuptools import setup

from rust_setuptools import build_rust_cmdclass, install_lib_including_rust, develop_including_rust


setup(
    name='pamagent',
    version='0.0.1',
    author='PushAMP LLC',
    author_email='devcore@pushamp.com',
    description=('Agent for PAM'),
    license='MIT',
    keywords=['pam', 'rust', 'profiling', 'performance'],
    url='https://github.com/pushamp/pamagent',
    tests_require=['pytest'],
    cmdclass={
        # This enables 'setup.py build_rust', and makes it run
        # 'cargo extensions/cargo.toml' before building your package.
        'build_rust': build_rust_cmdclass('pamcore/Cargo.toml', ext_name="pamagent.pamagent_core"),
        # This causes your rust binary to be automatically installed
        # with the package when install_lib runs (including when you
        # run 'setup.py install'.
        'install_lib': install_lib_including_rust,
        # This supports development mode for your rust extension by
        # causing the ext to be built in-place, according to its ext_name
        'develop': develop_including_rust
    },
    packages=['pamagent'],
    install_requires=[
        "wrapt==1.10.10",
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        ]
)
