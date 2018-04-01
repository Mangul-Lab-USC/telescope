import telescope.utils as utils
from nacl import pwhash, secret, utils as naclutils
import nacl


## standard libraries
import sys, os, io
import datetime, time
import json
import numpy as np

## For the web service
import tornado.ioloop
import tornado.web as web
from tornado.ioloop import IOLoop
from tornado.web import asynchronous, RequestHandler, Application
from tornado.httpclient import AsyncHTTPClient
import logging

## Import internal modules
from telescope.server import SGEServerInterface
import telescope.jobStatusMonitor as jobStatusMonitor
from telescope.sshKernel import tlscpSSH
from telescope.dbKernel import db
import telescope.utils as utils

rootdir=os.path.dirname(__file__)


class UserList(tornado.web.RequestHandler):
    """
    Root access
    """

    def initialize(self, ServerInterface, queueMonitor, databasePath ):

        ## ServerInterface object
        self.ServerInterface = ServerInterface

        # Server's queue monitoringInterval
        self.queueMonitor = queueMonitor

        self.databasePath = databasePath

        return



    def get(self):

        content = ""

        ## Starting the connection to the databse
        database = db( self.databasePath )

        ## Getting the list of users
        listUsers = database.getAllUsers()


        content += "<p>List of users currently being tracked.</p>"


        table_strstart = '''<div class="page-header">
                    <table class="table table-striped">
                    <thead><tr>
                    <th>User name</th>
                    <th>e-mail</th>
                    <th># Active Jobs</th>
                    <th>Another</th>
                    </tr></thead>
                    <tbody>'''

        content += table_strstart

        ## Getting number of users
        numUsers = len( listUsers )

        ## Looping through users
        if numUsers > 0:

            for userId in listUsers.keys():

                # Starting new row
                content += '<tr>'
                # Parsing data from qstat
                userParsed = listUsers[ userId ]

                # Getting the number of active jobs for this user.
                listActiveJobs = database.getbyUser_running( userParsed['userId'] )
                if listActiveJobs == None:
                    numActiveJobs = 'Zero jobs'
                else:
                    numActiveJobs = str(len(listActiveJobs)) + ' jobs'

                # Writing the info into the row
                content +=  '<td><a href="/user_details?userId=' \
                            + str(userParsed['userId']) + '">' \
                            + userParsed['username'][:12]  + '</td>' + \
                            '<td>' + userParsed['email']  + '</td>' + \
                            '<td>' + str(numActiveJobs) + '</td>' + \
                            '<td> </td>'
                ## End of row
                content += '</tr>'

        content += '</tbody></table></div>'


        ## Closing the connection with the database
        database.close()

        self.render(os.path.join(rootdir,"pages/index.html"), title="Telescope server",
                    content = content,
                    top=open(os.path.join(rootdir,"pages/top.html")).read(),
                    bottom=open(os.path.join(rootdir,"pages/bottom.html")).read()
                    )

        return
