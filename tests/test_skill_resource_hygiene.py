import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
INSTALL=load('hygiene_install','scripts/install.py')
RESEARCH=load('hygiene_research','skills/research/scripts/research_graph.py')
PROJECT=load('hygiene_project','skills/project-start/scripts/project_maintenance.py')
INVENTORY=load('hygiene_inventory','skills/skill-stocktake/scripts/inventory.py')


class AtomicResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.target=self.root/'state.json';self.target.write_text('existing')
        self.sentinel=self.root/'.unrelated';self.sentinel.write_text('foreign')
    def tearDown(self):self.temp.cleanup()
    def assert_preserved(self):
        self.assertEqual('existing',self.target.read_text());self.assertEqual('foreign',self.sentinel.read_text())
        self.assertEqual({'state.json','.unrelated'},{p.name for p in self.root.iterdir()})
    def test_serialization_failure_closes_only_own_temporary(self):
        for module in (RESEARCH,PROJECT):
            with self.subTest(module=module.__name__),self.assertRaises(TypeError):module.write_json_atomic(self.target,{'bad':object()})
            self.assert_preserved()
    def test_write_replace_and_controlled_cancel_keep_destination(self):
        for module in (INSTALL,RESEARCH,PROJECT):
            write=getattr(module,'atomic_write',None) or module.write_text_atomic
            with self.assertRaises(TypeError):write(self.target,object())
            self.assert_preserved()
            for failure in (OSError('replace failed'),KeyboardInterrupt()):
                with mock.patch.object(module.os,'replace',side_effect=failure),self.assertRaises(type(failure)):write(self.target,'new')
                self.assert_preserved()
    def test_substituted_temporary_is_retained(self):
        for module in (INSTALL,RESEARCH,PROJECT):
            write=getattr(module,'atomic_write',None) or module.write_text_atomic
            held=self.root/('held-'+module.__name__);captured=[]
            def replace(source,target):
                source=Path(source);source.rename(held);source.write_text('foreign replacement');captured.append(source)
                raise OSError('changed temp')
            with mock.patch.object(module.os,'replace',side_effect=replace),self.assertRaises(OSError):write(self.target,'new')
            self.assertEqual('foreign replacement',captured[0].read_text());self.assertEqual('existing',self.target.read_text())
    def test_success_has_no_temporary_and_original_format(self):
        for module in (RESEARCH,PROJECT):
            module.write_json_atomic(self.target,{'b':1,'a':'текст'})
            self.assertEqual({'b':1,'a':'текст'},json.loads(self.target.read_text()));self.assertTrue(self.target.read_text().endswith('\n'))
        INSTALL.atomic_write(self.target,'published')
        self.assertEqual({'state.json','.unrelated'},{p.name for p in self.root.iterdir()})
    def test_copy_excludes_caches_and_preserves_old_backup(self):
        source=self.root/'source';source.mkdir();(source/'ordinary').write_text('payload');(source/'.DS_Store').write_text('noise')
        for name in ('__pycache__','.pytest_cache'):
            (source/name).mkdir();(source/name/'cache').write_text('noise')
        target=self.root/'target';target.mkdir();(target/'prior-cache').write_text('keep');backup=self.root/'backup'
        self.assertEqual('installed',INSTALL.replace_directory(source,target,backup))
        self.assertEqual({'ordinary'},{p.name for p in target.iterdir()});self.assertEqual('keep',(backup/'prior-cache').read_text())
        self.assertEqual('in-sync',INSTALL.replace_directory(source,target,self.root/'unused'));self.assertFalse((self.root/'unused').exists())


class InventoryResourceTests(unittest.TestCase):
    def test_crlf_aliases_resources_and_same_body_different_helper(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);body=b'---\r\nname: example\r\ndescription: Example\r\n---\r\nBody\r\n'
            for name in ('a','b'):
                skill=root/name;skill.mkdir();(skill/'SKILL.md').write_bytes(body);(skill/'helper.py').write_text(name)
            alias=root/'alias';alias.symlink_to(root/'a',target_is_directory=True)
            secret=root/'outside-secret';secret.write_text('never dereference');(root/'a'/'linked').symlink_to(secret)
            result=INVENTORY.inventory([root/'a',alias,root/'b'],[])
            self.assertEqual(2,result['copies']);self.assertEqual(1,result['distinct_bodies']);self.assertEqual(2,result['distinct_packages'])
            self.assertEqual({'example'},{s['name'] for s in result['skills']})
            before=result['skills'][0]['resource_sha256']['linked'];secret.write_text('changed content')
            after=INVENTORY.inventory([root/'a'],[])['skills'][0]['resource_sha256']['linked'];self.assertEqual(before,after)
