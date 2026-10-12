"""Measured GunBound World profiles; do not extend to unobserved modes."""
import copy

ARMOR_SHOT1 = {'power_scale': 9.20007504911005, 'speed_offset': -0.06210580622212092, 'gravity': 391.0652458024489, 'wind_scale': 3.8148013807134467, 'sample_count': 8, 'speed_rmse': 0.0230667556706506, 'gravity_spread': 6.901569313274308, 'acceleration_rmse': 2.4947269386872812, 'acceleration_max_error': 4.223554218462436, 'power_range': [25, 100], 'wind_range': [0, 18], 'wind_observed': True, 'holdout_speed_error': 0.058005445882770346, 'holdout_acceleration_error': 4.604426931765277, 'native_euler_step': 0.05}

ARMOR_SHOT2 = {'power_scale': 9.199757044239016, 'speed_offset': -0.0280965885506248, 'gravity': 390.6981850186331, 'wind_scale': 3.808284011634467, 'sample_count': 4, 'speed_rmse': 0.015389914841973792, 'gravity_spread': 3.4296078816852855, 'acceleration_rmse': 1.728904884818855, 'acceleration_max_error': 3.361717605400816, 'power_range': [25, 100], 'wind_range': [0, 22], 'wind_observed': True, 'holdout_speed_error': 0.056196023424490704, 'holdout_acceleration_error': 4.915358231981591, 'native_euler_step': 0.05, 'validation_count': 3}

def measured_profile(mobile,shot,wind):
    fit={0:ARMOR_SHOT1,1:ARMOR_SHOT2}.get(shot) if mobile=='ARMOR' else None
    if not fit or not fit['wind_range'][0]<=wind<=fit['wind_range'][1]:return None
    return copy.deepcopy(fit)
