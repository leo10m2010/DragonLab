"""World/view mapping from the live renderer's affine matrix."""
def project(x,y,camera,viewport):
    camera=camera or {};vw,vh=viewport;m=camera.get('matrix');rw=camera.get('renderWidth');rh=camera.get('renderHeight')
    if m and rw and rh and all(m.get(k) is not None for k in ('a','b','c','d','tx','ty')):
        return (m['a']*x+m['c']*y+m['tx'])*vw/rw,(m['b']*x+m['d']*y+m['ty'])*vh/rh
    if all(camera.get(k) is not None for k in ('x','y','scale')):
        z=camera['scale']
        if camera.get('convention')=='top-left':return (x-camera['x'])*z,(y-camera['y'])*z
        return (x-camera['x'])*z+vw/2,(y-camera['y'])*z+vh/2
    return x,y

def unproject(x,y,camera,viewport):
    camera=camera or {};vw,vh=viewport;m=camera.get('matrix');rw=camera.get('renderWidth');rh=camera.get('renderHeight')
    if m and rw and rh and all(m.get(k) is not None for k in ('a','b','c','d','tx','ty')):
        det=m['a']*m['d']-m['b']*m['c']
        if abs(det)>1e-9:
            px=x*rw/vw-m['tx'];py=y*rh/vh-m['ty']
            return (m['d']*px-m['c']*py)/det,(-m['b']*px+m['a']*py)/det
    if all(camera.get(k) is not None for k in ('x','y','scale')) and camera['scale']:
        z=camera['scale']
        if camera.get('convention')=='top-left':return x/z+camera['x'],y/z+camera['y']
        return (x-vw/2)/z+camera['x'],(y-vh/2)/z+camera['y']
    return x,y
