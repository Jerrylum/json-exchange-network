# const
CONFIG_FILEPATH = 'config/default.json'



JOYSTICK_THRESHOLD = 0.08

def _axis(axis, default=0):
    def rtn(data):
        v = data.get('axes', {}).get(axis, default)
        if abs(v) < JOYSTICK_THRESHOLD:
            v = 0
        return v
    return rtn


def _hat(axis, value):
    def rtn(data):
        return data['axes'][axis] == value
    return rtn


def _trigger(axis, btn):
    def rtn(data):
        a = data['axes'].get(axis, None)
        t = data['btns'][btn]
        return a > 0 if a != None else t
    return rtn


"""
joystick low level keys ---map to---> high level names
XBox 360 controller mapping:
"""

# Axis
LEFT_X = _axis('x')
LEFT_Y = _axis('y')
RIGHT_X = _axis('rx')
RIGHT_Y = _axis('ry')
LEFT_TRIGGER = _axis('z', -1)
RIGHT_TRIGGER = _axis('rz', -1)

# Button and hat
LEFT_U = _hat('hat0y', -1)
LEFT_R = _hat('hat0x', 1)
LEFT_D = _hat('hat0y', 1)
LEFT_L = _hat('hat0x', -1)
RIGHT_U = 'y'
RIGHT_R = 'b'
RIGHT_D = 'a'
RIGHT_L = 'x'
LB = 'tl'
LT = _trigger('z', 'tl2')
RB = 'tr'
RT = _trigger('rz', 'tr2')
SELECT_BTN = 'select'
START_BTN = 'start'
MODE_BTN = 'mode'
LEFT_THUMB = 'thumbl'
RIGHT_THUMB = 'thumbr'
