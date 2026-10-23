import math
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from app import App
from calibration_validation import validated_fit
from core import Settings,acceleration,point
from learning_guard import errors,update
from physics_extensions import fit_calibration
from wind_models import acceleration as wind_acceleration


def sample(power,wind,angle,mode='floor',index=0):
    model={'gravity':392,'wind_scale':4,'wind_mode':mode}
    ax,ay=wind_acceleration(model,wind,angle)
    speed=2*power+7;heading=math.radians(43)
    return {'power':power,'vx':speed*math.cos(heading),'vy':-speed*math.sin(heading),
            'ax':ax,'ay':ay,'wind':wind,'wind_angle':angle,'sample_id':str(index),
            'simple_trajectory':True,'duration_s':3}


def samples(mode='floor'):
    return [sample(power,wind,angle,mode,index) for index,(power,wind,angle) in enumerate(
        ((100,5,31),(180,17,147),(260,29,237),(340,11,311)))]


class Var:
    def __init__(self,value):self.value=str(value)
    def get(self):return self.value
    def set(self,value):self.value=str(value)


def app_fixture(fit,clone='dragonbound'):
    book=SimpleNamespace(fit=fit,records={})
    book.profile=lambda *args:book.fit
    book.provisional=lambda *args:None
    book.acceleration=lambda *args:None
    book.key=lambda *args:':'.join(map(str,args))
    return SimpleNamespace(s=Settings(),clone_id=clone,book=book,profiles={},profile_stamp=None,
        vars={key:Var(value) for key,value in [('gravity',73.5),('wind_scale',.74),('power_scale',1)]},
        profile_key=lambda:'fixture')


class GuideWindModelTests(unittest.TestCase):
    def test_floor_fit_preserves_speed_fit_and_residual_fields(self):
        fit=fit_calibration(samples())
        self.assertEqual(fit['wind_mode'],'floor')
        self.assertAlmostEqual(fit['gravity'],392)
        self.assertAlmostEqual(fit['wind_scale'],4)
        self.assertAlmostEqual(fit['power_scale'],2)
        self.assertAlmostEqual(fit['speed_offset'],7)
        self.assertEqual(fit['sample_count'],4)
        self.assertEqual(fit['power_range'],[100,340])
        self.assertEqual(fit['wind_range'],[5,29])
        self.assertTrue(fit['wind_observed'])
        for key in ('speed_rmse','gravity_spread','acceleration_rmse','acceleration_max_error'):
            self.assertLess(fit[key],1e-9)

    def test_four_floor_samples_pass_independent_parameter_holdouts(self):
        fit=validated_fit(samples())
        self.assertEqual(fit['wind_mode'],'floor')
        self.assertLess(fit['holdout_acceleration_error'],1e-9)
        self.assertLess(fit['holdout_speed_error'],1e-9)

    def test_smooth_measurements_keep_smooth_model(self):
        fit=validated_fit(samples('smooth'))
        self.assertEqual(fit['wind_mode'],'smooth')
        self.assertLess(fit['holdout_acceleration_error'],1e-9)

    def test_bad_acceleration_still_fails_validation(self):
        observations=samples();observations[-1]['ax']+=40
        with self.assertRaises(ValueError):validated_fit(observations)

    def test_guide_trajectory_uses_selected_wind_model(self):
        settings=Settings(gravity=392,wind_scale=4,wind_mode='floor',wind=17,wind_angle=147,
                          hero_x=0,hero_y=0,angle=0,muzzle=False,power_scale=2,speed_offset=7)
        ax,ay=wind_acceleration({'gravity':392,'wind_scale':4,'wind_mode':'floor'},17,147)
        self.assertEqual(acceleration(settings),(ax,ay))
        self.assertEqual(point(settings,100,2),(414+2*ax,2*ay))

    def test_observed_acceleration_overrides_selected_model(self):
        settings=Settings(wind_mode='floor',environment={'observedAcceleration':[12,345]})
        self.assertEqual(acceleration(settings),(12,345))

    def test_old_settings_and_fits_keep_smooth_predictions(self):
        settings=Settings(wind=17,wind_angle=147)
        self.assertEqual(settings.wind_mode,'smooth')
        self.assertEqual(acceleration(settings),wind_acceleration({'gravity':73.5,'wind_scale':.74},17,147))
        fit={'power_scale':2,'speed_offset':7,'gravity':392,'wind_scale':4,'wind_observed':True}
        result=errors(fit,sample(200,17,147,'smooth'))
        self.assertLess(result['acceleration'],1e-9)
        self.assertLess(result['trajectory'],1e-9)

    def test_shadow_validation_uses_floor_for_acceleration_and_trajectory(self):
        fit=fit_calibration(samples());result=errors(fit,sample(220,17,147))
        self.assertLess(result['acceleration'],1e-9)
        self.assertLess(result['trajectory'],1e-9)

    def test_model_type_change_is_a_distinct_candidate(self):
        challenger=fit_calibration(samples());active={**challenger,'wind_mode':'smooth'}
        observations=samples();record={'fit':active,'samples':observations}
        with patch('learning_guard.current_fit',return_value=(challenger,0)):
            update(record,observations[-1])
        self.assertEqual(record['candidate']['fit']['wind_mode'],'floor')
        self.assertEqual(record['fit']['wind_mode'],'smooth')

    def test_application_tracks_mode_changes_and_resets_missing_fit(self):
        fit=fit_calibration(samples());app=app_fixture(fit)
        App.apply_measured_profile(app);stamp=app.profile_stamp
        self.assertEqual(app.s.wind_mode,'floor')
        app.book.fit={**fit,'wind_mode':'smooth'}
        App.apply_measured_profile(app)
        self.assertEqual(app.s.wind_mode,'smooth')
        self.assertNotEqual(app.profile_stamp,stamp)
        app.book.fit=fit;App.apply_measured_profile(app)
        app.book.fit=None;App.apply_measured_profile(app)
        self.assertEqual(app.s.wind_mode,'smooth')
        self.assertEqual(app.s.gravity,73.5)
        app.s.wind_mode='floor';App.apply_measured_profile(app)
        self.assertEqual(app.s.wind_mode,'smooth')

    def test_application_keeps_legacy_gunbound_model_smooth(self):
        fit={key:value for key,value in fit_calibration(samples('smooth')).items() if key!='wind_mode'}
        fit['native_euler_step']=.05
        app=app_fixture(fit,'gunbound-world');app.s.wind_mode='floor'
        App.apply_measured_profile(app)
        self.assertEqual(app.s.wind_mode,'smooth')
        self.assertEqual(app.s.environment['nativeEulerStep'],.05)


if __name__=='__main__':unittest.main()
