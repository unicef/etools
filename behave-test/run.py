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

    set_config('report_dir', report_dir)
    set_config('report_dir_errors', report_dir_error)
    set_config('screenshot_dir', screenshot_dir)
    set_config('driver', args.driver.lower())


def run_test(feature, tags):

    report_txt = read_config('report_dir') + '/result.txt'
    if not feature:
        print 'all features, tags: ' + tags
        # Popen(['behave', '--outfile', report_txt, '--tags', tags])
        returncode = subprocess.call(['behave', '--outfile', report_txt, '--tags', tags])
    else:
        feature = 'features/' + feature + '.feature'
        print feature + ', tags: ' + tags
        #Popen(['behave', '--outfile', report_txt, feature, '--tags', tags])
        returncode = subprocess.call(['behave', '--outfile', report_txt, feature, '--tags', tags])

    return returncode


def generate_report_pdf():
    report_txt = read_config('report_dir') + '/result.txt'
    report_pdf = read_config('report_dir') + '/result.pdf'
    Popen(['rst2pdf', report_txt, report_pdf])
    return report_pdf

def send_mail(files=None):
    send_to = read_config('default_send_report_to')
    send_from = read_config('default_send_report_from')
    subject = read_config('default_send_report_subject')
    text = read_config('default_send_report_text')

    print 'send test result to: ' + send_to

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

    smtp = smtplib.SMTP('localhost', 25)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


parser = argparse.ArgumentParser(prog='BEHAVE TEST', description='Run Behave test')
parser.add_argument('-rt', '--report', default=read_config('default_report_dir'),
                    help='define the report dir')
parser.add_argument('-sh', '--screenshot', default=read_config('default_screenshot_dir'),
                    help='define the screenshot dir')
parser.add_argument('-ft', '--feature', default='',
                    help='define a specific feature to test')
parser.add_argument('-t', '--tags', default=read_config('default_tags'),
                    help='define a specific tags to test (@tag1,@tag2)')
parser.add_argument('-d', '--driver', default=read_config('default_driver'),
                    help='define a specific feature to test (firefox chrome)')
parser.add_argument('-sr', '--sendreport', default=read_config('default_send_report'),
                    help='send test result by email')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.1')
args = parser.parse_args()

create_dirs(args)
run_test(args.feature, args.tags)

if args.sendreport == '1':
    report = generate_report_pdf()
    send_mail([report])

remove_config('report_dir')
remove_config('report_dir_errors')
remove_config('screenshot_dir')
remove_config('driver')

