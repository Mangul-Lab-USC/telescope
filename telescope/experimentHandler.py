## standard libraries
import sys, os, io
import datetime, time

## to create threads
import multiprocessing as mp

## For the web service
import tornado.ioloop
import tornado.web as web
from tornado.ioloop import IOLoop
from tornado.web import asynchronous, RequestHandler, Application
from tornado.httpclient import AsyncHTTPClient
import logging


## Import internal modules
from telescope.sshKernel import tlscpSSH
from telescope.dbKernel import db
import telescope.utils as utils

rootdir=os.path.dirname(__file__)

class experimentHandler(tornado.web.RequestHandler):

    def initialize(self, ServerInterface, queueMonitor, databasePath ):

        ## ServerInterface object
        self.ServerInterface = ServerInterface

        # Server's queue monitoringInterval
        self.queueMonitor = queueMonitor

        self.databasePath = databasePath

        return


    def get(self):

        self.jobID        = self.get_argument('jobID', '-1')
        self.outputStatus = self.get_argument('outputFormat', '0')


        if self.jobID == '-1':
            content = "<p>Experiment ID not provided.</p>"
            content += "<script>window.location.href = \"./\";</script>"

        else:

            # Grabt the latest status from the servers
            curStatus  = self.queueMonitor.getMonitorCurrentStatus()

            if int(self.jobID) in curStatus.keys():

                # Getting the specific line of the qstatus
                statParserd = curStatus[ int(self.jobID) ]

                ## Connecting to the server through SSH
                self.ServerInterface.startSSHconnection( username = statParserd['username'] )

                ## Retrieving information about the job
                curStatJ = self.ServerInterface.qstatJobQuery( self.jobID )

                # Name of the script
                sgeScriptRun = curStatJ.split( 'script_file:' )[1].split('\n')[0].replace(' ','')
                # Working directory
                sgeOWorkDir  = curStatJ.split( 'sge_o_workdir:' )[1].split('\n')[0].replace(' ','')
                # Capturing Job Name -- if job name is too long, qstat only shows
                # the beginning of the job name. This ensures we get the full name.
                sgeJobName   = curStatJ.split( 'job_name:' )[1].split('\n')[0].replace(' ','')

                ## Accessing the current output
                if self.outputStatus == '1':
                    numLines = 200  ## cap in 200 lines!
                else:
                    numLines = 20


                ## Grabbing the first 20 lines of the script source file
                scriptContent = self.ServerInterface.grabFile( sgeOWorkDir + '/' + sgeScriptRun,
                                                                nlines=20, order=1 )

                if statParserd['jobStatus'] == 'running' :

                    db_ = db( './telescopedb' )
                    dbJobInfo = db_.getbyjobId( int(self.jobID) )
                    db_.close()

                    curErrMsg  = self.ServerInterface.grabErrOut( sgeJobName, self.jobID,
                                                        sgeOWorkDir, nlines=numLines )

                    # Grabbing the last 20 lines of the output file
                    outputPath = os.path.join( sgeOWorkDir, dbJobInfo[int(self.jobID)]['outputFile'] )
                    curOutput = self.ServerInterface.grabFile(outputPath, nlines=20, order=-1 )

                else:

                    curOutput = None
                    curErrMsg = None


                ## Terminating the SSH connection
                self.ServerInterface.closeSSHconnection()

                ## Constructing the info to post on the web page
                content = self.constructContent( qstat = curStatus, qstat_parsed=statParserd,
                                                 catStat = curOutput,
                                                 catErrm = curErrMsg,
                                                 workDir = sgeOWorkDir,
                                                 scriptName = sgeScriptRun,
                                                 scriptContent = scriptContent
                                                )
            else:

                content = "<script>window.location.href = \"./\";</script>"



        ## Rendering the page
        self.render('pages/index.html', title="Farore's wind",
                    content = content,
                    top=open(rootdir+"/pages/top.html").read(),
                    bottom=open(rootdir+"/pages/bottom.html").read())

        return




    def constructContent(self, qstat = '', qstat_parsed = [], catStat = '', catErrm = '',
                            workDir = '', scriptName = '', scriptContent = ''):
        """
        Constructs the content of the page describing the status of the
        """

        content = '<div class="page-header">' + \
                    '<table class="table table-striped">' + \
                    '<thead><tr>' + \
                    '<th width=100px>Job ID</th>' + \
                    '<th>Job name</th>' + \
                    '<th>State</th>' + \
                    '<th>Started in</th>' + \
                    '</tr></thead>'+ \
                    '<tbody>\n'


        # Starting new row
        content += '<tr>'
        # Writing the info into the row
        content +=  '<td><a href="/experiment?jobID=' + str(qstat_parsed['jobId']) + '">' + \
                    str(qstat_parsed['jobId']) + '</a></td>' + \
                    '<td>' + qstat_parsed['jobName']  + '</td>' + \
                    '<td>' + qstat_parsed['jobStatus'] + '</td>' + \
                    '<td>' + qstat_parsed['startDate']   + '</td>'
        ## End of row
        content += '</tr>'
        content += '</tbody></table></div>'

        content += "<p><b>Script name:</b> " + scriptName + "</p>"
        content += "<p><b>Directory:</b> " + workDir + "</p>"

        content += "<h3>Content of the script file:</h3>"
        content += "<blockquote>" + scriptContent.replace('\n', '<br />') + "</blockquote>"

        if catStat != None:
            if self.outputStatus == '1':
                content += "<h3>Current status of the output</h3>"
                #content += "<p>Click <a href=\"./experiment?expID=1&outputFormat=0\">here</a> to see the only the last 20 lines of the output file.</p>"
            else:
                content += "<h3>Current status of the output (last 20 lines)</h3>"
                #content += "<p>Click <a href=\"./experiment?expID=1&outputFormat=1\">here</a> to see the full output file.</p>"

            content += "<blockquote>" + catStat.replace('\n', '<br />') + "</blockquote>"

        if catErrm != None:
            if self.outputStatus == '1':
                content += "<h3>Error messages:</h3>"
                #content += "<p>Click <a href=\"./experiment?expID=1&outputFormat=0\">here</a> to see the only the last 20 lines of the output file.</p>"
            else:
                content += "<h3>Error messages (last 20 lines):</h3>"
                #content += "<p>Click <a href=\"./experiment?expID=1&outputFormat=1\">here</a> to see the full output file.</p>"

            content += "<blockquote>" + catErrm.replace('\n', '<br />') + "</blockquote>"

        return content
