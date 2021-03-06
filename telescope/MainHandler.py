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


class MainHandler(tornado.web.RequestHandler):
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

        if self.get_secure_cookie("query"):

            # Grabbing the value stored in the secure cookie query
            queryText = str( self.get_secure_cookie("query").decode("utf-8") )

            if queryText[:2] == 'a:':

                actionID, arg = utils.cookieQueryParser(queryText)

                content += "<div id=\"WARNING\" style=\"position: fixed; min-width: 10px; padding-right:30px; padding-left:30px; padding-top: 20px; padding-bottom: 20px; top: 200px; left: 40%; background-color:#BFB; font-size:15pt; text-align: center; border: 1px solid #0A0; border-radius: 10px;\">"

                if actionID == 'stop job':
                    self.set_secure_cookie("query","")
                    content += "Stopped job ID <b>" + arg['jobid'] + "</b>"

                content += "</div>"

            content += "<script>$(document).ready(function(){ $(\"#WARNING\").delay(3000).fadeOut(1500); });</script>"

            self.set_secure_cookie("query","")

        content += "<p>Welcome to Telescope Server! Below you will find a list of your jobs. Click on the job ID to see more details.</p>"


        table_strstart = '''<div class="page-header">
                    <table class="table table-striped">
                    <thead><tr>
                    <th width=100px>Job ID</th>
                    <th width=100px>User</th>
                    <th>Job name</th>
                    <th>state</th>
                    <th>Started in</th>
                    <th></th>
                    </tr></thead>
                    <tbody>'''

        content += table_strstart

        # Grabt the latest status from the servers
        curStatus  = self.queueMonitor.getMonitorCurrentStatus()
        # Getting number of jobs
        numJobs = len( curStatus )


        if numJobs > 0:

            # Getting set of keys
            setJobKeys = np.sort( list(curStatus.keys()) )

            for jobKey in setJobKeys:

                # Starting new row
                content += '<tr>'
                # Parsing data from qstat
                statParserd = curStatus[jobKey]

                # Writing the info into the row
                content +=  '<td><a href="/experiment?jobID=' + str(statParserd['jobId']) + '">' + \
                            str(statParserd['jobId']) + '</a></td>' + \
                            '<td>' + statParserd['username'][:8]  + '</td>' + \
                            '<td>' + statParserd['jobName']  + '</td>' + \
                            '<td>' + \
                            utils.parseStatus2HTML( statParserd['jobStatus'] ) \
                            + '</td>' + \
                            '<td>' + statParserd['startDate']   + '</td>' + \
                            '<td><a href="/query?jobID=' + str(statParserd['jobId']) + \
                            '&act=0" style="color:#F00;">X</a></td>'
                ## End of row
                content += '</tr>'

        content += '</tbody></table></div>'

        self.db = db( self.databasePath )
        parsedFinishedJobs = self.db.getAllFinished()
        self.db.close()

        if parsedFinishedJobs != None:
            if len( parsedFinishedJobs ) > 0:

                content += "<br /><h3>List of finished jobs (under development)</3>" + table_strstart

                for jobKey in parsedFinishedJobs.keys():

                    # Starting new row
                    content += '<tr>'
                    # Parsing data from qstat
                    statParserd = parsedFinishedJobs[jobKey]

                    # Writing the info into the row
                    content +=  '<td>' + \
                                str(statParserd['jobId']) + '</a></td>' + \
                                '<td>' + statParserd['username'][:8]  + '</td>' + \
                                '<td>' + statParserd['jobName']  + '</td>' + \
                                '<td>Finished with status 0</td>' + \
                                '<td>--</td>'
                    ## End of row
                    content += '</tr>'

                content += '</tbody></table></div>'


        if curStatus == {}:
            content += "<script>setTimeout(function(){ window.location.reload(1); }, 5000);</script>"

        self.render(os.path.join(rootdir,"pages/index.html"), title="Telescope server",
                    content = content,
                    top=open(os.path.join(rootdir,"pages/top.html")).read(),
                    bottom=open(os.path.join(rootdir,"pages/bottom.html")).read()
                    )

        return
