#!/usr/bin/env python3

################################################################
#
# release-grq.py - Semi-automatically add new GovReady-Q release
#   to Govready.com/download/govready
#
# requirements:
#   python3 -m venv venv
#   source venv/bin/activate
#   python -m pip install --upgrade pip
#   pip install requests
#
# Usage: release-grq.py [--help] [--non-interactive] [--verbose]
#
# Optional arguments:
#   -h, --help             show this help message and exit
#   -n, --non-interactive  run without terminal interaction
#   -t, --timeout          seconds to allow external programs to run
#   -u, --user             do pip install with --user flag
#   -v, --verbose          output more information
#
################################################################

# Note: we use print("foo") ; sys.stdout.flush() instead of print("", flush=True)
# to avoid a syntax error crash if run under Python 2.

# parse command-line arguments
import argparse

# system stuff
import os
import requests
import platform
import re
import signal
import subprocess
import sys
import time
import json
from subprocess import PIPE

# JSON handling
import json

# Default constants
DIRECTORY = "/tmp/release"
RELEASE_INFO = "https://api.github.com/repos/govready/govready-q/releases/latest"
RELEASE_TAG_URL = "https://github.com/GovReady/govready-q/archive/refs/tags/"
SPACER = "\n====\n"

# Gracefully exit on control-C
signal.signal(signal.SIGINT, lambda signal_number, current_stack_frame: sys.exit(0))

# Define a fatal error handler
class FatalError(Exception):
    pass

# Define a halted error handler
class HaltedError(Exception):
    pass

# Define a non-zero return code error handler
class ReturncodeNonZeroError(Exception):
    def __init__(self, completed_process, msg=None):
        if msg is None:
            # default message if none set
            msg = "An external program or script returned an error."
        super(ReturncodeNonZeroError, self).__init__(msg)
        self.completed_process = completed_process

# Set up argparse
def init_argparse():
    parser = argparse.ArgumentParser(description='Quickly set up a new GovReady-Q instance from a freshly-cloned repository.')
    parser.add_argument('--non-interactive', '-n', action='store_true', help='run without terminal interaction')
    parser.add_argument('--timeout', '-t', type=int, default=120, help='seconds to allow external programs to run (default=120)')
    parser.add_argument('--user', '-u', action='store_true', help='do pip install with --user flag')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='output more information')
    parser.add_argument('--docker', '-d', action='store_true', help='runs with docker installation')
    return parser

################################################################
#
# helpers
#
################################################################

def run_optionally_verbose(args, timeout, verbose_flag):
    if verbose_flag:
        import time
        start = time.time()
        p = subprocess.run(args, timeout=timeout)
        print("Elapsed time: {:1f} seconds.".format(time.time() - start))
    else:
        p = subprocess.run(args, timeout=timeout, stdout=PIPE, stderr=PIPE)
    return p

def check_has_command(command_array):
    try:
        # hardcode timeout to 5 seconds; if checking command takes longer than that, something is really wrong
        p = subprocess.run(command_array, timeout=5, stdout=PIPE, stderr=PIPE)
        return True
    except FileNotFoundError as err:
        return False

# checks if a package is out of date
# if okay, returns (True, None, None)
# if out of date, returns (False, current_version, latest_version)
# N.B., this routine will return okay if the package is not installed
def check_package_version(package_name):
    p = subprocess.run([sys.executable, '-m', 'pip', 'list', '--outdated', '--format', 'json'], stdout=PIPE, stderr=PIPE)
    packages = json.loads(p.stdout.decode('utf-8'))
    for package in packages:
        if package['name'] == package_name:
            return False, package['version'], package['latest_version']
    return True, None, None

def download(url):
    """Download release file"""

    filename = "govready-q-" + url.split('/')[-1].replace(" ", "_")  # be careful with file names
    downloaded_obj = requests.get(url)
    with open(filename, "wb") as file:
        file.write(downloaded_obj.content)
    result = filename

    return result

def main():
    print(">>>>>>>>>> Welcome to the GovReady-Q Release Publisher Assistant <<<<<<<<<\n")

    try:
        # Collect command line arguments, print help if necessary
        argparser = init_argparse();
        args = argparser.parse_args();

        # Get most recent release
        r = requests.get(RELEASE_INFO)
        if r.status_code == 200:
            release_info = r.json()
            from pprint import pprint
        else:
            print('An error occurred while attempting to retrieve data from the API.')

        # print(release_info.keys())
        print("release_info.html_url", release_info['html_url'])
        print(SPACER)

        release_name = release_info['html_url'].split('/')[-1]
        print(f'Getting release {release_name}')


        for ext in ['.zip', '.tar.gz']:
            # Download zip version
            url = RELEASE_TAG_URL + release_name + ext
            print(f'downloading {url}')
            file = download(url)
            print(f'Downloaded {file}')

            # Get file size
            size = os.path.getsize(file)
            print(f"... filesize is {size}.")

            # Get checksum
            print("Get checksum")
            if args.user:
                get_checksum = ['shasum', '-a', '256', '--user', file]
            else:
                get_checksum = ['shasum', '-a', '256', file]

            p = run_optionally_verbose(get_checksum, args.timeout, args.verbose)
            if p.returncode != 0:
                raise ReturncodeNonZeroError(p)
            # print(p.stdout)
            checksum = p.stdout.decode(encoding='UTF-8').split(" ")[0]
            print(f'checksum is {checksum}')
            sys.stdout.flush()

            html_block = f"""
            <tr>
              <td class="release">{release_name}</td>
              <td><a href="govready-q-{release_name}{ext}">govready-q-{release_name}{ext}</a></td>
              <td>{checksum}</td>
              <td>{size} MB</td>
            </tr>
            """

            print(html_block)

            # Print spacer
            print(SPACER)

            # <!--0.9.2.1-->
            # <tr>
            #   <td class="release">0.9.2.1</td>
            #   <td><a href="govready-q-0.9.2.1.tar.gz">govready-q-0.9.2.1.tar.gz</a></td>
            #   <td>03af2aaa2d9478b3834e263e1c77cd6fcb9ed473beecb235a9e486a1018565b5</td>
            #   <td>5.5 MB</td>
            # </tr>
            # <tr>
            #   <td class="">&nbsp;</td>
            #   <td><a href="govready-q-0.9.2.1.zip">govready-q-0.9.2.1.zip</a></td>
            #   <td>c37266b5e897600f2a98f66c607e13e9a4cddc45bef49eb8d4f64ea61a323764</td>
            #   <td>5.9 MB</td>
            # </tr>


    except ReturncodeNonZeroError as err:
        p = err.completed_process
        sys.stderr.write("\n\nFatal error, exiting: external program or script {} returned error code {}.\n\n".format(p.args, p.returncode))
        # diagnose stdout and stdout to see if we can find an obvious problem
        # (add more checks here as appropriate)
        # check for missing Xcode Command Line Tools (macOS)
        if p.stderr and 'xcrun: error: invalid active developer path (/Library/Developer/CommandLineTools), missing xcrun at: /Library/Developer/CommandLineTools/usr/bin/xcrun' in p.stderr.decode('utf-8'):
            sys.stderr.write("Suggested fix (see documentation): You need to do 'xcode-select --install'.\n\n")
        sys.exit(1)

    except subprocess.TimeoutExpired as err:
        sys.stderr.write("\n\nFatal error, exiting: external program or script {} took longer than {:.1f} seconds.\n\n".format(err.cmd, err.timeout))
        sys.stderr.write("Suggested fix: run again with '--timeout {}'.\n\n".format(max(args.timeout+120, 600)))
        sys.exit(1)

    except HaltedError as err:
        sys.stderr.write("\n\nInstall halted because: {}.\n\n".format(err));
        sys.exit(1)

    except FatalError as err:
        sys.stderr.write("\n\nFatal error, exiting: {}.\n\n".format(err));
        sys.exit(1)

    # catch all errors
    except Exception as err:
        sys.stderr.write('\n\nFatal error, exiting: unrecognized error on line {}, "{}".\n\n'.format(sys.exc_info()[2].tb_lineno, err));
        sys.exit(1)

if __name__ == "__main__":
    exit(main())
