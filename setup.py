import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

from rust_setuptools import build_rust_cmdclass, install_lib_including_rust, develop_including_rust


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        errno = tox.cmdline(args=args)
        sys.exit(errno)


setup(
    name='pamagent',
    version='0.1.1',
    author='PushAMP LLC',
    author_email='devcore@pushamp.com',
    description=('Agent for PAM'),
    license='MIT',
    keywords=['pam', 'rust', 'profiling', 'performance'],
    url='https://github.com/pushamp/pamagent',
    tests_require=['tox', 'django', 'requests'],
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
        'develop': develop_including_rust,
        'test': Tox,
    },
    packages=['pamagent', 'pamagent.hooks'],
    install_requires=[
        "wrapt==1.10.10",
    ],
    zip_safe=False,
    package_data={'': ['rust_setuptools.py']},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        ]
)
