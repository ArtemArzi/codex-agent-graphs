import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('overlay_storage',ROOT/'scripts/storage_install.py')
STORAGE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(STORAGE)
OVERLAYS={e['id']:e for e in json.loads((ROOT/'policies/storage-overlays/manifest.json').read_text())['overlays']}


class VideoDBOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.listener=self.root/'listener.py'
        self.listener.write_bytes(STORAGE.rendered_overlay((ROOT/'tests/fixtures/storage/videodb-ws_listener.py.txt').read_bytes(),OVERLAYS['videodb-listener']))
        self.dotenv=types.ModuleType('dotenv');self.dotenv.load_dotenv=lambda:None
        self.sdk=types.ModuleType('videodb');errors=types.ModuleType('videodb.exceptions')
        errors.AuthenticationError=type('AuthenticationError',(Exception,),{})
        self.modules={'dotenv':self.dotenv,'videodb':self.sdk,'videodb.exceptions':errors};self.output=self.root/'events'
    def tearDown(self):self.temp.cleanup()
    def load(self,cap='33554432',args=None):
        with mock.patch.dict(sys.modules,self.modules),mock.patch.object(sys,'argv',['listener',*(args if args is not None else [str(self.output)])]),mock.patch.dict(os.environ,{'VIDEODB_MAX_EVENT_BYTES':cap}):
            spec=importlib.util.spec_from_file_location('tested_video_listener',self.listener)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    def test_utf8_budget_preserves_prior_events(self):
        module=self.load();module.write_pid();module.append_event({'text':'Привет'})
        before=module.EVENTS_FILE.read_bytes();module.MAX_EVENT_BYTES=len(before)
        with self.assertRaisesRegex(module.EventBudgetExceeded,'PARTIAL'):module.append_event({'text':'ещё'})
        self.assertEqual(before,module.EVENTS_FILE.read_bytes());module.cleanup_pid();self.assertFalse(module.PID_FILE.exists())
    def test_oversized_first_event_and_invalid_caps(self):
        for cap in ('0','-1','invalid'):
            with self.subTest(cap=cap),self.assertRaises(SystemExit):self.load(cap)
        module=self.load('1');module.write_pid()
        with self.assertRaises(module.EventBudgetExceeded):module.append_event({'text':'x'})
        self.assertEqual(b'',module.EVENTS_FILE.read_bytes());module.cleanup_pid()
    def test_exclusive_owner_changed_pid_and_symlink_journal(self):
        first=self.load();second=self.load();first.write_pid()
        with self.assertRaises(FileExistsError):second.write_pid()
        first.PID_FILE.rename(self.root/'old-pid');first.PID_FILE.write_text('foreign owner')
        first.cleanup_pid();self.assertEqual('foreign owner',first.PID_FILE.read_text())
        with self.assertRaises(RuntimeError):first.append_event({'text':'x'})
        first.PID_FILE.unlink();first.write_pid();foreign=self.root/'foreign';foreign.write_text('keep')
        first.EVENTS_FILE.symlink_to(foreign)
        with self.assertRaises(OSError):first.append_event({'text':'x'})
        self.assertEqual('keep',foreign.read_text());first.cleanup_pid()
    def test_clear_refuses_prior_events_and_output_is_explicit(self):
        module=self.load();module.EVENTS_FILE.write_text('retained event\n')
        with self.assertRaises(SystemExit):self.load(args=['--clear',str(self.output)])
        self.assertEqual('retained event\n',module.EVENTS_FILE.read_text())
        with mock.patch.dict(os.environ,{},clear=True),self.assertRaises(SystemExit):self.load(args=[])
    def test_budget_failure_exits_retry_loop_without_reconnecting(self):
        module=self.load('1');module.write_pid();calls=[]
        class Socket:
            connection_id='synthetic'
            async def receive(self):yield {'data':{'text':'too large'}}
        class Wrapper:
            async def connect(self):return Socket()
        class Connection:
            def connect_websocket(self):return Wrapper()
        def connect():calls.append('connect');return Connection()
        self.sdk.connect=connect
        with self.assertRaises(module.EventBudgetExceeded):asyncio.run(module.listen_with_retry())
        self.assertEqual(['connect'],calls);self.assertEqual(b'',module.EVENTS_FILE.read_bytes());module.cleanup_pid()


class UIDemoOverlayTests(unittest.TestCase):
    def run_case(self,mode):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'raw.webm';raw.write_bytes(b'video payload');dest=root/'final.webm'
            if mode=='existing':dest.write_bytes(b'prior result')
            snippet=OVERLAYS['ui-demo']['edits'][0][1]
            code="""const fs=require('fs'),path=require('path');
const dir=process.argv[2],mode=process.argv[3]; let closed=false,deleted=false;
const src=path.join(dir,'raw.webm');const VIDEO_DIR=dir,OUTPUT_NAME='final.webm';
const browser={close:async()=>{closed=true;}};
const context={close:async()=>{if(mode==='close-fail')throw Error('close');}};
const page={video:()=>({path:async()=>src,delete:async()=>{deleted=true;fs.unlinkSync(src);}})};
if(mode==='copy-fail')fs.copyFileSync=()=>{throw Error('copy');};
if(mode==='read-fail')fs.readSync=()=>{throw Error('read');};
(async()=>{try{REPLACEMENT}catch(e){}finally{
console.log(JSON.stringify({closed,deleted,raw:fs.existsSync(src)}));}})();
""".replace('REPLACEMENT',snippet)
            script=root/'test.cjs';script.write_text(code)
            result=subprocess.run(['node',str(script),str(root),mode],capture_output=True,text=True)
            return json.loads(result.stdout.splitlines()[-1]),dest.read_bytes() if dest.exists() else None
    def test_success_closes_browser_and_raw_only_after_verified_save(self):
        state,final=self.run_case('ok');self.assertEqual({'closed':True,'deleted':True,'raw':False},state);self.assertEqual(b'video payload',final)
    def test_existing_result_copy_read_and_context_failure_keep_raw(self):
        for mode in ('existing','copy-fail','read-fail','close-fail'):
            with self.subTest(mode=mode):
                state,final=self.run_case(mode);self.assertEqual({'closed':True,'deleted':False,'raw':True},state)
                if mode=='existing':self.assertEqual(b'prior result',final)
