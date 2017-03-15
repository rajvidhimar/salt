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
        result = self.caller.cmd('mac_min', 'junos.facts')
        self.assertTrue(result['mac_min']['out'])
        self.assertIsInstance(result['mac_min']['facts'], dict)
        self.assertTrue('hostname' in result['mac_min']['facts'])
        self.assertTrue('model' in result['mac_min']['facts'])
        self.assertTrue('version_info' in result['mac_min']['facts'])

    def test_facts_refresh(self):
        self.caller.cmd('mac_min', 'junos.install_config', ['salt://name.set'])
        result = self.caller.cmd('mac_min', 'junos.facts_refresh')
        self.assertEqual(result['mac_min']['facts']['hostname'], 'salt-testing')
        self.assertTrue(result['mac_min']['out'])
        self.caller.cmd('mac_min', 'junos.rollback', [1])

    def test_set_hostname_no_name(self):
        result = self.caller.cmd('mac_min', 'junos.set_hostname')
        self.assertEqual(result['mac_min']['message'], 'Please provide the hostname.')
        self.assertFalse(result['mac_min']['out'])

    def test_set_hostname(self):
        result = self.caller.cmd('mac_min', 'junos.set_hostname', ['test'])
        self.assertEqual(result['mac_min']['message'], 'Successfully changed hostname.')
        self.assertTrue(result['mac_min']['out'])
        name = self.caller.cmd('mac_min', 'junos.cli', ['show configuration system host-name'])
        self.assertEqual(str(name['mac_min']['message']), '\nhost-name test;\n' )
        self.caller.cmd('mac_min', 'junos.rollback', [1])

    def test_commit(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set system host-name salty')
        dev.close()
        result = self.caller.cmd('mac_min', 'junos.commit')
        self.assertEqual(result['mac_min']['message'], 'Commit Successful.',)
        self.assertTrue(result['mac_min']['out'])
        self.caller.cmd('mac_min', 'junos.rollback', [1])

    def test_diff(self):
        dev = Device(host='10.221.141.48', user='regress', passwd='MaRtInI')
        dev.open()
        cu = Config(dev)
        cu.load('set interfaces ge-0/0/1 description salt-test')
        dev.close()
        result = self.caller.cmd('mac_min', 'junos.diff')
        self.assertEqual(result['mac_min']['message'], '\n[edit interfaces]\n+   ge-0/0/1 {\n+       description salt-test;\n+   }\n', )
        self.assertTrue(result['mac_min']['out'])
        self.caller.cmd('mac_min', 'junos.rollback')

    def test_diff_exception(self):
        result = self.caller.cmd('mac_min', 'junos.diff', [0.1])
        self.assertTrue('RpcError' and 'message: error: invalid rollback value: 0.1' in result['mac_min']['message'])
        self.assertFalse(result['mac_min']['out'])

    def test_cli_without_args(self):
        result = self.caller.cmd('mac_min', 'junos.cli')
        self.assertEqual(result['mac_min']['message'], 'Please provide the CLI command to be executed.')
        self.assertFalse(result['mac_min']['out'])

    def test_cli(self):
        result = self.caller.cmd('mac_min', 'junos.cli', ['show system commit revision'])
        self.assertTrue('Revision:' in result['mac_min']['message'])
        self.assertTrue(result['mac_min']['out'])

    def test_cli_format_xml(self):
        result = self.caller.cmd('mac_min', 'junos.cli', ['show system commit revision', 'xml'])
        self.assertTrue('commit-revision-information' in result['mac_min']['message']
                     and 'revision' in result['mac_min']['message']['commit-revision-information'])
        self.assertTrue(result['mac_min']['out'])

    def test_cli_exception(self):
        result = self.caller.cmd('mac_min', 'junos.cli', ['cause error'])
        self.assertTrue('RpcError' and 'message: syntax error, expecting <command> or </command>' in result['mac_min']['message'] )

    def test_cli_with_dest_arg(self):
        result = self.caller.cmd('mac_min', 'junos.cli', ['show system commit revision'], kwarg = {'dest': '/srv/salt/delete_me'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.read().split(' ',2)[0], '\nRevision:')
            self.assertTrue('Revision:' in result['mac_min']['message'])
            self.assertTrue(result['mac_min']['out'])
        os.remove('/srv/salt/delete_me')
