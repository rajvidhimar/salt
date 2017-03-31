import salt.client
import unittest
from nose.plugins.attrib import attr
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
import os

@attr('functional')
class TestJunosModule(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.caller = salt.client.LocalClient()
        self.dev = Device(host='10.221.129.70', user='regress', passwd='MaRtInI')
        self.dev.open()
        self.cu = Config(self.dev)

    @classmethod
    def tearDownClass(self):
        self.dev.close()

    def test_facts_refresh(self):
        self.caller.cmd('dev', 'junos.install_config', ['salt://name.set'])
        result = self.caller.cmd('dev', 'junos.facts_refresh')
        self.assertEqual(result['dev']['facts']['hostname'], 'salt-testing')
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_facts(self):
        result = self.caller.cmd('dev', 'junos.facts')
        self.assertTrue(result['dev']['out'])
        self.assertIsInstance(result['dev']['facts'], dict)
        self.assertTrue('hostname' in result['dev']['facts'])
        self.assertTrue('model' in result['dev']['facts'])
        self.assertTrue('version_info' in result['dev']['facts'])

    def test_rpc_without_args(self):
        result = self.caller.cmd('dev', 'junos.rpc')
        self.assertEqual(result['dev']['message'], 'Please provide the rpc to execute.')
        self.assertFalse(result['dev']['out'])

    def test_rpc_xml_with_args(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-interface-information', '/srv/salt/delete_me'], kwarg={'terse': True, 'interface_name': 'lo0'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.readline(), '<interface-information style="terse">\n')
            self.assertEqual(len(result['dev']['rpc_reply']['interface-information']['physical-interface']), 4)
            self.assertEqual(result['dev']['rpc_reply']['interface-information']['physical-interface']['name'], 'lo0')
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

    def test_rpc_json_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-interface-information', '/srv/salt/delete_me', 'json'],
                                 kwarg={'terse': True, 'interface_name': 'lo0'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.readlines()[1], ' "interface-information": [\n')
            self.assertEqual(type(result['dev']['rpc_reply']['interface-information']), list)
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

    # def test_rpc_text_with_dest_arg(self):
    #     result = self.caller.cmd('dev', 'junos.rpc', ['get-interface-information', '/srv/salt/delete_me', 'text'],
    #                              kwarg={'terse': True, 'interface_name': 'lo0'})
    #     with open('/srv/salt/delete_me', 'r') as fp:
    #         print type(fp.readlines())
    #         self.assertEqual(" ['\n', 'Interface", fp.readlines())
    #         self.assertEqual(type(result['dev']['rpc_reply']), str)
    #         self.assertTrue(result['dev']['out'])
    #     os.remove('/srv/salt/delete_me')

    def test_rpc_exception(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['incorrect-rpc'])
        self.assertTrue('RPC execution failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_rpc_get_config_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-config', '/srv/salt/delete_me', 'json'], kwarg={'filter': '<configuration><system/></configuration>'})

        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.readlines()[1],  ' "configuration": {\n')
            self.assertTrue('configuration' in result['dev']['rpc_reply'])
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

    def test_rpc_get_config_json_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-config', '', 'json'],
                                 kwarg={'filter': '<configuration><system/></configuration>'})
        self.assertTrue('@' in result['dev']['rpc_reply']['configuration'])
        self.assertTrue(result['dev']['out'])

    def test_rpc_get_config_text_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-config', '', 'json'],
                                 kwarg={'filter': '<configuration><system/></configuration>'})
        self.assertTrue(type(result['dev']['rpc_reply']), str)
        self.assertTrue(result['dev']['out'])

    def test_rpc_get_config_exception(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-config', '', 'json'],
                                 kwarg={'filter': '<configuration><invalid/></configuration>'})
        self.assertTrue('RPC execution failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_set_hostname_no_name(self):
        result = self.caller.cmd('dev', 'junos.set_hostname')
        self.assertEqual(result['dev']['message'], 'Please provide the hostname.')
        self.assertFalse(result['dev']['out'])

    # def test_set_hostname(self):
    #     result = self.caller.cmd('dev', 'junos.set_hostname', ['test'])
    #     self.assertEqual(result['dev']['message'], 'Successfully changed hostname.')
    #     self.assertTrue(result['dev']['out'])
    #     name = self.caller.cmd('dev', 'junos.cli', ['show configuration system host-name'])
    #     self.assertEqual(str(name['dev']['message']), '\nhost-name test;\n' )
    #     self.caller.cmd('dev', 'junos.rollback', [1])

    def test_set_hostname_load_exception(self):
        result = self.caller.cmd('dev', 'junos.set_hostname', ['Invalid#'])
        self.assertTrue('Could not load configuration due to error' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])


    def test_set_hostname_commit_check_exception(self):
        self.cu.lock()
        self.cu.load('set interfaces lo0 unit 57 family inet address 10.0.0.1/32')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.set_hostname', ['test-name'])
        self.assertTrue('Commit check failed with' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    # def test_set_hostname_commit_exception(self):
    #     result = self.caller.cmd('dev', 'junos.set_hostname', ['test-name'], kwarg={'confirm': 0.1})
    #     self.assertTrue('Successfully loaded host-name but commit failed with' in result['dev']['message'])
    #     self.assertFalse(result['dev']['out'])
    #     self.caller.cmd('dev', 'junos.rollback')

    # def test_commit(self):
    #     self.cu.lock()
    #     self.cu.load('set interfaces ge-0/0/3 description "salt test"')
    #     self.cu.unlock()
    #     result = self.caller.cmd('dev', 'junos.commit')
    #     self.assertEqual(result['dev']['message'], 'Commit Successful.',)
    #     self.assertTrue(result['dev']['out'])
    #     output = self.caller.cmd('dev', 'junos.cli', ['show interfaces ge-0/0/3 descriptions'])
    #     self.assertTrue('ge-0/0/3' and 'salt test' in output['dev']['message'])
    #     self.caller.cmd('dev', 'junos.rollback', [1])

    def test_commit_check_exception(self):
        #self.cu.lock()
        self.cu.load('set interfaces lo0 unit 57 family inet address 10.0.0.1/32')
        #self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.commit')
        self.assertTrue('Commit check failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_commit_exception(self):
        result = self.caller.cmd('dev', 'junos.commit', kwarg = {'confirm': 0.1})
        self.assertTrue('Commit check succeeded but actual commit failed with' in result['dev']['message'] )
        self.assertFalse(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_commit_with_detail_as_arg(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/2 description "salt test"')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.commit', kwarg={'detail': True})
        self.assertTrue('routing-engine' in result['dev']['message'])
        self.assertTrue('name' in result['dev']['message']['routing-engine'])
        self.assertTrue(isinstance(result['dev']['message']['routing-engine']['progress-indicator'], list))
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_rollback(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/4 description "salt test"')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.rollback')
        self.assertEqual(result['dev']['message'], 'Rollback successful')
        self.assertTrue(result['dev']['out'])
        output = self.caller.cmd('dev', 'junos.cli', ['show interfaces ge-0/0/4 descriptions'])
        self.assertEqual(output['dev']['message'], '')

    def test_rollback_exception(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/3 description "salt test"')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.rollback', [0.1])
        self.assertTrue('Rollback failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_rollback_with_id_arg(self):
        self.caller.cmd('dev', 'junos.set_hostname', ['test-name'])
        result = self.caller.cmd('dev', 'junos.rollback', [1])
        self.assertEqual(result['dev']['message'], 'Rollback successful')
        self.assertTrue(result['dev']['out'])
        name = self.caller.cmd('dev', 'junos.cli', ['show configuration system host-name'])
        self.assertTrue('host-name re0;' in name['dev']['message'])

    def test_diff(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/1 description salt-test')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.diff')
        print result['dev']
        # self.assertTrue('description salt-test;' in result['dev']['message'] and 'ge-0/0/1' in result['dev']['message'])
        # self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_diff_exception(self):
        result = self.caller.cmd('dev', 'junos.diff', [0.1])
        self.assertTrue('RpcError' and 'message: error: invalid rollback value: 0.1' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    # def test_diff_with_id_arg(self):
    #     pass

    def test_ping_without_args(self):
        result = self.caller.cmd('dev', 'junos.ping')
        self.assertEqual(result['dev']['message'], 'Please specify the destination ip to ping.')
        self.assertFalse(result['dev']['out'])

    def test_ping(self):
        result = self.caller.cmd('dev', 'junos.ping', ['127.0.0.1'])
        self.assertTrue('ping-results' in result['dev']['message'])
        self.assertTrue(result['dev']['out'])

    def test_ping_with_count_and_ttl(self):
        result = self.caller.cmd('dev', 'junos.ping', ['127.0.0.1'], kwarg={'count': 3, 'ttl': 4})
        self.assertEqual(result['dev']['message']['ping-results']['probe-results-summary']['probes-sent'], '3')
        self.assertTrue(result['dev']['out'])

    def test_ping_exception(self):
        result = self.caller.cmd('dev', 'junos.ping', ['127.0.0.1'], kwarg={'count': 0.1})
        self.assertTrue('Execution failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_cli_without_args(self):
        result = self.caller.cmd('dev', 'junos.cli')
        self.assertEqual(result['dev']['message'], 'Please provide the CLI command to be executed.')
        self.assertFalse(result['dev']['out'])

    def test_cli(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision'])
        self.assertTrue('Revision:' in result['dev']['message'])
        self.assertTrue(result['dev']['out'])

    def test_cli_format_xml(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision', 'xml'])
        self.assertTrue('commit-revision-information' in result['dev']['message']
                     and 'revision' in result['dev']['message']['commit-revision-information'])
        self.assertTrue(result['dev']['out'])

    def test_cli_format_as_empty_string(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision', ''])
        self.assertTrue('Revision:' in result['dev']['message'])
        self.assertTrue(result['dev']['out'])

    # def test_cli_exception(self):
    #     result = self.caller.cmd('dev', 'junos.cli', ['cause error'])
    #     print result
    #     self.assertTrue('Execution failed due to' in result['dev']['message'])
    #     self.assertFalse(result['dev']['out'])


    def test_cli_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision'], kwarg = {'dest': '/srv/salt/delete_me'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.read().split(' ',2)[0], '\nRevision:')
            self.assertTrue('Revision:' in result['dev']['message'])
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

    def test_shutdown_without_args(self):
        result = self.caller.cmd('dev', 'junos.shutdown')
        self.assertEqual(result['dev']['message'], 'Provide either one of the arguments: shutdown or reboot.')
        self.assertFalse(result['dev']['out'])
