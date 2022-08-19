# P14: Pin closest to CPU is Ground
# P12: Pin furthest from CPU is Ground
# P4: Pin furthest from CPU is Ground (Pin 4)
# Programs that use GPIO and i2c must be executed using sudo to give python access to the hardware
# Imports for capacititve touch
import RPi.GPIO as GPIO
from time import sleep
import board
import busio
import adafruit_mpr121

# Imports for Speech Recognition
import json
import grpc
import rero_grpc.audio_pb2_grpc as audio_grpc
import rero_grpc.audio_pb2 as audio
import rero_grpc.speech_recognition_pb2_grpc as sr_grpc

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Provide power to the breakout board
CTPID=14
GPIO.setup(CTPID, GPIO.OUT, initial=GPIO.HIGH)

# Set up I2C, working on figuring out how to manipulate values so we can connect to different GPIO pins. I'm fairly certain you can just provide the GPIO number
i2c=busio.I2C(board.SCL, board.SDA)
mpr121=adafruit_mpr121.MPR121(i2c)
flag=True

try:
	while True:
		# This library doesn't have a function for changing the sensitivity threshold, as a work around, I manually calculate the current capacitence and then use that value to determine if there is touch.
		# In my experince 120-150 is standard when touching it, and 0-20 is standard when not. For this reason I chose to use 60 as the pivot value.
		val=abs(mpr121.baseline_data(11)-mpr121.filtered_data(11))
		if val>60 and flag:
		# if mpr121[11] and flag:
			print("Listening")
			flag=False
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

		if not(val>60) and not(flag):
		# if not(mpr121[11]) and not(flag):
			print("")
			flag=True


except:
	print("Exiting...")

finally:
	# Always turn off power to the chip (not technically necessary, but I do it anyway)
	GPIO.output(CTPID,GPIO.LOW)
