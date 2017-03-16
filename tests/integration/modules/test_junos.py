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

    def test_facts(self):
        result = self.caller.cmd('dev', 'junos.facts')
        self.assertTrue(result['dev']['out'])
        self.assertIsInstance(result['dev']['facts'], dict)
        self.assertTrue('hostname' in result['dev']['facts'])
        self.assertTrue('model' in result['dev']['facts'])
        self.assertTrue('version_info' in result['dev']['facts'])

    def test_facts_refresh(self):
        self.caller.cmd('dev', 'junos.install_config', ['salt://name.set'])
        result = self.caller.cmd('dev', 'junos.facts_refresh')
        self.assertEqual(result['dev']['facts']['hostname'], 'salt-testing')
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_set_hostname_no_name(self):
        result = self.caller.cmd('dev', 'junos.set_hostname')
        self.assertEqual(result['dev']['message'], 'Please provide the hostname.')
        self.assertFalse(result['dev']['out'])

    def test_set_hostname(self):
        result = self.caller.cmd('dev', 'junos.set_hostname', ['test'])
        self.assertEqual(result['dev']['message'], 'Successfully changed hostname.')
        self.assertTrue(result['dev']['out'])
        name = self.caller.cmd('dev', 'junos.cli', ['show configuration system host-name'])
        self.assertEqual(str(name['dev']['message']), '\nhost-name test;\n' )
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_commit(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set system host-name salty')
        dev.close()
        result = self.caller.cmd('dev', 'junos.commit')
        self.assertEqual(result['dev']['message'], 'Commit Successful.',)
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_commit_check_exception(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set interfaces lo0 unit 57 family inet address 10.0.0.1/32')
        dev.close()
        result = self.caller.cmd('dev', 'junos.commit')
        self.assertTrue('Commit check failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_commit_exception(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set interfaces ge-0/0/1 description "salt test"')
        dev.close()
        result = self.caller.cmd('dev', 'junos.commit', kwarg = {'confirm': 0.1})
        self.assertTrue('Commit check succeeded but actual commit failed with' in result['dev']['message'] )
        self.assertFalse(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_commit_with_detail_as_arg(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set interfaces ge-0/0/2 description "salt test"')
        dev.close()
        result = self.caller.cmd('dev', 'junos.commit', kwarg={'detail': True})
        self.assertTrue('routing-engine' in result['dev']['message'])
        self.assertTrue('name' in result['dev']['message']['routing-engine'])
        self.assertTrue(isinstance(result['dev']['message']['routing-engine']['progress-indicator'], list))
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback', [1])

    def test_diff(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set interfaces ge-0/0/1 description salt-test')
        dev.close()
        result = self.caller.cmd('dev', 'junos.diff')
        self.assertEqual(result['dev']['message'], '\n[edit interfaces]\n+   ge-0/0/1 {\n+       description salt-test;\n+   }\n', )
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_diff_exception(self):
        result = self.caller.cmd('dev', 'junos.diff', [0.1])
        self.assertTrue('RpcError' and 'message: error: invalid rollback value: 0.1' in result['dev']['message'])
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

    def test_cli_exception(self):
        result = self.caller.cmd('dev', 'junos.cli', ['cause error'])
        self.assertTrue('RpcError' and 'message: syntax error, expecting <command> or </command>' in result['dev']['message'] )

    def test_cli_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision'], kwarg = {'dest': '/srv/salt/delete_me'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.read().split(' ',2)[0], '\nRevision:')
            self.assertTrue('Revision:' in result['dev']['message'])
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')
