"""Landmark geometry and sustained-duration signals, not sleep diagnosis."""
import math
class FaceSignals:
    def __init__(self, closed=3, away=5, turn=3):
        self.durations={'EYES_CLOSED':closed,'FACE_AWAY':away,'HEAD_TURNED':turn}
        self.since={}; self.latched=set()
    def update(self, now, face, ear=None, yaw=None):
        active={'FACE_AWAY':not face,'EYES_CLOSED':face and ear is not None and ear<.20,
                'HEAD_TURNED':face and yaw is not None and abs(yaw)>.38}
        signal=None
        for name,on in active.items():
            if not on:
                self.since.pop(name,None); self.latched.discard(name)
            else:
                self.since.setdefault(name,now)
                if now-self.since[name]>=self.durations[name] and name not in self.latched:
                    self.latched.add(name); signal=name
        return signal

def geometry(points, aspect=4/3):
    def dist(a,b): return math.hypot((points[a].x-points[b].x)*aspect,points[a].y-points[b].y)
    def ear(ids):
        a,b,c,d,e,f=ids
        return (dist(b,f)+dist(c,e))/max(2*dist(a,d),1e-6)
    value=(ear((33,160,158,133,153,144))+ear((362,385,387,263,373,380)))/2
    left,right=points[234].x,points[454].x
    yaw=(points[1].x-(left+right)/2)/max(abs(right-left)/2,1e-6)
    return value,yaw
