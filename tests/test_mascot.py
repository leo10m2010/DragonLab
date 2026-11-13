"""Bundled artwork, alpha, containment and event-driven mascot regression checks."""
import hashlib
import os
import pathlib
import runpy
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from mascot import ASSET_PATH,DragonMascot,mascot_image,mascot_source

class MascotAssetTests(unittest.TestCase):
    def test_artwork_is_the_original_webp_with_transparency(self):
        self.assertEqual(hashlib.sha256(ASSET_PATH.read_bytes()).hexdigest(),'426851c714940158915f20ef9ee5e7b0a3278c8cc424b812d6f9ff8941cc0db6')
        source=mascot_source()
        self.assertEqual(source.mode,'RGBA');self.assertEqual(source.size,(1536,1024))
        self.assertEqual(source.getpixel((0,0))[3],0)
        self.assertIs(source,mascot_source())

    def test_containment_preserves_proportions_and_reuses_resized_artwork(self):
        image=mascot_image(92,84)
        self.assertEqual(image.size,(92,61));self.assertEqual(image.mode,'RGBA')
        self.assertEqual(image.getpixel((0,0))[3],0)
        self.assertIs(image,mascot_image(92,84))
        self.assertEqual(mascot_image(46,42).size,(46,31))

    def test_both_windows_packages_bundle_the_original_asset(self):
        project=ASSET_PATH.parent.parent
        for spec in ('DragonLab-Cloud.spec','DragonLab-Launcher.spec'):
            with self.subTest(spec=spec):
                analysis=Mock(return_value=SimpleNamespace(pure=(),scripts=(),binaries=(),datas=()))
                runpy.run_path(str(project/'native'/spec),init_globals={'SPECPATH':str(project/'native'),'Analysis':analysis,'PYZ':Mock(),'EXE':Mock()})
                self.assertIn((str(ASSET_PATH),'assets'),analysis.call_args.kwargs['datas'])

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'requires desktop')
class MascotCanvasTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.mascot=DragonMascot(self.root)

    def tearDown(self):self.root.destroy()

    def test_all_states_reuse_artwork_and_only_change_a_separate_indicator(self):
        photo=self.mascot._photo;before=self.root.tk.call('after','info');colors=set()
        for state in DragonMascot.STATES:
            self.mascot.set_state(state);self.mascot.draw()
            self.assertIs(self.mascot._photo,photo)
            self.assertEqual(len(self.mascot.find_withtag('mascot-artwork')),1)
            self.assertEqual(self.mascot.type(self.mascot._image_id),'image')
            self.assertEqual(len(self.mascot.find_all()),2)
            colors.add(self.mascot.itemcget(self.mascot._indicator_id,'fill'))
        self.assertEqual(len(colors),4)
        self.assertEqual(before,self.root.tk.call('after','info'))
        self.assertTrue(self.root.tk.call(str(photo),'transparency','get',0,0))

    def test_resize_retains_a_bounded_photo_cache_and_reuses_prior_size(self):
        original=self.mascot._photo
        self.mascot.configure(width=184,height=168);self.mascot.draw()
        self.assertEqual((self.mascot._photo.width(),self.mascot._photo.height()),(184,123))
        self.mascot.configure(width=92,height=84);self.mascot.draw()
        self.assertIs(self.mascot._photo,original)
        for width in range(100,110):
            self.mascot.configure(width=width);self.mascot.draw()
        self.assertLessEqual(len(self.mascot._photos),4)

if __name__=='__main__':unittest.main()
