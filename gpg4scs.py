#!/usr/bin/env python
#-*-coding:UTF-8-*-

# Known Bugs:
# 1. Does not support Chinese path or filename
# 2. Can not download and encypt files whose path contains space on Linux 

__version__ = '0.1.0'

import sys
reload(sys).setdefaultencoding('UTF-8')
sys.dont_write_bytecode = True

import os
sys.path.insert(0, os.path.join(os.getcwd(), 'packages'))

import random, string
import re, ConfigParser
import time
from datetime import datetime
from sets import Set

import gnupg
import sinastorage
from sinastorage.bucket import ACL, SCSError, KeyNotFound, BadRequest

class Common(object):
    """Common Object"""

    def __init__(self):
        """load config"""
        ConfigParser.RawConfigParser.OPTCRE = re.compile(r'(?P<option>[^=\s][^=]*)\s*(?P<vi>[=])\s*(?P<value>.*)$')
        self.CONFIG = ConfigParser.ConfigParser(allow_no_value=True)
        self.CONFIG_FILENAME = os.path.join(os.getcwd(), 'profile.ini')
        self.CONFIG.read(self.CONFIG_FILENAME)

        self.SCS_ACCESS_KEY = self.CONFIG.get('sina-storage', 'accesskey')
        self.SCS_SECRET_KEY = self.CONFIG.get('sina-storage', 'secretkey')
        self.SCS_BUKET_NAME = self.CONFIG.get('sina-storage', 'buket')

        sinastorage.setDefaultAppInfo(self.SCS_ACCESS_KEY, self.SCS_SECRET_KEY)
        self.SCSBucket = sinastorage.bucket.SCSBucket(self.SCS_BUKET_NAME)

        self.root = self.CONFIG.get('local', 'path')
        self.WORKSPACE = os.path.join(self.root, '.workspace')

        self.GPG_HOME = os.path.join(os.getcwd(), 'GunPG')
        self.GPG = gnupg.GPG(gnupghome=self.GPG_HOME)
        fo = open(os.path.join(os.getcwd(), 'secret.asc'))
        self.GPG_KEY = self.GPG.import_keys(fo.read()).fingerprints[0]
        fo.close()
        self.GPG_PASSPHRASE = self.CONFIG.get('gpg', 'passphrase')
        if self.GPG_PASSPHRASE == '': self.GPG_PASSPHRASE = None

        try:
            os.mkdir(self.GPG_HOME)
        except OSError:
            pass # already exists or cannot be created

        try:
            os.makedirs(self.WORKSPACE)
        except:
            pass

    def get_random_name(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

    """
    GnuPG
    """
    def encrypt_message(self, message):
        return str(self.GPG.encrypt(message, recipients=[self.GPG_KEY], always_trust=True))

    def encrypt_file(self, outputName, inputName):
        with open(inputName, 'rb') as f:
            status = self.GPG.encrypt_file(
                f, recipients=[self.GPG_KEY], always_trust=True,
                output=outputName)
        return status.ok

    def decrypt_file(self, outputName, inputName):
        with open(inputName, 'rb') as f:
            status = self.GPG.decrypt_file(f, always_trust=True, passphrase=self.GPG_PASSPHRASE, output=outputName)
        return status.ok

    """
    Sina Cloud Storage
    """
    def put_file(self, onlineName, localName):
        return self.SCSBucket.putFile(onlineName, localName)

    def put_content(self, onlineName, content):
        return self.SCSBucket.put(onlineName, content)

    def download_file(self, localName, onlineName):
        directory = os.path.dirname(localName)
        try:
            os.makedirs(directory)
        except:
            pass # already exists or cannot be created

        response = self.SCSBucket[onlineName]
        CHUNK = 16 * 1024
        with open(localName, 'wb') as fp:
            while True:
                chunk = response.read(CHUNK)
                if not chunk: break
                fp.write(chunk)

    def get_online_files_dict(self):
        files_generator = self.SCSBucket.listdir()
        fdict = dict()
        for item in files_generator:
            # item[0]: file name
            # item[4]: last modified datetime object
            fdict[item[0]] = time.mktime(item[4].timetuple())
        return fdict

    """
    Sina Cloud Storage with GnuPG
    """
    def encrypt_and_put_file(self, onlineName, localName):
        tmpName = os.path.join(self.WORKSPACE, self.get_random_name())
        self.encrypt_file(tmpName, localName)
        self.put_file(onlineName, tmpName)

    def encrypt_and_put_content(self, onlineName, content):
        edata = self.encrypt_message(content)
        self.put_content(onlineName, edata)

    def download_and_decrypt(self, localName, onlineName):
        directory = os.path.dirname(localName)
        try:
            os.makedirs(directory)
        except:
            pass # already exists or cannot be created
        tmpName = os.path.join(self.WORKSPACE, self.get_random_name())
        self.download_file(tmpName, onlineName)
        self.decrypt_file(localName, tmpName)


class FileManagement(object):
    """File Management Object"""

    def __init__(self):
        self.common = Common()
        self.ofiles = self.common.get_online_files_dict()
        self.lfiles = dict()
        for path, dirs, files in os.walk(self.common.root):
            for name in files:
                fileName = os.path.join(path, name)
                self.lfiles[fileName] = os.path.getmtime(fileName) - 8*3600

    def oname_to_lname(self, onlineName):
        localRel = os.path.splitext(onlineName)[0].replace('/', os.path.sep)
        return os.path.join(self.common.root, localRel)

    def lname_to_oname(self, localName):
        localRel = os.path.relpath(localName, self.common.root)
        result = localRel.replace(os.path.sep, '/') + '.gpg'
        return result

    def is_to_up(self, lname):
        oname = self.lname_to_oname(lname)
        if self.common.WORKSPACE in lname:
            return False
        if oname in self.ofiles.keys():
            # self.lfiles[lname]: local modified timestamp
            # self.ofiles[oname]: online modified timestamp
            if self.lfiles[lname] <= self.ofiles[oname]:
                return False
        return True

    def is_to_down(self, oname):
        lname = self.oname_to_lname(oname)
        if lname in self.lfiles:
            return False
        return True

    def get_up_list(self):
        ulist = list()
        # print self.lfiles.keys()
        for lname in self.lfiles.keys():
            if self.is_to_up(lname):
                ulist.append(lname)
        return ulist # local path fomat

    def get_down_list(self):
        dlist = list()
        for oname in self.ofiles.keys():
            if self.is_to_down(oname):
                dlist.append(oname)
        return dlist # online path fomat

    def upload(self):
        ulist = self.get_up_list()
        if len(ulist) == 0:
            return

        print 'uploading', len(ulist), 'file(s)...'
        try:
            for lname in ulist:
                print lname
                oname = self.lname_to_oname(lname)
                self.common.encrypt_and_put_file(oname, lname)
        except:
            print 'upload failed!'

    def download(self):
        dlist = self.get_down_list()
        if len(dlist) == 0:
            return

        print 'downloading', len(dlist), 'file(s)...'
        try:
            for oname in dlist:
                print os.path.splitext(oname)[0] # print without '.gpg'
                lname = self.oname_to_lname(oname)
                self.common.download_and_decrypt(lname, oname)
                # set local file last modified time as online version
                if os.path.exists(lname):
                    os.utime(lname, (time.time(), self.ofiles[oname] + 8*3600))
        except:
            print 'download failed!'

    def clean_workspace(self):
        size = sum(os.path.getsize(os.path.join(self.common.WORKSPACE, f)) for f in os.listdir(self.common.WORKSPACE))
        if size > 1073741824: # 1 GB = 1024*1024*1024 byte
            try:
                __import__('shutil').rmtree(self.common.WORKSPACE)
            except:
                pass


def main():
    args = Set(sys.argv[1:])
    cmds = Set(['-u', '--upload', '-d', '--download', '-s', '--sync'])
    if not args.issubset(cmds) or len(args) == 0:
        print """usage: python gpg4scs.py [option]
Options:
-u, --upload   : upload
-d, --download : download
-s, --sync     : synchronize"""
        return

    try:
        fm = FileManagement()
    except:
        print 'connect to sina cloud failed!'

    if '-s' in args or '--sync' in args:
        fm.upload()
        fm.download()
        return
    if '-u' in args or '--upload' in args:
        fm.upload()
    if '-d' in args or 'download' in args:
        fm.download()

    if random.randint(1, 5) == 1:
        fm.clean_workspace()


if __name__ == "__main__":
    sys.exit(main())