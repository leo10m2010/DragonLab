import pathlib,unittest
from launcher import demo_launch_requested


class TrialFilenameCaseTests(unittest.TestCase):
    def test_windows_path_case_does_not_change_automatic_trial_access(self):
        for filename in ('DragonLab-Prueba.exe','dragonlab-prueba.exe','DRAGONLAB-PRUEBA.EXE'):
            with self.subTest(filename=filename):
                self.assertTrue(demo_launch_requested([],str(pathlib.PureWindowsPath('C:/Mis Programas')/filename),True))
    def test_production_executables_and_source_do_not_gain_trial_by_filename(self):
        for filename in ('DragonLab-Launcher.exe','DragonLab-Cloud.exe','OtraDragonLab-Prueba.exe'):
            self.assertFalse(demo_launch_requested([],filename,True))
        self.assertFalse(demo_launch_requested([],r'C:\DragonLab-Prueba.exe',False))
        self.assertTrue(demo_launch_requested(['--demo'],'launcher.py',False))


if __name__=='__main__':unittest.main()
