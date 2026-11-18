"""Single-owner, FPS-capped camera worker. Frames never written to disk."""
import argparse
import ctypes
import sys
import threading
import time
from vision_check import WaveTracker
from face_signals import FaceSignals, geometry
from vision_worker import emit

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--continuous',action='store_true'); p.add_argument('--preview',action='store_true')
    p.add_argument('--seconds',type=float,default=8)
    for key,default in [('closed',3),('away',5),('turn',3)]: p.add_argument('--'+key,type=float,default=default)
    args=p.parse_args()
    k=ctypes.windll.kernel32; k.CreateMutexW.restype=ctypes.c_void_p
    mutex=k.CreateMutexW(None,False,'Local\\urWatchdogCameraOwner')
    if not mutex or k.GetLastError()==183:
        emit(error='Kamera dimiliki urWatchdog lain; matikan Camera Watch sebelum preview',result='ERROR'); return
    stop=threading.Event()
    def stop_requested():
        if not args.continuous: return False
        import msvcrt
        available=ctypes.c_ulong()
        handle=msvcrt.get_osfhandle(sys.stdin.fileno())
        ok=k.PeekNamedPipe(ctypes.c_void_p(handle),None,0,None,ctypes.byref(available),None)
        if not ok: return True  # parent pipe closed
        return available.value>0
    cap=None; frames=0; outcome='NONE'
    try:
        import cv2
        import mediapipe as mp
        emit(status='loading models')
        with mp.solutions.hands.Hands(max_num_hands=1,min_detection_confidence=.65,min_tracking_confidence=.65) as hands, mp.solutions.face_mesh.FaceMesh(max_num_faces=1,min_detection_confidence=.6,min_tracking_confidence=.6) as faces:
            cap=cv2.VideoCapture(0,cv2.CAP_DSHOW)
            if not cap.isOpened(): raise RuntimeError('Kamera tidak tersedia: izin atau sedang dipakai')
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,640); cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
            wave=WaveTracker(); detector=FaceSignals(args.closed,args.away,args.turn)
            started=time.monotonic(); last_report=0
            while not stop_requested() and (args.continuous or time.monotonic()-started<args.seconds):
                frame_start=time.monotonic()
                ok,frame=cap.read()
                if not ok or frame is None: raise RuntimeError('Kamera gagal membaca frame')
                frames+=1; frame=cv2.flip(frame,1); rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                hand=hands.process(rgb).multi_hand_landmarks or []
                face=faces.process(rgb).multi_face_landmarks or []
                x=None; opened=False
                if hand:
                    points=hand[0].landmark
                    def distance(a,b): return ((a.x-b.x)**2+(a.y-b.y)**2)**.5
                    opened=sum(distance(points[t],points[0])>1.15*distance(points[j],points[0]) for t,j in [(8,6),(12,10),(16,14),(20,18)])>=3
                    if opened: x=sum(points[i].x for i in (0,5,9,13,17))/5
                    if args.preview: mp.solutions.drawing_utils.draw_landmarks(frame,hand[0],mp.solutions.hands.HAND_CONNECTIONS)
                ear,yaw=geometry(face[0].landmark,frame.shape[1]/frame.shape[0]) if face else (None,None)
                now=time.monotonic()
                signal=detector.update(now,bool(face),ear,yaw)
                if wave.update(x,now): signal='WAVE'; wave.reset()
                if signal or now-last_report>=.4:
                    emit(status='watching',frames=frames,face=bool(face),hand=bool(hand),open_hand=opened,reversals=wave.turns,ear=ear,yaw=yaw,signal=signal)
                    last_report=now
                if signal: outcome=signal
                if args.preview:
                    cv2.putText(frame,f'Face {bool(face)} | hand {bool(hand)} | {signal or "monitoring"} | ESC exit',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),1)
                    cv2.imshow('urWatchdog SAFE preview - no recording',frame)
                    if cv2.waitKey(1)&255==27: break
                stop.wait(max(0,.1-(time.monotonic()-frame_start)))
    except Exception as exc:
        emit(error=str(exc)); outcome='ERROR'
    finally:
        if cap is not None: cap.release()
        if args.preview:
            try: cv2.destroyAllWindows()
            except Exception: pass
        k.CloseHandle(ctypes.c_void_p(mutex))
        emit(result=outcome,frames=frames,camera_released=True)
