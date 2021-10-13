#!/usr/bin/env python3

# Dependencies to run this:
#  - xmlto and docbook2html in $PATH

# FIXME:
#  - correctly handle all exceptions
#  - copy dtd files where they should be
#  - new structure for website:
#    specs.fd.o/index.html -- general index
#    specs.fd.o/desktop-entry/index.html -- index of all versions of desktop entry, with all formats
#    specs.fd.o/desktop-entry/1.0/desktop-entry-spec.xml -- docbook version of the spec 1.0
#    specs.fd.o/desktop-entry/1.0/index.html -- one-page html version of the spec 1.0
#    specs.fd.o/desktop-entry/1.0/split/ -- multiple-page html version of the spec 1.0
#    specs.fd.o/desktop-entry/latest/ -- link to directory containing latest version of the spec

import os
import sys
import io

import errno

import hashlib
import shutil
import subprocess
import re
import urllib.request
import urllib.error
from distutils import spawn

# True = Allow this file to differ from the committed version
DEVELOPMENT = True

# When running this on the website itself, set USELOCALFILES to False
# But since docbook2html isn't installed there, we currently have to run it locally so this is now True (i.e. it uses the local files)
USELOCALFILES = False

# Directory to put everything in, relative to the git root directory
OUTPUTDIR = "public"

GITWEB = 'https://gitlab.freedesktop.org'
HASH = 'md5'

BUG_REPORT_LABEL = 'Freedesktop.org GitLab'
BUG_REPORT_URL = 'https://gitlab.freedesktop.org/xdg/xdg-specs/issues/new?issue[assignee_id]=&issue[milestone_id]=&issue[title]=web-export:%20&issue[description]=%0d%0dCC:%20@hadess'

# Specifications with their own build system
# FIXME: would be good to be able to use the same script to generate them
SELF_BUILT = [ "idle-inhibit-spec", "secret-service", "mpris-spec" ]

if not spawn.find_executable("xmlto"):
    print("ERROR: xmlto is not installed...")
    sys.exit(1)

def safe_mkdir(dir):
    if not dir:
        return

    try:
        os.mkdir(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e


def get_hash_from_fd(fd, algo = HASH, read_blocks = 1024):
    if algo not in [ 'md5' ]:
        raise Exception('Internal error: hash algorithm \'%s\' not planned in code.' % algo)

    hash = hashlib.new(algo)
    while True:
        data = fd.read(read_blocks)
        if not data:
            break
        hash.update(data)
    return hash.digest()


def get_hash_from_url(url, algo = HASH):
    fd = urllib.request.urlopen(url, None)
    digest = get_hash_from_fd(fd, algo)
    fd.close()
    return digest


def get_hash_from_path(path, algo = HASH):
    fd = open(path, 'rb')
    digest = get_hash_from_fd(fd, algo, read_blocks = 32768)
    fd.close()
    return digest


def get_hash_from_data(data, algo = HASH):
    fd = io.BytesIO(data)
    digest = get_hash_from_fd(fd, algo, read_blocks = 32768)
    fd.close()
    return digest

def get_main_branch(url):
    out = subprocess.check_output(["git ls-remote --symref " + url + " HEAD"], shell=True)
    m = re.search('refs/heads/(.+)\t', out.decode('utf-8'))
    return m.group(1)

def open_file_with_template(dst, template):
    fd = open(dst, 'w')
    with open(template, 'r') as content_file:
        content = content_file.read()
    fd.write(content)
    return fd

class VcsObject:
    def __init__(self, vcs, repo, file, revision = None):
        self.vcs = vcs
        if self.vcs != 'git':
            raise Exception('Unknown VCS: %s' % self.vcs)
        self.repo = repo
        self.file = file
        self.revision = revision
        if not self.revision:
            self.revision = get_main_branch('/'.join((GITWEB, self.repo + '.git')))
        self.data = None

    def get_url(self):
        query = {}
        baseurl = GITWEB
        path = '/'.join((self.repo, 'raw', self.revision, self.file))

        (scheme, netloc, basepath) = urllib.parse.urlsplit(baseurl)[0:3]
        full_path = '/'.join((basepath, path))

        query_str = urllib.parse.quote(bytes(query))
        return urllib.parse.urlunsplit((scheme, netloc, full_path, query_str, ''))

    def fetch(self):
        if self.data:
            return

        if USELOCALFILES:
            localpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/' + self.file
            fd = open(localpath, 'rb')
            self.data = fd.read()
            fd.close()
        else:
            url = self.get_url()
            try:
                fd = urllib.request.urlopen(url, None)
            except:
                print("Failed to fetch URL: %s" % url)
                raise
            self.data = fd.read()
            fd.close()

    def get_hash(self):
        self.fetch()
        return get_hash_from_data(self.data)


class SpecObject():
    def __init__(self, vcs, spec_dir, version):
        self.vcs = vcs
        self.spec_dir = spec_dir
        self.version = version

        basename = os.path.basename(self.vcs.file)
        (self.basename_no_ext, self.ext) = os.path.splitext(basename)

        self.filename = '%s-%s%s' % (self.basename_no_ext, self.version, self.ext)

        if self.ext not in ['.xml', '.sgml', '.txt', '.dtd', '.html']:
            raise Exception('Format \'%s\' not supported for %s' % (self.ext, self.vcs.get_url()))

        self.downloaded = False
        self.one_chunk = False
        self.multiple_chunks = False

    def download(self):
        safe_mkdir(self.spec_dir)
        path = os.path.join(self.spec_dir, self.filename)

        if os.path.exists(path):
            current_hash = get_hash_from_path(path)
            vcs_hash = self.vcs.get_hash()
            if current_hash == vcs_hash:
                return

        self.vcs.fetch()
        fd = open(path, 'wb')
        fd.write(bytes(self.vcs.data))
        fd.close()

        self.downloaded = True

    def htmlize(self, force = False):
        if not self.downloaded and not force:
            return

        if self.ext == '.html':
            return

        print("Converting", self.filename, "to HTML")

        path = os.path.join(self.spec_dir, self.filename)
        (path_no_ext, ext) = os.path.splitext(path)

        # One-chunk HTML
        html_path = '%s%s' % (path_no_ext, '.html')
        if os.path.exists(html_path):
            os.unlink(html_path)

        # Multiple chunks
        html_dir = os.path.join(self.spec_dir, self.version)
        if os.path.exists(html_dir):
            shutil.rmtree(html_dir)

        one_chunk_command = None
        multiple_chunks_command = None

        if self.spec_dir in SELF_BUILT:
            if self.spec_dir != 'mpris-spec':
                multiple_chunks_command = ['make', '-C', "../" + os.path.dirname(self.vcs.file)]
            else:
                multiple_chunks_command = ['make', '-C', "../mpris-spec"]
        elif self.ext == '.xml':
            one_chunk_command = ['xmlto', '-o', self.spec_dir, 'html-nochunks', path]
            multiple_chunks_command = ['xmlto', '-o', html_dir, 'html', path]
        elif self.ext == '.sgml':
            one_chunk_command = ['docbook2html', '-o', self.spec_dir, '--nochunks', path]
            multiple_chunks_command = ['docbook2html', '-o', html_dir, path]

        if one_chunk_command:
            retcode = subprocess.call(one_chunk_command)
            if retcode != 0:
                raise Exception('Cannot convert \'%s\' to HTML.\nThe command was %s' % (path, one_chunk_command))
            self.one_chunk = True

        if self.spec_dir not in SELF_BUILT:
            safe_mkdir(html_dir)
        if multiple_chunks_command:
            retcode = subprocess.call(multiple_chunks_command)
            if retcode != 0:
                raise Exception('Cannot convert \'%s\' to multiple-chunks HTML.\nThe command was %s' % (path, multiple_chunks_command))
            self.multiple_chunks = True
        if multiple_chunks_command and self.spec_dir in SELF_BUILT:
            if self.spec_dir != 'mpris-spec':
                shutil.copytree('../' + os.path.dirname(self.vcs.file) + '/html', html_dir)
            else:
                shutil.copytree('../mpris-spec/doc/spec/', html_dir)

    def latestize(self, fd):
        filename_latest = '%s-latest%s' % (self.basename_no_ext, self.ext)

        path_latest = os.path.join(self.spec_dir, filename_latest)
        if os.path.exists(path_latest):
            os.unlink(path_latest)
        os.symlink(self.filename, path_latest)

        fd.write('\n- %s\n' % self.spec_dir)

        if self.ext in ['.xml', '.sgml']:
            fd.write('  - **version %s (' % self.version)

            # One-chunk HTML
            html_path_latest = os.path.join(self.spec_dir, '%s-latest%s' % (self.basename_no_ext, '.html'))
            if os.path.exists(html_path_latest):
                os.unlink(html_path_latest)

            (filename_no_ext, ext) = os.path.splitext(self.filename)
            html_filename = '%s%s' % (filename_no_ext, '.html')
            html_path = os.path.join(self.spec_dir, html_filename)
            has_html_path = False
            if os.path.exists(html_path):
                os.symlink(html_filename, html_path_latest)
                has_html_path = True
                fd.write('[one page](%s)' % html_path_latest)

            # Multiple chunks
            html_dir_latest = os.path.join(self.spec_dir, 'latest')
            if os.path.exists(html_dir_latest):
                os.unlink(html_dir_latest)

            html_dir = os.path.join(self.spec_dir, self.version)
            if os.path.exists(html_dir):
                os.symlink(self.version, html_dir_latest)
                if has_html_path:
                    fd.write(', ')
                fd.write('[split pages](%s))**\n' % html_dir_latest)
            else:
                fd.write(')**\n')

            return

        fd.write('  - **version %s ([%s format](%s))**\n' % (self.version, self.ext, path_latest))

SCRIPT = VcsObject('git', 'xdg/xdg-specs', 'web-export/update.py')
SPECS_INDEX = VcsObject('git', 'xdg/xdg-specs', 'web-export/specs.idx')


def is_up_to_date():
    current_hash = get_hash_from_path(__file__)
    vcs_hash = SCRIPT.get_hash()

    return current_hash == vcs_hash


if not DEVELOPMENT:
    if not is_up_to_date():
        print(sys.stderr, 'Script is not up-to-date, please download %s' % SCRIPT.get_url(), file=sys.stderr)
        sys.exit(1)

    SPECS_INDEX.fetch()
    lines = SPECS_INDEX.data.split('\n')
else:
    lines = open('specs.idx').readlines()


out = subprocess.check_output(["git rev-parse --show-toplevel"], shell=True)
root_dir = out.decode('utf-8').rstrip()
public_dir = os.path.join(root_dir, OUTPUTDIR)
safe_mkdir(public_dir)

latests = []
source_dirs = {}
index_fd = open_file_with_template(os.path.join(public_dir, 'index.md'), 'index.md.in')

for line in lines:
    line = line.strip()
    if not line or line.startswith('#'):
        continue

    (data, revision, version, path) = line.split()
    splitted_line = data.split(":")
    if data.startswith("git:"):
        repo = splitted_line[1]
        if USELOCALFILES and (revision != "HEAD" or repo != "xdg/xdg-specs"):
            continue
        vcs = VcsObject('git', repo, splitted_line[2], revision)
    else:
        vcs = VcsObject(splitted_line[0], None, data, revision)

    spec = SpecObject(vcs, path, version)

    spec.download()
    spec.htmlize()

    # Create latest links if it's the first time we see this spec
    if (spec.spec_dir, spec.basename_no_ext) not in latests:
        latests.append((spec.spec_dir, spec.basename_no_ext))
        spec.latestize(index_fd)
        shutil.copy('redirect.html', spec.spec_dir + '/index.html')
    else:
        index_fd.write('  - [version %s](%s/%s)\n' % (version, spec.spec_dir, spec.version))

    target_dir = os.path.join(public_dir, spec.spec_dir)
    src_dir = spec.spec_dir
    if src_dir not in source_dirs:
        source_dirs[src_dir] = target_dir

index_fd.write('\n\n\n\n')
index_fd.write('###### Report website bugs on the [%s](%s)\n' % (BUG_REPORT_LABEL, BUG_REPORT_URL))
index_fd.close()

for dirs in source_dirs.items():
    shutil.copytree(dirs[0], dirs[1], symlinks=True)

# Copy file for the website look
shutil.copy('favicon.ico', public_dir)
shutil.copy('simple.css', public_dir)
shutil.copytree('images', os.path.join(public_dir, 'images'))
os.chdir(public_dir)
subprocess.call(['discount-mkd2html', '-css', 'simple.css', 'index.md'])
