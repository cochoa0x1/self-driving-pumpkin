#! /usr/bin/python3
import os
import pygame
import picamera
import RPi.GPIO as GPIO
from time import sleep, time
import numpy as np
from PIL import Image


#needed for headless operation
os.putenv('SDL_VIDEODRIVER','fbcon')
os.environ['SDL_VIDEODRIVER'] ='dummy'

AUTO=False
from brain import Brain


class Motors():
    '''simple motor class'''
    def __init__(self):
        self.throttle_left_pin = 12
        self.throttle_right_pin = 11
        self.left_forward_pin = 16
        self.left_backward_pin = 18
        self.right_forward_pin = 13
        self.right_backward_pin = 15

        self.left_throttle = None
        self.right_throttle = None

    def setup(self):
        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.throttle_left_pin, GPIO.OUT)
        GPIO.setup(self.throttle_right_pin, GPIO.OUT)
        GPIO.setup(self.left_forward_pin, GPIO.OUT)
        GPIO.setup(self.left_backward_pin, GPIO.OUT)
        GPIO.setup(self.right_forward_pin, GPIO.OUT)
        GPIO.setup(self.right_backward_pin, GPIO.OUT)
        self.left_throttle = GPIO.PWM(self.throttle_left_pin,1000)
        self.right_throttle = GPIO.PWM(self.throttle_right_pin,1000)

        self.left_throttle.start(0)
        self.right_throttle.start(0)

    def update(self, left_t, right_t):
        if left_t >= 0:
            GPIO.output(self.left_forward_pin,GPIO.HIGH)
            GPIO.output(self.left_backward_pin,GPIO.LOW)
        else:
            GPIO.output(self.left_forward_pin,GPIO.LOW)
            GPIO.output(self.left_backward_pin,GPIO.HIGH)

        if right_t >= 0:
            GPIO.output(self.right_forward_pin,GPIO.HIGH)
            GPIO.output(self.right_backward_pin,GPIO.LOW)
        else:
            GPIO.output(self.right_forward_pin,GPIO.LOW)
            GPIO.output(self.right_backward_pin,GPIO.HIGH)
            
            
        self.left_throttle.ChangeDutyCycle(abs(left_t))
        self.right_throttle.ChangeDutyCycle(abs(right_t))
            

class PS3Controller():
    def __init__(self):
        
        pygame.init()
        pygame.joystick.init()
        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()

def get_throttles(theta, throttle):
    '''converts steering angles into motor actuations'''
    lt, rt = throttle, throttle
    if  np.abs(theta) < .1:
        return lt,rt

    if theta < 0:
        lt = (1-np.abs(theta))*throttle
    elif theta >=0:
        rt = (1-theta)*throttle

    return lt,rt
    
import signal
import sys
from picamera.array import PiRGBArray

DEAD_ZONE = .005

class Camera():
    def __init__(self):
        self.camera = picamera.PiCamera()
        self.camera.resolution = (160,120)
        self.camera.framerate = 15
        self.raw = PiRGBArray(self.camera, size = (160,120))
        self.stream = self.camera.capture_continuous(self.raw, format = 'rgb', use_video_port=True)
        sleep(1)
        self.camera.start_preview(fullscreen=False, window=(100,100,640,480))
        
    def close(self):
        self.stream.close()
        self.camera.close()
        
    def capture(self):
        frame = next(self.stream)
        self.raw.truncate(0)
        return frame

        
        
record = False

from uuid import uuid4
base_name = uuid4().hex

if __name__ == '__main__':
    print('hello robot')

    wheels = Motors()
    ps3 = PS3Controller()
    wheels.setup()

    throttle =0
    theta =0.0

    wheels.update(0,0)

    t = time()

    camera = Camera()

    print('loading brain')
    brain = Brain('feature_net.h5','test_lstm.h5', N=7)
    print('loaded')

    #camera = picamera.PiCamera()
    #camera.resolution = (160,120)
    #camera.framerate = 15
    #camera.vflip=True
    #camera.hflip=True

    #camera.start_recording('my_video.h264')

    csv = open('log.csv','a')

    def signal_handler(sig,frame):
        print("caught contorl-c")
        GPIO.cleanup()
        camera.close()
        csv.close()
        sys.exit(0)

    signal.signal(signal.SIGINT,signal_handler)
    
    while True:
        events = [e for e in pygame.event.get()]
        #print(events)
        

        #look for button up on right trigger
        for e in events:
            #print(e)
            #if e.type == pygame.JOYBUTTONDOWN and e.button==7:
            #    throttle = 50

            if e.type == pygame.JOYBUTTONDOWN and e.button==5:
                record = not(record)
                base_name = uuid4().hex
                print('record set to ', record, ' ', base_name)
            
            if e.type == pygame.JOYBUTTONDOWN and e.button==3:
                AUTO = not(AUTO)
                brain.reset_memory()
                print('AUTO TOGGLED', AUTO)
                
            if e.type == pygame.JOYBUTTONUP and e.button in [7,6]:
                throttle =0
                print('stop')

            if e.type == pygame.JOYAXISMOTION and e.axis==5 and e.value > -.95:
                v = .5*(1.0+e.value)
                throttle = v*35+25
                #print(throttle)
                
            elif e.type == pygame.JOYAXISMOTION and e.axis==2 and e.value > -.95:
                v = -1*.5*(1.0+e.value)
                throttle = v*75+25
                #print(throttle)
                
            if e.type == pygame.JOYAXISMOTION and e.axis==0: #and np.abs(e.value) > DEAD_ZONE:
                theta = -1*e.value

        
        if ( time() - t > 1.0/10) and AUTO:
            frame = camera.capture().array / 255.0
            st = time()
            theta = brain.predict_theta(frame)
            #print(st-time(), theta)
            

        lt,rt = get_throttles(.5*theta,throttle)
        
        wheels.update(lt,rt)
        
        if ( time() - t > 1.0/10) and record:
            #print(time(),'frame')
            t = time()
            frame = camera.capture()
            image_file_name= 'data/' + str(t) + '.png'
            img = Image.fromarray(frame.array.astype(np.uint8))
            img.save(image_file_name)
            
            row = ','.join([str(throttle),str(theta),str(base_name),image_file_name])
            #print(row)
            csv.write(row+'\n')
        
        
    
    GPIO.cleanup()
    camera.close()
    csv.close()



