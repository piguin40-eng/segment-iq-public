"""Measured reference plane plus regional height (anterior is -Y)."""
import numpy as np

def regional_weight(y,bounds):
    low,high=bounds
    u=np.clip((high-np.asarray(y,dtype=float))/max(high-low,1e-8),0,1)
    return u*u*(3-2*u)

def top_height(xy,config):
    xy=np.asarray(xy,dtype=float)
    # bar_top_z is the intercept, also mirrored in bar_plane[2] for reports.
    # Keeping one authoritative intercept preserves explicit height corrections.
    slope=np.asarray(config.get('bar_plane',[0.,0.]),dtype=float)[:2]
    return xy@slope+config['bar_top_z']+config.get('anterior_raise_mm',0)*regional_weight(xy[...,1],config.get('bar_y_bounds',[0,1]))
