from setuptools import setup


def readme():
  with open('README.md', 'r') as f:
    return f.read()


setup(
  name='bot4',
  version='0.0.6',
  author='Jeelesk',
  author_email='eywevynriimnetyiu@gmail.com',
  description='This is a module for creating bots',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/Jeelesk/bot4',
  packages=['bot4', 'bot4.net', 'bot4.protocol', 'bot4.types', 'bot4.versions'],
  package_data = {'bot4': ['versions/*.json', 'versions/version_protocols', 'types/buffer/*']},
  install_requires=['bitstring >= 3.1.0', 'cryptography >= 0.9'],
  classifiers=[
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent'
  ],
  project_urls={},
  python_requires='>=3.10'
)