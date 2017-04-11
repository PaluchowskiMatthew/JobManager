#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0403
# pylint: disable=E1101
# pylint: disable=R0901
# pylint: disable=R0915

# Copyright (c) 2014-2015, Human Brain Project
#                          Cyrille Favreau <cyrille.favreau@epfl.ch>
#
# This file is part of RenderingResourceManager
# <https://github.com/BlueBrain/RenderingResourceManager>
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License version 3.0 as published
# by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# All rights reserved. Do not distribute without further notice.

"""
This modules defines the data structure used by the rendering resource manager to manager
user session
"""
import requests
import random
import json
import traceback

from rest_framework import serializers, viewsets
from django.http import HttpResponse
import management.session_manager_settings as consts
import rendering_resource_manager_service.service.settings as settings
import rendering_resource_manager_service.utils.custom_logging as log
import rendering_resource_manager_service.utils.tools as tools
from rendering_resource_manager_service.session.models import Session
from rendering_resource_manager_service.session.management import job_manager
import management.session_manager as session_manager



class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer to session data
    """

    def __len__(self):
        pass

    def __getitem__(self, item):
        pass

    class Meta(object):
        """
        Meta class for the Session Serializer
        """
        model = Session
        fields = ('id', 'owner', 'renderer_id')


class SessionDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer to session data
    """

    def __len__(self):
        pass

    def __getitem__(self, item):
        pass

    class Meta(object):
        """
        Meta class for the Session Serializer
        """
        model = Session
        fields = ('id', 'owner', 'created', 'renderer_id', 'job_id', 'status',
                  'http_host', 'http_port', 'valid_until', 'cluster_node')


class CommandSerializer(serializers.ModelSerializer):
    """
    Serializer to command data
    """
    def __len__(self):
        pass

    def __getitem__(self, item):
        pass

    class Meta(object):
        """
        Meta class for the Command Serializer
        """
        model = Session
        fields = ('parameters', )


class DefaultSerializer(serializers.ModelSerializer):
    """
    Serializer to default view (No parameters)
    """
    def __len__(self):
        pass

    def __getitem__(self, item):
        pass

    class Meta(object):
        """
        Meta class for the Command Serializer
        """
        model = Session
        fields = ('created',)


class KeepAliveSerializer(serializers.ModelSerializer):
    """
    Serializer to default view (No parameters)
    """
    def __len__(self):
        pass

    def __getitem__(self, item):
        pass

    class Meta(object):
        """
        Meta class for the Command Serializer
        """
        model = Session
        fields = ('status', )

class SessionDetailsViewSet(viewsets.ModelViewSet):
    """
    Displays all attributes of the current session
    """
    queryset = Session.objects.all()
    serializer_class = SessionDetailsSerializer

    @classmethod
    def get_session(cls, request, pk):
        """
        Retrieves a user session
        :param : request: The REST request
        :rtype : A Json response containing on ok status or a description of the error
        """
        sm = session_manager.SessionManager()
        status = sm.get_session(pk, request, SessionSerializer)
        return HttpResponse(status=status[0], content=status[1])


class SessionViewSet(viewsets.ModelViewSet):
    """
    Displays a minimal set of information related to a given session
    """

    queryset = Session.objects.all()
    serializer_class = SessionSerializer

    @classmethod
    def create_session(cls, request):
        """
        Creates a user session
        :param : request: request containing the launching parameters of the rendering resource
        :rtype : An HTTP response containing on ok status or a description of the error
        """
        sm = session_manager.SessionManager()
        # Create new Cookie ID for new session
        session_id = sm.get_session_id()
        try:
            status = sm.create_session(
                session_id, request.DATA['owner'], request.DATA['renderer_id'])
            response = HttpResponse(status=status[0], content=status[1])
            response.set_cookie(consts.COOKIE_ID, session_id)
            log.info(1, 'Session created ' + str(session_id))
            return response
        except KeyError as e:
            return HttpResponse(status=401, content=str(e))
        else:
            return HttpResponse(status=401, content='Unexpected exception')


class CommandViewSet(viewsets.ModelViewSet):
    """
    ViewSets define the view behavior
    """

    queryset = Session.objects.all()
    serializer_class = CommandSerializer

    @classmethod
    def execute(cls, request, command):
        """
        Executes a command on the rendering resource
        :param : request: The REST request
        :param : command: Command to be executed on the rendering resource
        :rtype : A Json response containing on ok status or a description of the error
        """
        # pylint: disable=R0912
        try:
            session_id = session_manager.SessionManager().get_session_id_from_request(request)
            log.debug(1, 'Processing command <' + command + '> for session ' + str(session_id))
            session = Session.objects.get(id=session_id)
            response = None
            if command == 'schedule':
                response = cls.__schedule_job(session, request)
            else:
                url = request.get_full_path()
                prefix = settings.BASE_URL_PREFIX + '/session/'
                cmd = url[url.find(prefix) + len(prefix) + 1: len(url)]
                response = cls.__forward_request(session, cmd, request)
            return response
        except KeyError as e:
            log.debug(1, str(traceback.format_exc(e)))
            response = json.dumps({'contents': 'Cookie ' + str(e) + ' is missing'})
            return HttpResponse(status=404, content=response)
        except Session.DoesNotExist as e:
            log.debug(1, str(traceback.format_exc(e)))
            response = json.dumps({'contents': 'Session does not exist'})
            return HttpResponse(status=404, content=response)
        except Exception as e:
            msg = traceback.format_exc(e)
            log.error(str(msg))
            response = json.dumps({'contents': str(msg)})
            return HttpResponse(status=500, content=response)

    @classmethod
    def __schedule_job(cls, session, request):
        """
        Starts a rendering resource by scheduling a slurm job
        :param : session: Session holding the rendering resource
        :param : request: HTTP request with a body containing a JSON representation of the job
                 parameters
        :rtype : An HTTP response containing the status and description of the command
        """
        job_information = job_manager.JobInformation()
        body = request.DATA
        job_information.params = body.get('params')
        job_information.environment = body.get('environment')
        job_information.reservation = body.get('reservation')
        job_information.nb_cpus = body.get('nb_cpus', 0)
        job_information.nb_gpus = body.get('nb_gpus', 0)
        job_information.nb_nodes = body.get('nb_nodes', 0)
        job_information.exclusive_allocation = body.get('exclusive', False)
        job_information.allocation_time = body.get('allocation_time', settings.SLURM_DEFAULT_TIME)
        session.http_host = ''
        session.http_port = consts.DEFAULT_RENDERER_HTTP_PORT + random.randint(0, 1000)
        status = job_manager.globalJobManager.schedule(session, job_information)
        return HttpResponse(status=status[0], content=status[1])



    @classmethod
    def __forward_request(cls, session, command, request):
        """
        Forwards the HTTP request to the rendering resource held by the given session
        :param : session: Session holding the rendering resource
        :param : command: Command passed to the rendering resource
        :param : request: HTTP request
        :rtype : An HTTP response containing the status and description of the command
        """
        # query the status of the current session
        status = cls.__session_status(session)
        if status[0] != 200:
            return HttpResponse(status=status[0], content=status[1])

        try:
            # Any other command is forwarded to the rendering resource
            url = 'http://' + session.http_host + ':' + str(session.http_port) + '/' + command
            log.info(1, 'Querying ' + str(url))
            headers = tools.get_request_headers(request)

            response = requests.request(
                method=request.method, timeout=settings.REQUEST_TIMEOUT,
                url=url, headers=headers, data=request.body)

            data = response.content
            response.close()
            return HttpResponse(status=response.status_code, content=data)
        except requests.exceptions.RequestException as e:
            response = json.dumps({'contents': str(e)})
            return HttpResponse(status=400, content=response)
