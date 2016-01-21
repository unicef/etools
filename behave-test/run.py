from subprocess import Popen

from config import *
from datetime import datetime

import os
import argparse

parser = argparse.ArgumentParser(prog='BEHAVE TEST', description='Run Behave test')
parser.add_argument('--report', default='reports', help='define the report dir')
parser.add_argument('--screenshot', default='screenshots', help='define the screenshot dir')
parser.add_argument('--version', action='version', version='%(prog)s 1.0')

args = parser.parse_args()

basedir = args.report + '/'
basedir_shots = args.screenshot + '/'

current = datetime.now().strftime('%Y-%m-%d')
report_dir = basedir + current
report_dir_error = report_dir + '/errors'
report_txt = report_dir + '/result.txt'

if not os.path.exists(report_dir):
    os.chmod(basedir, 0777)
    os.makedirs(report_dir)
    os.chmod(report_dir, 0777)

if not os.path.exists(report_dir_error):
    os.makedirs(report_dir_error)

screenshot_dir = basedir_shots + current

if not os.path.exists(screenshot_dir):
    os.chmod(basedir_shots, 0777)
    os.makedirs(screenshot_dir)

update_config('report_dir', report_dir)
update_config('report_dir_errors', report_dir_error)
update_config('screenshot_dir', screenshot_dir)

Popen(['behave', '--outfile', report_txt])
# Popen(['rst2pdf', report_txt, reportPdf])
