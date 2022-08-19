############################
# RUN THIS PROGRAM WITH SUDO
############################

# Imports for lighting and capacitive touch
import RPi.GPIO as GPIO
import board
import busio
import adafruit_mpr121

# Imports for speech recognition
import json
import grpc
import rero_grpc.audio_pb2_grpc as audio_grpc
import rero_grpc.audio_pb2 as audio
import rero_grpc.speech_recognition_pb2_grpc as sr_grpc

# General imports
import time
import threading

# Set up LED power
led_pin=11
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(led_pin, GPIO.OUT)
ledPWM=GPIO.PWM(led_pin, 500)
ledPWM.start(0)

# Set up capacitive touch breakout
CTPID=14
GPIO.setup(CTPID, GPIO.OUT, initial=GPIO.HIGH)
# Set up I2C, working on figuring out how to manipulate values so we can connect to different GPIO pins. I'm fairly certain you can just provide the GPIO number
i2c=busio.I2C(board.SCL, board.SDA)
mpr121=adafruit_mpr121.MPR121(i2c)

# Set up thread control, you can do this with lamda functions, but this is quick and easy
stopThreads=False

# Turns the light on. This has a while true in it for compatibility with the more complex functions
def lightOn():
	# Turn the light on
	ledPWM.ChangeDutyCycle(100)
	while True:
		# If there is a state change, end the loop
		if stopThreads:
			break

# Turns the light off. This has a while true in it for compatibility with the more complex functions
def lightOff():
	# Turn the light off
	ledPWM.ChangeDutyCycle(0)
	while True:
		# If there is a state change, end the loop
		if stopThreads:
			break

# Blinks the light
def lightBlink():
	# Initilize the blink intervals, value in milliseconds
	intervalOn=750
	intervalOff=750

	# Initilize time (in milliseconds) and state
	t1=int(round(time.time()*1000))
	state='off'
	while True:
		# Set current time
		t2=int(round(time.time()*1000))

		# If the light is off and appropriate interval has passed, turn the light on
		if (state=='off') and (abs(t1-t2)>=intervalOn):
			ledPWM.ChangeDutyCycle(100)
			t1=t2
			state='on'

		# If the light is off and appropriate interval has passed, turn the light off
		elif (state=='on') and (abs(t1-t2)>=intervalOff):
			ledPWM.ChangeDutyCycle(0)
			t1=t2
			state='off'

		# If there is a state change, end the loop
		if stopThreads:
			break


def lightPulse():
	# Initilize the pulse brightness and modifier
	base=90
	mod=-1

	# Initilize the time (in milliseconds)
	t1=int(round(time.time()*1000))
	while True:
		# Set current time
		t2=int(round(time.time()*1000))

		# If enough time has passed, update the pulse width value
		if abs(t1-t2)>=20:
			base+=mod
			ledPWM.ChangeDutyCycle(base)
			t1=t2
			# If the light has hit one of the ends, change the direction
			if base<=10 or base>=90:
				mod=mod*-1

		# If there is a state change, end the loop
		if stopThreads:
			break

def SRRequest():
	#create channel
	with grpc.insecure_channel('localhost:50052') as channel:
		#audio stub
		audio_stub = audio_grpc.AudioStreamerStub(channel)

		#speech recognition stub
		sr_stub = sr_grpc.SpeechRecognitionStub(channel)

		#create audio request object
		request = audio.StreamRequest()

		#set audio params
		request.sample_rate = 16000
		request.num_channels = 1
		request.format = "paInt16"
		request.frames_per_buffer = 1024
		request.bytes_per_sample = 2

		#get speech recognition result synchronously (call sr_stub.RecognizeSpeech.future for asynchronous object)
		audio_stream = audio_stub.GetStream(request)
		sr_result = sr_stub.RecognizeSpeech(audio_stream)

		#parse json result
		parsed_result = json.loads(sr_result.result)

		#print result
		print("Speech Recognition Result: ", parsed_result['text'])
		
	return parsed_result['text']


def run():
	try:
		# Initilize relevant variables. stopThreads is a flag that controls when the while loops in the threads end. flag acts as a state tracker for capacitive touch/release
		global stopThreads
		stopThreads=False
		flag=True
		pivot=60

		# I have to start a thread for the rest of the program to work, so I start it off. This can be changed at will.
		ledThread=threading.Thread(target=lightOff)
		ledThread.start()

		# Run this until a user ends the program or it dies
		while True:
			# The MPR121 library doesn't have a function for changing the sensitivity threshold, as a work around, I manually calculate the current capacitence and then use that value to determine if there is touch.
			# In my experince 120-150 is standard when touching it, and 0-20 is standard when not. For this reason I chose to use 60 as the pivot value.
			val=abs(mpr121.baseline_data(11)-mpr121.filtered_data(11))

			# If touch is detected, perform the following actions
			if val>pivot and flag:
				print("Listening")
				flag=False

				# Get speech recognition request
				speechResult=SRRequest()

				# Check if the speech recognition result contains any key words for state changes. This can be done by NLU, but this is good enough for a proof of concept
				if ("on" in speechResult) ^ ("off" in speechResult) ^ ("blink" in speechResult) ^ ("pulse" in speechResult):
					# Kill the old loop, wait a bit?, then kill the thread, then reset the loop kill flag
					stopThreads=True
					#time.sleep(0.1)
					ledThread.join()
					stopThreads=False

					# God I wish python had switch statements.
					# Based on the detected key word, start that function as a new thread
					if "on" in speechResult:
						ledThread=threading.Thread(target=lightOn)
						ledThread.start()
					elif "off" in speechResult:
						ledThread=threading.Thread(target=lightOff)
						ledThread.start()
					elif "blink" in speechResult:
						ledThread=threading.Thread(target=lightBlink)
						ledThread.start()
					elif "pulse" in speechResult:
						ledThread=threading.Thread(target=lightPulse)
						ledThread.start()

				# Check if the speech recognition result contains any key words for ending the program
				if ("kill" in speechResult) ^ ("exit" in speechResult) ^ ("stop" in speechResult):
					# Kill threads and then exit the program
					stopThreads=True
					ledThread.join()
					break

			# Reset the touch flag when the capacitive touch medium is released
			if val<pivot and not(flag):
				print("")
				flag=True

	# when the program finishes or dies, do this
	finally:
		# Stop the threads if they haven't been already
		if not stopThreads:
			stopThreads=True
			ledThread.join()

		# Turn off the LED and capacitive touch breakout
		ledPWM.ChangeDutyCycle(0)
		GPIO.output(CTPID,GPIO.LOW)


if __name__ == '__main__':
	run()