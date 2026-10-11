"""Measured GunBound World profiles; do not extend to unobserved modes."""
import copy

ARMOR_SHOT1 = {'power_scale': 9.20007504911005, 'speed_offset': -0.06210580622212092, 'gravity': 391.0652458024489, 'wind_scale': 3.8148013807134467, 'sample_count': 8, 'speed_rmse': 0.0230667556706506, 'gravity_spread': 6.901569313274308, 'acceleration_rmse': 2.4947269386872812, 'acceleration_max_error': 4.223554218462436, 'power_range': [25, 100], 'wind_range': [0, 18], 'wind_observed': True, 'holdout_speed_error': 0.058005445882770346, 'holdout_acceleration_error': 4.604426931765277, 'native_euler_step': 0.05}

def measured_profile(mobile,shot,wind):
    if mobile!='ARMOR' or shot!=0 or not 0<=wind<=18:return None
    return copy.deepcopy(ARMOR_SHOT1)
