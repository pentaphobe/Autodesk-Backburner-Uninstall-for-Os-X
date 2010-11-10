#!/usr/bin/python

import shutil
import os
import sys

# set this to True to prevent any file writes (except backups)
TEST_MODE = False

# a few errors should be non-terminal, change this to make them terminal
QUIT_ON_ERRORS = False

UNATTENDED = False
HTTPD_CONF_PATH = '/etc/apache2/httpd.conf'
BACKBURNER_UTILS_PATH = '/usr/discreet'
BACKUP_DIR      = os.path.expanduser('~/Desktop/Backburner Uninstall Backups/')
LAUNCHDAEMON_PATH = '/Library/LaunchDaemons/'
LAUNCHDAEMON_LIST = ['com.autodesk.backburner_manager.plist', 'com.autodesk.backburner_server.plist', 'com.autodesk.backburner_start.plist']
WEBSERVER_PATH     = '/Library/WebServer/Documents/'
WEBSERVER_LIST    = ['adsk_web_entry', 'Backburner', 'index.php']


apacheText = '''
#
# Backburner Flash Monitor authentication section
#
<Directory /Library/WebServer/Documents/Backburner>
AuthType Basic
AuthName Backburner 
AuthUserFile /etc/apache2/auth/backburner.auth
<Limit GET POST>                                    
</Limit>
require valid-user
</Directory>

<Directory /Library/WebServer/Documents/backburner>
AuthType Basic
AuthName Backburner 
AuthUserFile /etc/apache2/auth/backburner.auth
<Limit GET POST>                                    
</Limit>
require valid-user
</Directory>

#
# Wiretap tool authentication section
#
<Location /cgi-bin/Backburner/wiretap_tool>
AuthType Basic
AuthName Backburner
AuthUserFile /etc/apache2/auth/backburner.auth
<Limit GET POST>
</Limit>
require valid-user
</Location>'''

READMEtxt = '''
This folder contains backups from your Backburner uninstall

You _can_ copy these files back to their original locations if you wish to re-install Backburner,
however I wouldn't recommend it.  use the Autodesk installer instead.

'''

internalExceptionNote = '\n(to override this problem run the uninstaller with the -o option\n'

class UninstallerException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg + internalExceptionNote)

def ask(text, positiveResponse='yes', negativeResponse='no'):
    optionString = "(%s/%s): " % (positiveResponse, negativeResponse)
    inp = raw_input(text + optionString)
    while inp != positiveResponse and inp != negativeResponse:
        inp = raw_input("  please enter either '%s' or '%s': " % (positiveResponse, negativeResponse))
    
    return inp == positiveResponse    

def deleteWithConfirmation(fname):
    fType = None
    if os.path.isfile(fname):
        fType = 'file'
    elif os.path.isdir(fname):
        fType = 'directory'

    if fType != None:
        if not UNATTENDED:
            if not ask("  may I delete the %s:\n  %s ?" % (fType, fname)):
                Exception("\nInstallation incomplete")
        if not TEST_MODE:
            if fType == 'file':
                os.remove(fname)
            else:
                shutil.rmtree(fname)

def confirmBackupFolder():
    if not os.path.isdir(BACKUP_DIR):
        print "  creating backup folder on your desktop"
        os.makedirs(BACKUP_DIR, mode=0777)
        f = open(BACKUP_DIR + 'README.txt', 'w')
        f.writelines(READMEtxt)
        f.close()
    

def backup(fname):
    confirmBackupFolder()
    backup_fname = BACKUP_DIR + os.path.basename(fname)
    print "  backing up %s to \n    %s" % (fname, backup_fname)
    try:
        if os.path.isfile(fname):
            shutil.copy2(fname, backup_fname)
        elif os.path.isdir(fname):
            shutil.copytree(fname, backup_fname)
    except Exception, err:
        print "\n\nError backing up %s" % (fname)
        if err.args[0] == 17:
            print "  this is commonly due to an existing file in the backup location"
            print "  You can manually move or delete the backup, but I ain't touching it!"
            print "     the backup dir is: %s" % (BACKUP_DIR)
        raise err
        
def stop_backburner():
    """ stops the backburner server and manager as per instructions at
        http://usa.autodesk.com/adsk/servlet/ps/dl/item?linkID=9242618&id=15505121&siteID=123112
    """
    os.system('/usr/discreet/backburner/backburner_server stop')
    os.system('/usr/discreet/backburner/backburner_manager stop')

def stop_apache():
    """ stops the Apache server so we can modify the config file
        it may be acceptable to merely modify the file and then restart the server (almost certainly)
        but better not to risk it until I've confirmed this
    """
    os.system('sudo /usr/sbin/apachectl stop')

def start_apache():
    """ starts the Apache server """
    os.system('sudo /usr/sbin/apachectl start')

def confirm_sudo():
    if os.geteuid() != 0:
        sys.exit("This script requires high privileges to modify system files.\nTry: sudo %s" % (os.path.basename(sys.argv[0])))

def fix_apache():
    print "fixing Apache config file..."
    backup(HTTPD_CONF_PATH);
    f = open(HTTPD_CONF_PATH, 'r')

    lines = ''.join(f.readlines())
    f.close()
    idx = lines.find(apacheText)
    if idx == -1 and QUIT_ON_ERRORS:
        raise UninstallerException("Can't find Backburner's data in the Apache config (%s)" % (HTTPD_CONF_PATH) )
    fixed = lines[:idx] + lines[idx+len(apacheText):]

    if not TEST_MODE:
        f = open(HTTPD_CONF_PATH, 'w')
        f.seek(0)
        f.writelines(fixed)
        
    f.close()
    print "  done."

def remove_backburner_server():
    """ removes the Backburner support files from the system """
    print "removing Backburner support files..."
    backup(BACKBURNER_UTILS_PATH)

    deleteWithConfirmation(BACKBURNER_UTILS_PATH)

def remove_launchDaemons():
    print "removing Backburner launchDaemons..."
    for ldFile in LAUNCHDAEMON_LIST:
        backup(LAUNCHDAEMON_PATH + ldFile)
        deleteWithConfirmation(LAUNCHDAEMON_PATH + ldFile)

def ask_attendance():
    """ I'm writing this quite quickly, and had a major cbf moment with features, so this is to
        avoid writing argument handling.  yes, I know there are libs. yes I know they are easy to use.
    """
    global UNATTENDED
    
    print """By default this program will confirm its actions with you before doing them
(except backing up, which happens automatically)."""
    UNATTENDED = ask("Would you like to skip confirmations?", 'yes', 'no')
    modeText = "ATTENDED"
    if UNATTENDED:
        modeText = "UNATTENDED"
    print "\n(Running in %s mode)\n" % (modeText)

def remove_web_files():
    """ Cleans out the apache web directory and attempts to restore backups
    """
    print "removing Backburner files from web server..."
    for webFile in WEBSERVER_LIST:
        backup(WEBSERVER_PATH + webFile)
        deleteWithConfirmation(WEBSERVER_PATH + webFile)

    fixFiles = os.listdir(WEBSERVER_PATH)
    for tofix in fixFiles:
        if tofix.startswith('index') and tofix.endswith('.backup'):
            newName = tofix[:tofix.find('.backup')]
            print "  restoring %s to %s" % (tofix, newName)
            if not TEST_MODE:
                os.rename(WEBSERVER_PATH + tofix, WEBSERVER_PATH + newName)

def main():
    try:
        confirm_sudo()
        ask_attendance()
        stop_backburner()
        stop_apache()
        fix_apache()
        remove_backburner_server()
        remove_launchDaemons()
        remove_web_files()
        start_apache()
    except Exception, err:
        print err.args

if __name__ == '__main__':
    main()
