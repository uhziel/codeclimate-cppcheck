import json
import subprocess
import sys
import tempfile
import os

from lxml import etree

from command import Command
from issue_formatter import IssueFormatter
from workspace import Workspace
import rediswq

CONFIG_FILE_PATH = '/config.json'


class Runner:
    """Runs cppcheck, collects and reports results."""
    def __init__(self):
        self._config = None


    def run(self):
        config = self._decode_config()
        self._print_debug('[cppcheck] config: {}'.format(config))

        workspace = Workspace(config.get('include_paths'))
        workspace_files = workspace.calculate()

        if not len(workspace_files) > 0:
            return

        plugin_config = config.get('config', {})

        wq_url = os.getenv('CODE_ANALYSIS_WORK_QUEUE_URL')
        wq_name = os.getenv('CODE_ANALYSIS_WORK_QUEUE_NAME')

        if wq_url is not None and wq_name is not None:
            self._runAsQueueWorker(plugin_config, workspace, wq_url, wq_name)
            return

        self._print_debug('[cppcheck] analyzing {} files'.format(len(workspace_files)))

        file_list_path = self._build_file_list(workspace_files)

        self._runOnce(plugin_config, workspace, file_list_path, "file_list_path")


    def _runAsQueueWorker(self, plugin_config, workspace, wq_url, wq_name):
        q = rediswq.RedisWQ(name = wq_name, host = wq_url)
        self._print_debug("[cppcheck_wq] Worker with sessionID: " +  q.sessionID())
        self._print_debug("[cppcheck_wq] Initial queue state: empty=" + str(q.empty()))
        while not q.empty():
            item = q.lease(lease_secs=10, block=True, timeout=2) 
            if item is not None:
                itemstr = item.decode("utf-8")
                self._print_debug("[cppcheck_wq] Working on " + itemstr)
                self._runOnce(plugin_config, workspace, itemstr, "checked_file") # actual work 
                q.complete(item)
        else:
            self._print_debug("[cppcheck_wq] Waiting for work")
        self._print_debug("[cppcheck_wq] Queue empty, exiting")
    
    def _runOnce(self, plugin_config, workspace, file_path, file_path_type):

        command = Command(plugin_config, file_path, file_path_type).build()

        self._print_debug('[cppcheck] command: {}'.format(command))

        results = self._run_command(command)
        issues = self._parse_results(results)

        for issue in issues:
            # cppcheck will emit issues for files outside of the workspace,
            # like header files. This ensures that we only emit issues for
            # files in the workspace.
            if issue and workspace.should_include(issue["location"]["path"]):
                print('{}\0'.format(json.dumps(issue)))


    def _decode_config(self):
        contents = open(CONFIG_FILE_PATH).read()

        return json.loads(contents)


    def _build_file_list(self, workspace_files):
        _, path = tempfile.mkstemp()

        with open(path, 'w') as file:
            for workspace_file in workspace_files:
                file.write('{}\n'.format(workspace_file))

        return path


    def _run_command(self, command):
        process = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        _stdout, stderr = process.communicate()

        if process.returncode != 0:
            self._print_debug('[cppcheck] error: {}'.format(stderr))
            sys.exit(process.returncode)

        return stderr


    def _parse_results(self, results):
        root = etree.fromstring(results)
        issues = []

        for node in root:
            if node.tag == 'errors':
                for error in node:
                    issue = IssueFormatter(error).format()
                    issues.append(issue)

        return issues


    def _print_debug(self, message):
        print(message, file=sys.stderr)
