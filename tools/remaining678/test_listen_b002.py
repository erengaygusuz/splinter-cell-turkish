import unittest,tempfile,json,threading,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
import listen_b002 as ui

class ListeningTests(unittest.TestCase):
 def test_new_revision_keeps_old_decisions_and_rejects_missing_audio(self):
  with tempfile.TemporaryDirectory() as d:
   batch=Path(d);(batch/'qa_review').mkdir();old=batch/'qa_review/b002_dinleme_kararlari_v01.json';old.write_text('{"old":"preserved"}')
   entries=[dict(key='available',clips=[dict(sha256='one')]),dict(key='missing',clips=[])]
   store=ui.ReviewStore(batch,entries)
   with self.assertRaises(ValueError):store.set_decision('missing','DOGRU','')
   store.set_decision('available','DOGRU','test fixture')
   self.assertEqual(old.read_text(),'{"old":"preserved"}')
   self.assertEqual(ui.ReviewStore(batch,entries).snapshot()['available']['audio_sha256'],'one')
   entries[0]['clips'][0]['sha256']='changed'
   self.assertNotIn('available',ui.ReviewStore(batch,entries).snapshot())
 def test_audio_route_serves_only_selected_file_and_range(self):
  with tempfile.TemporaryDirectory() as d:
   batch=Path(d);wav=batch/'correct.wav';wav.write_bytes(b'RIFFcorrect file content')
   entries=[dict(key='known',clips=[dict(rel='correct.wav',sha256=ui.sha256(wav))]),dict(key='missing',clips=[])]
   store=ui.ReviewStore(batch,entries);server=ThreadingHTTPServer(('127.0.0.1',0),ui.handler_factory(batch,entries,store))
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    req=urllib.request.Request(base+'/audio?key=known&part=0',headers={'Range':'bytes=0-3'})
    with urllib.request.urlopen(req) as response:self.assertEqual(response.status,206);self.assertEqual(response.read(),b'RIFF')
    for key in ['missing','unknown']:
     with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/audio?key='+key+'&part=0')
     self.assertEqual(error.exception.code,404);error.exception.close()
    wav.write_bytes(b'changed')
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/audio?key=known&part=0')
    self.assertEqual(error.exception.code,409);error.exception.close()
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
