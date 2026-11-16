#!/bin/sh
rsync -a /var/www/ backup@10.0.0.50:/srv/backups/web01/
