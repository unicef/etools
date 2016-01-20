from datetime import datetime

import os

from subprocess import Popen

basedir = 'reports/'
current = datetime.now().strftime('%Y-%m-%d')
dirReport = basedir + current
reportTxt = dirReport + '/report.txt'
reportPdf = dirReport + '/report.pdf'

if not os.path.exists(dirReport):
    os.chmod(basedir, 0777)
    os.makedirs(dirReport)
    os.chmod(dirReport, 0777)
    os.makedirs(dirReport + '/errors')

basedirShots = 'screenshots/'
dirScreenshots = basedirShots + current
if not os.path.exists(dirScreenshots):
    os.chmod(basedirShots, 0777)
    os.makedirs(dirScreenshots)

Popen(['behave', '--outfile', reportTxt])
#Popen(['rst2pdf', reportTxt, reportPdf])
