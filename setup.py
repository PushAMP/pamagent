import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

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
    version='0.1.2',
    author='PushAMP LLC',
    author_email='devcore@pushamp.com',
    description=('Agent for PAM'),
    license='MIT',
    keywords=['pam', 'rust', 'profiling', 'performance'],
    url='https://github.com/pushamp/pamagent',
    tests_require=['tox', 'django', 'requests'],
    cmdclass={
        'test': Tox,
    },
    rust_extensions=[RustExtension('pamagent.pamagent_core', 'pamcore/Cargo.toml', binding=Binding.PyO3)],
    packages=['pamagent', 'pamagent.hooks'],
    install_requires=[
        "wrapt==1.10.10",
    ],
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        ]
)
