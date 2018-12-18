#!/bin/bash

DJANGO_BASE_DIR=/home/nzilio/ulrich_lab_intranet/django_project
BACKUP_DIR=$DJANGO_BASE_DIR/ulrich_lab_intranet_db_backup/

# Remove all .xlsx and .gz files older than 7 days from backup folder 
/usr/bin/find $BACKUP_DIR -maxdepth 1 -type f -mtime +7 -iname '*.gz' -delete

# Create datadump for django database and gzip it
CURRENT_DATE_TIME=`date +'%Y%m%d_%H%M'`
/usr/bin/mysqldump -u django -pdFf3CpE8yqpVzadIn5VJ django | gzip > $BACKUP_DIR/ulrich_lab_intranet_db_dump_${CURRENT_DATE_TIME}.sql.gz

/home/nzilio/ulrich_lab_intranet/bin/python $DJANGO_BASE_DIR/manage.py shell < $DJANGO_BASE_DIR/beyond_django/export_db_tables_as_xlsx.py