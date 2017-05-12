# -*- coding: utf-8 -*-

import salt.client
import unittest
from nose.plugins.attrib import attr
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
import os
import time
from lxml import etree


@attr('functional')
class TestJunosModule(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.caller = salt.client.LocalClient()
        self.dev = Device(host='10.221.141.165', user='regress', passwd='MaRtInI')
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

    def test_rpc_text_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.rpc', ['get-interface-information', '/srv/salt/delete_me', 'text'],
                                 kwarg={'terse': True, 'interface_name': 'lo0'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertTrue("Interface" in fp.readlines()[1])
            self.assertEqual(type(result['dev']['rpc_reply']), str)
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

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

    def test_rollback_exception(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/3 description "salt test"')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.rollback', [0.1])
        self.assertTrue('Rollback failed due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])
        self.cu.lock()
        self.cu.rollback()
        self.cu.unlock()

    def test_diff(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/5 description "salt test"')
        self.cu.commit()
        self.cu.rollback(rb_id=1)
        self.cu.commit()
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.diff', [1])
        self.assertTrue(' ge-0/0/5' in result['dev']['message'] and 'description "salt test"' in result['dev']['message'])
        self.assertTrue(result['dev']['out'])
        self.caller.cmd('dev', 'junos.rollback')

    def test_diff_exception(self):
        result = self.caller.cmd('dev', 'junos.diff', [0.1])
        self.assertTrue('RpcError' and 'message: error: invalid rollback value: 0.1' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

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

    def test_cli_with_dest_arg(self):
        result = self.caller.cmd('dev', 'junos.cli', ['show system commit revision'], kwarg = {'dest': '/srv/salt/delete_me'})
        with open('/srv/salt/delete_me', 'r') as fp:
            self.assertEqual(fp.read().split(' ',2)[0], '\nRevision:')
            self.assertTrue('Revision:' in result['dev']['message'])
            self.assertTrue(result['dev']['out'])
        os.remove('/srv/salt/delete_me')

    def test_set_hostname_no_name(self):
        result = self.caller.cmd('dev', 'junos.set_hostname')
        self.assertEqual(result['dev']['message'], 'Please provide the hostname.')
        self.assertFalse(result['dev']['out'])

    def test_set_hostname(self):
        result = self.caller.cmd('dev', 'junos.set_hostname', ['test'])
        self.assertEqual(result['dev']['message'], 'Successfully changed hostname.')
        self.assertTrue(result['dev']['out'])
        name = self.caller.cmd('dev', 'junos.cli', ['show configuration system host-name'])
        self.assertEqual(str(name['dev']['message']), '\nhost-name test;\n')
        self.cu.lock()
        self.cu.load('set system host-name re0')
        self.cu.commit()
        self.cu.unlock()

    def test_set_hostname_load_exception(self):
        result = self.caller.cmd('dev', 'junos.set_hostname', ['Invalid#'])
        self.assertTrue('Could not load configuration due to error' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    # def test_set_hostname_commit_exception(self):
    #     result = self.caller.cmd('dev', 'junos.set_hostname', ['test-name'], kwarg={'confirm': 0.1})
    #     self.assertTrue('Successfully loaded host-name but commit failed with' in result['dev']['message'])
    #     self.assertFalse(result['dev']['out'])
    #     self.cu.lock()
    #     self.cu.load('set system host-name re0')
    #     self.cu.commit()
    #     self.cu.unlock()

    def test_commit(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/3 description "salt test"')
        self.cu.commit(confirm=1)
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.commit')
        self.assertEqual(result['dev']['message'], 'Commit Successful.', )
        self.assertTrue(result['dev']['out'])
        time.sleep(90)
        output = self.caller.cmd('dev', 'junos.cli', ['show interfaces ge-0/0/3 descriptions'])
        self.assertTrue('ge-0/0/3' and 'salt test' in output['dev']['message'])
        self.cu.lock()
        self.cu.load('delete interfaces ge-0/0/3 description')
        self.cu.commit()
        self.cu.unlock()

    def test_commit_exception(self):
        result = self.caller.cmd('dev', 'junos.commit', kwarg={'confirm': 0.1})
        self.assertTrue('Commit check succeeded but actual commit failed with' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])
        self.cu.lock()
        self.cu.rollback()
        self.cu.unlock()

    def test_commit_with_detail_as_arg(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/2 description "salt test"')
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.commit', kwarg={'detail': True})
        self.assertTrue('routing-engine' in result['dev']['message'])
        self.assertTrue('name' in result['dev']['message']['routing-engine'])
        self.assertTrue(isinstance(result['dev']['message']['routing-engine']['progress-indicator'], list))
        self.assertTrue(result['dev']['out'])
        self.cu.lock()
        self.cu.rollback(rb_id=1)
        self.cu.commit()
        self.cu.unlock()

    def test_rollback(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/4 description "salt test"')
        self.cu.commit()
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.rollback', [1])
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
        self.cu.lock()
        self.cu.rollback()
        self.cu.unlock()

    def test_diff(self):
        self.cu.lock()
        self.cu.load('set interfaces ge-0/0/5 description "salt test"')
        self.cu.commit()
        self.cu.rollback(rb_id=1)
        self.cu.commit()
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.diff', [1])
        self.assertTrue('ge-0/0/5' in result['dev']['message'] and 'description "salt test"' in result['dev']['message'])
        self.assertTrue(result['dev']['out'])
        self.cu.lock()
        self.cu.rollback()
        self.cu.unlock()

    def test_diff_exception(self):
        result = self.caller.cmd('dev', 'junos.diff', [0.1])
        self.assertTrue('RpcError' and 'message: error: invalid rollback value: 0.1' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_shutdown_without_args(self):
        result = self.caller.cmd('dev', 'junos.shutdown')
        self.assertEqual(result['dev']['message'], 'Provide either one of the arguments: shutdown or reboot.')
        self.assertFalse(result['dev']['out'])

    def test_lock_and_unlock(self):
        result = self.caller.cmd('dev', 'junos.lock')
        self.assertEqual(result['dev']['message'], 'Successfully locked the configuration.')
        self.assertTrue(result['dev']['out'])
        try:
            self.cu.lock()
        except Exception as e:
            self.assertEqual(type(e).__name__, 'LockError')
        result = self.caller.cmd('dev', 'junos.unlock')
        self.assertEqual(result['dev']['message'], 'Successfully unlocked the configuration.')
        self.assertTrue(result['dev']['out'])
        self.assertTrue(self.cu.lock())
        self.cu.unlock()

    def test_commit_check(self):
        self.cu.load('set system host-name test')
        result = self.caller.cmd('dev', 'junos.commit_check')
        self.assertEqual(result['dev']['message'], 'Commit check succeeded.')
        self.assertTrue(result['dev']['out'])
        self.cu.rollback()

    def test_commit_check_exception(self):
        pass

    def test_install_config_no_path(self):
        result = self.caller.cmd('dev', 'junos.install_config')
        self.assertEqual(result['dev']['message'], 'Please provide the salt path where the configuration is present')
        self.assertFalse(result['dev']['out'])

    def test_install_config_invalid_path(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': '/invalid/path'})
        self.assertEqual(result['dev']['message'], 'Template failed to render')
        self.assertFalse(result['dev']['out'])

    def test_install_config_load_set(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.set'})
        self.assertEqual(result['dev']['message'], 'Successfully loaded and committed!')
        self.assertTrue(result['dev']['out'])
        try:
            name = self.dev.cli('show configuration system host-name')
            self.assertEqual(name, '\nhost-name test_install;\n')
        finally:
            self.cu.lock()
            self.cu.load('set system host-name re0')
            self.cu.commit()
            self.cu.unlock()

    def test_install_config_no_diff(self):
        self.cu.lock()
        self.cu.load('set system host-name test_install')
        self.cu.commit()
        self.cu.unlock()
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.set'})
        self.assertEqual(result['dev']['message'], 'Configuration already applied!')
        self.assertTrue(result['dev']['out'])
        self.cu.lock()
        self.cu.load('set system host-name re0')
        self.cu.commit()
        self.cu.unlock()

    def test_install_config_load_xml(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.xml'})
        self.assertEqual(result['dev']['message'], 'Successfully loaded and committed!')
        self.assertTrue(result['dev']['out'])
        try:
            name = self.dev.cli('show configuration system host-name')
            self.assertEqual(name, '\nhost-name test_install_xml;\n')
        finally:
            self.cu.lock()
            self.cu.load('set system host-name re0')
            self.cu.commit()
            self.cu.unlock()

    def test_install_config_load_text(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.text'})
        self.assertEqual(result['dev']['message'], 'Successfully loaded and committed!')
        self.assertTrue(result['dev']['out'])
        try:
            name = self.dev.cli('show configuration system host-name')
            self.assertEqual(name, '\nhost-name test_install_text;\n')
        finally:
            self.cu.lock()
            self.cu.load('set system host-name re0')
            self.cu.commit()
            self.cu.unlock()

    def test_install_config_load_exception(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://load_exception.text'})
        self.assertTrue('Could not load configuration due to' in result['dev']['message'])
        self.assertFalse(result['dev']['out'])

    def test_install_config_commit_confirm(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.set', 'confirm': 1})
        self.assertEqual(result['dev']['message'], 'Successfully loaded and committed!')
        self.assertTrue(result['dev']['out'])
        time.sleep(70)
        name = self.dev.cli('show configuration system host-name')
        self.assertEqual(name, '\nhost-name re0;\n')

    def test_install_config_commit_comment(self):
        result = self.caller.cmd('dev', 'junos.install_config', kwarg={'path': 'salt://test_config.set', 'comment': 'Testing SaltStack install_config'})
        self.assertEqual(result['dev']['message'], 'Successfully loaded and committed!')
        self.assertTrue(result['dev']['out'])
        try:
            commit_history = self.dev.rpc.get_commit_information()
            self.assertEqual(etree.tostring(commit_history.xpath('//commit-history')[0][4]), '<log>Testing SaltStack install_config</log>\n')
        finally:
            self.cu.lock()
            self.cu.load('set system host-name re0')
            self.cu.commit()
            self.cu.unlock()
