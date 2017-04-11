"""setup.py"""
import os

from setuptools import setup
from pip.req import parse_requirements
from pip.download import PipSession
from optparse import Option

BASEDIR = os.path.dirname(os.path.abspath(__file__))


def parse_reqs(reqs_file):
    ''' parse the requirements '''
    options = Option("--workaround")
    options.skip_requirements_regex = None
    options.isolated_mode = True
    install_reqs = parse_requirements(reqs_file, options=options, session=PipSession())
    return [str(ir.req) for ir in install_reqs]


REQS = parse_reqs(os.path.join(BASEDIR, "requirements.txt"))

EXTRA_REQS_PREFIX = 'requirements_'
EXTRA_REQS = {}
for file_name in os.listdir(BASEDIR):
    if not file_name.startswith(EXTRA_REQS_PREFIX):
        continue
    base_name = os.path.basename(file_name)
    (extra, _) = os.path.splitext(base_name)
    extra = extra[len(EXTRA_REQS_PREFIX):]
    EXTRA_REQS[extra] = parse_reqs(file_name)

exec(open('job_manager_service/version.py').read())
setup(name="job_manager_service",
      version=VERSION,
      description="Service in charge of allocating renderers for Visualization WebServices",

      packages=['job_manager_service',
                'job_manager_service/admin',
                'job_manager_service/config',
                'job_manager_service/config/management',
                'job_manager_service/service',
                'job_manager_service/session',
                'job_manager_service/session/management',
                'job_manager_service/utils'],
      url='https://github.com/bluebrain/RenderingResourceManager.git',
      author='Cyrille Favreau',
      author_email='cyrille.favreau@epfl.ch',
      license='GNU LGPL',
      install_requires=REQS,
      extras_require=EXTRA_REQS,)
