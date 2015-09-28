#!/bin/sh

if [ $# -lt 2 ]; then
    echo "Usage: $0 <username_on_gabe> <subdir>"
    exit 1
fi
rsync --progress -v -a -e "ssh -x" "$2" $1@gabe.freedesktop.org:/srv/specifications.freedesktop.org/www/

