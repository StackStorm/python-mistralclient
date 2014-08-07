# Copyright (c) 2014 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

from tempest import cli


class MistralCLIAuth(cli.ClientTestBase):

    def mistral(self, action, flags='', params='', admin=True, fail_ok=False,
                keystone_version=3):
        """Executes Mistral command."""
        return self.cmd_with_auth(
            'mistral', action, flags, params, admin, fail_ok, keystone_version)


class SimpleMistralCLITests(MistralCLIAuth):
    """Basic tests, check '-list', '-help' commands."""

    @classmethod
    def setUpClass(cls):
        super(SimpleMistralCLITests, cls).setUpClass()

    def test_command_help(self):
        mistral_help = self.mistral('--help')

        self.assertIn('Command-line interface to the Mistral APIs',
                      mistral_help)
        self.assertIn('Commands:', mistral_help)

        expected_commands = ('complete', 'execution-create',
                             'execution-delete', 'execution-get',
                             'execution-list', 'execution-update',
                             'help', 'task-get', 'task-list',
                             'task-update', 'workbook-create',
                             'workbook-delete', 'workbook-get',
                             'workbook-get-definition', 'workbook-list',
                             'workbook-update', 'workbook-upload-definition')
        for command in expected_commands:
            self.assertIn(command, mistral_help)

    def test_workbooks_list(self):
        workbooks = self.parser.listing(self.mistral('workbook-list'))
        self.assertTableStruct(workbooks,
                               ['Name', 'Description', 'Tags'])

    def test_executions_list(self):
        executions = self.parser.listing(
            self.mistral('execution-list', params='""'))
        self.assertTableStruct(executions,
                               ['ID', 'Workbook', 'Task', 'State'])

    def test_tasks_list(self):
        tasks = self.parser.listing(
            self.mistral('task-list', params='"", ""'))
        self.assertTableStruct(tasks,
                               ['ID', 'Workbook', 'Execution', 'Name',
                                'Description', 'State', 'Tags'])


class ClientTestBase(MistralCLIAuth):

    @classmethod
    def setUpClass(cls):
        super(ClientTestBase, cls).setUpClass()

        cls.definition = os.path.relpath(
            'functionaltests/hello.yaml', os.getcwd())

    def tearDown(self):
        super(ClientTestBase, self).tearDown()

        for wb in self.parser.listing(self.mistral('workbook-list')):
            if wb['Name'] != "<none>":
                execs = self.parser.listing(self.mistral(
                    'execution-list', params='{0}'.format(wb['Name'])))
                ids = [ex['ID'] for ex in execs]
                for id in ids:
                    if id != "<none>":
                        self.parser.listing(self.mistral(
                            'execution-delete',
                            params='"{0}" "{1}"'.format(wb['Name'], id)))

                self.parser.listing(self.mistral(
                    'workbook-delete', params=wb['Name']))

    def get_value_of_field(self, obj, field):
        return [o['Value'] for o in obj
                if o['Field'] == "{0}".format(field)][0]


class WorkbookCLITests(ClientTestBase):
    """Test suite checks commands to work with workbooks."""

    @classmethod
    def setUpClass(cls):
        super(WorkbookCLITests, cls).setUpClass()

    def test_workbook_create_delete(self):
        wb = self.parser.listing(self.mistral('workbook-create', params='wb'))
        self.assertTableStruct(wb, ['Field', 'Value'])

        name = self.get_value_of_field(wb, "Name")
        self.assertEqual('wb', name)

        wbs = self.parser.listing(self.mistral('workbook-list'))
        self.assertIn('wb', [workbook['Name'] for workbook in wbs])

        self.parser.listing(self.mistral('workbook-delete', params='wb'))

        wbs = self.parser.listing(self.mistral('workbook-list'))
        self.assertNotIn('wb', [workbook['Name'] for workbook in wbs])

    def test_workbook_update(self):
        self.parser.listing(self.mistral('workbook-create', params='wb'))

        wb = self.parser.listing(self.mistral(
            'workbook-update', params='"wb" "Test Description" "tag"'))
        self.assertTableStruct(wb, ['Field', 'Value'])

        name = self.get_value_of_field(wb, "Name")
        description = self.get_value_of_field(wb, "Description")
        tags = self.get_value_of_field(wb, "Tags")

        self.assertEqual('wb', name)
        self.assertIn('Test Description', description)
        self.assertIn('tag', tags)

    def test_workbook_upload_get_definition(self):
        self.parser.listing(self.mistral('workbook-create', params='wb'))

        self.parser.listing(self.mistral(
            'workbook-upload-definition',
            params='"wb" "{0}"'.format(self.definition)))

        definition = self.mistral('workbook-get-definition', params='wb')
        self.assertNotIn('404 Not Found', definition)


class ExecutionCLITests(ClientTestBase):
    """Test suite checks commands to work with executions."""

    def setUp(self):
        super(ExecutionCLITests, self).setUp()
        self.mistral('workbook-create', params='wb')
        self.mistral('workbook-upload-definition',
                     params='"wb" "{0}"'.format(self.definition))

    def tearDown(self):
        super(ExecutionCLITests, self).tearDown()

    def test_execution_create_delete(self):
        execution = self.parser.listing(self.mistral(
            'execution-create', params='"wb" "hello" "{}"'))

        self.assertTableStruct(execution, ['Field', 'Value'])

        exec_id = self.get_value_of_field(execution, 'ID')
        wb = self.get_value_of_field(execution, 'Workbook')
        task = self.get_value_of_field(execution, 'Task')
        status = self.get_value_of_field(execution, 'State')

        self.assertEqual('wb', wb)
        self.assertEqual('hello', task)
        self.assertEqual('RUNNING', status)

        execs = self.parser.listing(
            self.mistral('execution-list', params='wb'))
        self.assertIn(exec_id, [ex['ID'] for ex in execs])
        self.assertIn(wb, [ex['Workbook'] for ex in execs])
        self.assertIn(task, [ex['Task'] for ex in execs])
        self.assertIn('SUCCESS', [ex['State'] for ex in execs])

        self.parser.listing(self.mistral(
            'execution-delete', params='"wb" "{0}"'.format(exec_id)))

        execs = self.parser.listing(
            self.mistral('execution-list', params='wb'))
        self.assertNotIn(exec_id, [ex['ID'] for ex in execs])

    def test_update_execution(self):
        execution = self.parser.listing(self.mistral(
            'execution-create', params='"wb" "hello" "{}"'))

        self.assertTableStruct(execution, ['Field', 'Value'])

        exec_id = self.get_value_of_field(execution, 'ID')
        status = self.get_value_of_field(execution, 'State')

        self.assertEqual('RUNNING', status)

        execution = self.parser.listing(self.mistral(
            'execution-update', params='"wb" "{0}" "STOPPED"'.format(exec_id)))

        self.assertTableStruct(execution, ['Field', 'Value'])

        updated_exec_id = self.get_value_of_field(execution, 'ID')
        status = self.get_value_of_field(execution, 'State')

        self.assertEqual(exec_id, updated_exec_id)
        self.assertEqual('STOPPED', status)

    def test_get_execution(self):
        execution = self.parser.listing(self.mistral(
            'execution-create', params='"wb" "hello" "{}"'))

        exec_id = self.get_value_of_field(execution, 'ID')

        execution = self.parser.listing(self.mistral(
            'execution-get', params='"wb" "{0}"'.format(exec_id)))

        gotten_id = self.get_value_of_field(execution, 'ID')
        wb = self.get_value_of_field(execution, 'Workbook')
        task = self.get_value_of_field(execution, 'Task')

        self.assertEqual(exec_id, gotten_id)
        self.assertEqual('wb', wb)
        self.assertEqual('hello', task)


class TaskCLITests(ClientTestBase):
    """Test suite checks commands to work with tasks."""

    def test_get_task(self):
        self.mistral('workbook-create', params='wb')
        self.mistral('workbook-upload-definition',
                     params='"wb" "{0}"'.format(self.definition))

        execution = self.parser.listing(self.mistral(
            'execution-create', params='"wb" "hello" "{}"'))
        exec_id = self.get_value_of_field(execution, 'ID')

        tasks = self.parser.listing(
            self.mistral('task-list', params='"wb" "{0}"'.format(exec_id)))

        task_id = [task['ID'] for task in tasks][0]

        task = self.parser.listing(self.mistral(
            'task-get', params='"wb" "hello" "{0}"'.format(task_id)))

        gotten_id = self.get_value_of_field(task, 'ID')
        wb = self.get_value_of_field(task, 'Workbook')

        self.assertEqual(task_id, gotten_id)
        self.assertEqual('wb', wb)
