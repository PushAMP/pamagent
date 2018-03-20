import os
import sys

import pip
from setuptools import setup
from setuptools.command.test import test as TestCommand


THIS_DIR = os.path.dirname(os.path.realpath(__name__))


def read(*parts):
    with open(os.path.join(THIS_DIR, *parts)) as f:
        return f.read()


try:
    from setuptools_rust import Binding, RustExtension
except ImportError:
    status = pip.main(['install', 'setuptools-rust'])
    if status != 0:
        print("Please install setuptools-rust package")
        raise SystemExit(status)
    else:
        from setuptools_rust import Binding, RustExtension


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
    version='0.2.5',
    author='PushAMP LLC',
    author_email='devcore@pushamp.com',
    description='Agent for PAM',
    license='MIT',
    python_requires='>=3.5',
    keywords=['pam', 'rust', 'profiling', 'performance'],
    url='https://github.com/pushamp/pamagent',
    tests_require=['tox', 'django', 'requests'],
    setup_requires=['setuptools-rust'],
    cmdclass={
        'test': Tox,
    },
    platforms='Posix; MacOS X; Windows',
    rust_extensions=[RustExtension('pamagent.pamagent_core', 'pamcore/Cargo.toml', binding=Binding.PyO3)],
    packages=['pamagent', 'pamagent.hooks', 'pamagent.utils'],
    install_requires=read('requirements.txt').splitlines(),
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        ]
)
