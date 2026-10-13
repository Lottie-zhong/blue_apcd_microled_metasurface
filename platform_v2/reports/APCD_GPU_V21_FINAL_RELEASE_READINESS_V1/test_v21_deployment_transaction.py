import unittest,tempfile,json,sqlite3,hashlib,sys
from pathlib import Path
from unittest.mock import patch
import v21_deployment_transaction as T

XML='''<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Triggers><CalendarTrigger/></Triggers><Principals><Principal><UserId>fixture-owner</UserId><LogonType>S4U</LogonType></Principal></Principals><Settings><Enabled>true</Enabled><AllowStartOnDemand>true</AllowStartOnDemand><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy></Settings><Actions><Exec><Command>N:\\anaconda_envs\\RCP_LCP\\python.exe</Command><Arguments>old --plan</Arguments><WorkingDirectory>old</WorkingDirectory></Exec></Actions></Task>'''
class TestTransaction(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='zero_solver_deploy_');self.root=Path(self.temp.name);self.rt=self.root/'runtime';self.rt.mkdir();self.package=self.root/'package';self.package.mkdir();self.calls=[]
  p=self.package/'platform_v2/tools/serial_controller.py';p.parent.mkdir(parents=True);p.write_text('# fixture, never executes science')
  cfg={'profiles':[]};(self.package/'DISABLED_PLATFORM.json').write_text(json.dumps(cfg))
  self.science=self.root/'science.json';self.science.write_text('{"entered_count":0,"hold":true}')
  db=sqlite3.connect(self.rt/'ledger.sqlite3');db.executescript('create table slot(generation,token,owner,request_sha);insert into slot values(1,null,null,null);create table tasks(state,entered);insert into tasks values("TRUTH_VALID",1);');db.close()
  self.manifest={'gpu_head':T.GPU_HEAD,'coupling_head':T.COUPLING_HEAD,'files':{'platform_v2/tools/serial_controller.py':{'sha256':T.sha(p)},'DISABLED_PLATFORM.json':{'sha256':T.sha(self.package/'DISABLED_PLATFORM.json')}},'scheduler_xml_sha256':hashlib.sha256(XML.encode()).hexdigest(),'production_authority':{str(self.science):T.sha(self.science)},'science_ledgers':[str(self.science)]}
  (self.package/'PACKAGE_MANIFEST.json').write_text(json.dumps(self.manifest));self.pin=T.sha(self.package/'PACKAGE_MANIFEST.json')
  self.rt_patch=patch.object(T,'RT',self.rt);self.rt_patch.start()
 def tearDown(self):self.rt_patch.stop();self.temp.cleanup()
 def shell(self,cmd):
  self.calls.append(cmd)
  if cmd.startswith('Export-'):return XML
  if 'Get-CimInstance' in cmd:return ''
  if 'Get-Acl' in cmd:return 'fixture-sddl'
  if 'Select-Object State' in cmd:return '{"Enabled":false,"Demand":false,"State":"Disabled"}'
  return ''
 def test_install_without_authorization_never_mutates(self):
  with patch.object(T,'shell',side_effect=AssertionError('must not execute')):
   with self.assertRaisesRegex(AssertionError,'NOT_AUTHORIZED'):T.apply(self.package,'DENY','DENY',self.pin)
 def test_acl_requires_separate_authorization(self):
  with patch.object(T,'shell',side_effect=AssertionError('must not execute')):
   with self.assertRaisesRegex(AssertionError,'ACL_NOT_AUTHORIZED'):T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','DENY',self.pin)
 def test_package_tamper_refused(self):
  (self.package/'platform_v2/tools/serial_controller.py').write_text('changed')
  with self.assertRaisesRegex(AssertionError,'PACKAGE_SHA_CHANGED'):T.verify_package(self.package)
 def test_package_path_escape_refused(self):
  self.manifest['files']['../science.json']={'sha256':T.sha(self.science)};(self.package/'PACKAGE_MANIFEST.json').write_text(json.dumps(self.manifest))
  with self.assertRaises(AssertionError):T.verify_package(self.package)
 def test_unlisted_executable_file_refused(self):
  (self.package/'unlisted.py').write_text('raise RuntimeError("untrusted")')
  with self.assertRaisesRegex(AssertionError,'UNDECLARED_PACKAGE_FILE'):T.verify_package(self.package)
 def test_xml_rebind_preserves_s4u_disables_timer_and_demand(self):
  root=T.ET.fromstring(T.task_xml(XML,'a'*64,self.root/'release'));n=lambda k:'{'+T.NS+'}'+k
  self.assertEqual(root.find(n('Settings')+'/'+n('Enabled')).text,'false');self.assertEqual(root.find(n('Settings')+'/'+n('AllowStartOnDemand')).text,'false');self.assertEqual(len(root.find(n('Triggers'))),0)
  self.assertEqual(root.find(n('Principals')+'/'+n('Principal')+'/'+n('LogonType')).text,'S4U');self.assertIn('--platform-sha256 '+('a'*64),root.find(n('Actions')+'/'+n('Exec')+'/'+n('Arguments')).text)
 def test_rollback_xml_never_enables_legacy(self):
  root=T.ET.fromstring(T.disabled_rollback_xml(XML));n=lambda k:'{'+T.NS+'}'+k
  self.assertEqual(root.find(n('Settings')+'/'+n('Enabled')).text,'false');self.assertEqual(root.find(n('Actions')+'/'+n('Exec')+'/'+n('Arguments')).text,'old --plan')
 def test_active_slot_refuses_without_process_termination(self):
  db=sqlite3.connect(self.rt/'ledger.sqlite3');db.execute('update slot set token="occupied"');db.commit();db.close()
  with self.assertRaisesRegex(AssertionError,'ACTIVE_SLOT'):T.idle()
 def test_unpinned_package_never_mutates(self):
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=AssertionError('must not execute')):
   with self.assertRaisesRegex(AssertionError,'UNPINNED_PACKAGE'):T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY','0'*64)
 def test_apply_fixture_preserves_budget_and_database(self):
  before=T.state();budget=T.sha(self.science)
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=self.shell),patch.object(T.subprocess,'run',return_value=T.subprocess.CompletedProcess([],0,'DISABLED_PLATFORM_LOAD_PASS','')):
   T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY',self.pin)
  self.assertEqual(T.state(),before);self.assertEqual(T.sha(self.science),budget);self.assertEqual(json.loads((self.rt/'CURRENT_INSTALLATION.json').read_text())['science_release'],'DENY_NO_PROFILES_NO_ADMISSION');self.assertFalse(any('Start-ScheduledTask' in x or 'Stop-Process' in x for x in self.calls))
 def test_smoke_failure_keeps_disabled_no_automatic_rollback(self):
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=self.shell),patch.object(T.subprocess,'run',return_value=T.subprocess.CompletedProcess([],1,'','fixture dependency failure')):
   with self.assertRaises(AssertionError):T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY',self.pin)
  self.assertTrue(self.calls[-1].startswith('Disable-ScheduledTask'));self.assertTrue(list((self.rt/'installation_backups').glob('*/FAIL_CLOSED.json')));self.assertFalse(any('Enable-ScheduledTask' in x for x in self.calls))
 def test_state_drift_rollback_refuses_before_change(self):
  b=self.root/'backup';b.mkdir();(b/'BEFORE.json').write_text(json.dumps({'execution':{'slot':[]},'science_authority':{}}))
  with patch.object(T,'shell',side_effect=self.shell):
   with self.assertRaisesRegex(AssertionError,'NO_REWIND'):T.rollback(b,'APPROVE_V21_DISABLED_ROLLBACK_ONLY')
  self.assertFalse(any('Disable-ScheduledTask' in x or 'Register-ScheduledTask' in x for x in self.calls))
 def test_rollback_denies_without_new_authorization(self):
  with self.assertRaisesRegex(AssertionError,'NOT_AUTHORIZED'):T.rollback(self.root,'DENY')
 def old_inventory(self):
  oldroot=self.root/'old_code';oldroot.mkdir();src=oldroot/'core.py';src.write_text('# immutable old core')
  inv=self.root/'old_inventory.json';inv.write_text(json.dumps({'code_root':str(oldroot),'files':{'core.py':{'sha256':T.sha(src)}}}))
  self.manifest['installed_code_inventory']={'path':str(inv),'sha256':T.sha(inv)};(self.package/'PACKAGE_MANIFEST.json').write_text(json.dumps(self.manifest));self.pin=T.sha(self.package/'PACKAGE_MANIFEST.json');return src
 def test_old_source_backup_preserves_exact_bytes(self):
  src=self.old_inventory()
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=self.shell),patch.object(T.subprocess,'run',return_value=T.subprocess.CompletedProcess([],0,'PASS','')):
   T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY',self.pin)
  copies=list((self.rt/'installation_backups').glob('*/old_code_source/core.py'));self.assertEqual(len(copies),1);self.assertEqual(copies[0].read_bytes(),src.read_bytes())
 def test_old_source_tamper_denies_before_disabling_task(self):
  src=self.old_inventory();src.write_text('tampered')
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=self.shell):
   with self.assertRaisesRegex(AssertionError,'OLD_SOURCE_SHA_DRIFT'):T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY',self.pin)
  self.assertFalse(any('Disable-ScheduledTask' in x for x in self.calls))
 def test_full_no_entry_rollback_preserves_truth_and_budget(self):
  self.old_inventory();before=T.state();budget=T.sha(self.science)
  with patch.object(sys,'executable',T.PYTHON),patch.object(T,'shell',side_effect=self.shell),patch.object(T.subprocess,'run',return_value=T.subprocess.CompletedProcess([],0,'PASS','')):
   T.apply(self.package,'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY',self.pin)
   backup=next((self.rt/'installation_backups').iterdir());T.rollback(backup,'APPROVE_V21_DISABLED_ROLLBACK_ONLY')
  self.assertEqual(T.state(),before);self.assertEqual(T.sha(self.science),budget);receipt=json.loads((backup/'ROLLBACK_RECEIPT.json').read_text());self.assertFalse(receipt['database_rewound']);self.assertFalse(receipt['acl_weakened']);self.assertFalse(any('Enable-ScheduledTask' in x for x in self.calls))
if __name__=='__main__':unittest.main(verbosity=2)
