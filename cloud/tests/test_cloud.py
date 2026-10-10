import sys,pathlib,unittest,tempfile,hashlib,io,math
from types import SimpleNamespace
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'cloud/jobs'))
from cloud_client import CloudError,download_verified,CloudClient
from cloud_profiles import compatible_fit
from calibrate import candidates
class CloudTests(unittest.TestCase):
 def test_update_rejects_corruption_and_preserves_installed_binary(self):
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/'app.exe';path.write_bytes(b'installed')
   with self.assertRaises(CloudError):download_verified('https://github.com/leo10m2010/DragonLab/releases/download/v1/app.exe',path,hashlib.sha256(b'expected').hexdigest(),'leo10m2010/DragonLab',lambda *a,**kw:io.BytesIO(b'corrupt'))
   self.assertEqual(path.read_bytes(),b'installed');self.assertFalse(path.with_suffix('.download').exists())
   with self.assertRaises(CloudError):download_verified('https://example.com/app.exe',path,'a'*64,'leo10m2010/DragonLab')
 def test_updates_replace_only_after_hash_verification(self):
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/'app.exe';payload=b'verified';download_verified('https://github.com/leo10m2010/DragonLab/releases/download/v1/app.exe',path,hashlib.sha256(payload).hexdigest(),'leo10m2010/DragonLab',lambda *a,**kw:io.BytesIO(payload));self.assertEqual(path.read_bytes(),payload)
 def test_consent_and_no_factory_or_player_data_upload(self):
  with tempfile.TemporaryDirectory() as folder:
   client=CloudClient.__new__(CloudClient);client.directory=pathlib.Path(folder);client.account={'share_measurements':False,'user_id':'test'};calls=[];client.rpc=lambda name,args:(calls.append(args),len(args['batch']))[1]
   sample={'power':100,'vx':200,'vy':-300,'ax':0,'ay':398,'wind':0,'wind_angle':20,'source':'native-shot-start','sample_id':'live','player_name':'private','chat':'private'}
   book=SimpleNamespace(records={'dragonbound:ICE:0':{'samples':[sample]}})
   self.assertEqual(client.send_new_measurements(book),0);self.assertFalse(calls)
   client.account['share_measurements']=True;digest=hashlib.sha256(b'dragonbound:ICE:0:live').hexdigest();self.assertEqual(client.send_new_measurements(book,{digest}),0)
   self.assertEqual(client.send_new_measurements(book),1);self.assertNotIn('player_name',calls[0]['batch'][0]);self.assertNotIn('sample_id',calls[0]['batch'][0]);self.assertEqual(client.send_new_measurements(book),0)
 def test_shared_profiles_require_observed_matching_regime(self):
  fit={'gravity':398,'power_scale':2.4,'speed_offset':0};profiles=[{'id':1,'clone':'dragonbound','mobile':'ICE','shot':0,'fit':fit}];book=SimpleNamespace(records={})
  self.assertIsNone(compatible_fit(profiles,book,'dragonbound','ICE',0,0))
  book.records['dragonbound:ICE:0']={'samples':[{'power':100,'vx':240,'vy':0,'ay':398,'wind':0}]};self.assertEqual(compatible_fit(profiles,book,'dragonbound','ICE',0,0),fit);self.assertIsNone(compatible_fit(profiles,book,'dragonbound','ICE',0,5))
  book.records['dragonbound:ICE:0']['samples'][-1]['ay']=410;self.assertIsNone(compatible_fit(profiles,book,'dragonbound','ICE',0,0))
 def test_candidates_need_multiple_contributors_and_holdout_validation(self):
  rows=[]
  for user in ('a','b','c'):
   for power in (100,140,180,220,260,300):rows.append({'clone':'dragonbound','mobile':'ICE','shot':0,'user_id':user,'sample':{'power':power,'vx':power*2.4,'vy':0,'ax':0,'ay':398,'wind':0,'wind_angle':20}})
  self.assertFalse(candidates(rows[:12]));result=candidates(rows);self.assertEqual(len(result),1);self.assertEqual(result[0]['contributors'],3);self.assertEqual(result[0]['evidence']['held_out_contributor_max_speed_error'],0)
  for row in rows:row['sample']['wind']=2
  self.assertFalse(candidates(rows))
if __name__=='__main__':unittest.main()
