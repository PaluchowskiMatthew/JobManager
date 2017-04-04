#!/bin/bash

cd /home/raccct/DATA/Dropbox/EPFL/17fs/Semesterproject/samplecode/RenderingResourceManager #path of RRM

source activate py27

export PYTHONPATH=$PWD:$PYTHONPATH
cd rendering_resource_manager_service
python manage.py syncdb

google-chrome http://localhost:9000/rendering-resource-manager/v1/api-docs

python manage.py runserver localhost:9000 #runs the server

$SHELL
