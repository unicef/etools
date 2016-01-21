from subprocess import Popen
from config import *
from datetime import datetime
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

import os
import argparse
import smtplib
import subprocess


def create_dirs(args):
    basedir = args.report + '/'
    basedir_shots = args.screenshot + '/'

    current = datetime.now().strftime('%Y-%m-%d')
    report_dir = basedir + current
    report_dir_error = report_dir + '/errors'

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


def run_test(feature):

    report_txt = read_config('report_dir') + '/result.txt'
    if not feature:
        print 'all features'
        # Popen(['behave', '--outfile', report_txt])
        returncode = subprocess.call(['behave', '--outfile', report_txt])
    else:
        feature = 'features/' + feature + '.feature'
        print feature
        #Popen(['behave', '--outfile', report_txt, feature])
        returncode = subprocess.call(['behave', '--outfile', report_txt, feature])

    return returncode


def generate_report_pdf():
    report_txt = read_config('report_dir') + '/result.txt'
    report_pdf = read_config('report_dir') + '/result.pdf'
    Popen(['rst2pdf', report_txt, report_pdf])


def send_mail(files=None,
              server="localhost"):
    send_to = read_config('send_report_to')
    send_from = read_config('send_report_from')
    subject = read_config('send_report_subject')
    text = read_config('send_report_text')

    msg = MIMEMultipart(
        From=send_from,
        To=COMMASPACE.join(send_to),
        Date=formatdate(localtime=True),
        Subject=subject
    )
    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            msg.attach(MIMEApplication(
                fil.read(),
                Content_Disposition='attachment; filename="%s"' % basename(f),
                Name=basename(f)
            ))

    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


parser = argparse.ArgumentParser(prog='BEHAVE TEST', description='Run Behave test')
parser.add_argument('-rt', '--report', default='reports', help='define the report dir')
parser.add_argument('-sh', '--screenshot', default='screenshots', help='define the screenshot dir')
parser.add_argument('-ft', '--feature', default='', help='define a specific feature to test')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.1')
args = parser.parse_args()


create_dirs(args)
run_test(args.feature)
generate_report_pdf()
send_mail()

