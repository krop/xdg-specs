#!/bin/sh

if [ $# -lt 2 ]; then
    echo "Usage: $0 <username_on_www> <subdir>"
    exit 1
fi
rsync --progress -v -a -e "ssh -x" "$2" $1@www.freedesktop.org:/srv/specifications.freedesktop.org/www/

ssh $1@www.freedesktop.org chmod -R g+w /srv/specifications.freedesktop.org/www/"$2" 2>/dev/null

