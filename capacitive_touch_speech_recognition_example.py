# P14: Pin closest to CPU is Ground
# P12: Pin furthest from CPU is Ground
# P4: Pin furthest from CPU is Ground (Pin 4)
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
GPIO.setup(CTPID, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(CTPID,GPIO.HIGH)

# print(type(board.SCL))

# Set up I2C, working on figuring out how to manipulate values so we can connect to different GPIO pins. I'm fairly certain you can just provide the GPIO number
i2c=busio.I2C(board.SCL, board.SDA)
mpr121=adafruit_mpr121.MPR121(i2c)
flag=True

try:
	while True:
		if mpr121[11].value and flag:
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

		if not(mpr121[11].value) and not(flag):
			print("")
			flag=True


except:
	print("Exiting...")

finally:
	# Always turn off the chip (not technically necessary, but I do it anyway)
	GPIO.output(CTPID,GPIO.LOW)
