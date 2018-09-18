import os
from stravalib import Client, exc, model
from requests.exceptions import ConnectionError, HTTPError
import requests
import csv
import shutil
import time
import datetime as dt
from datetime import datetime
import argparse
import logging

def setup_logging():
	logger = logging.getLogger()

	# optionally change log level, default is info
	LOG_LEVEL = os.environ.get("LOG_LEVEL")
	if not LOG_LEVEL:
	  LOG_LEVEL = "INFO"
	logger.setLevel(logging.getLevelName(LOG_LEVEL))

	# add logging to console
	consoleHandler = logging.StreamHandler()
	formatter = logging.Formatter(
	  '%(asctime)s - [%(levelname)-5.5s] - %(message)s'
	)
	consoleHandler.setFormatter(formatter)
	logger.addHandler(consoleHandler)

	# optionally create a log file
	LOG_FILE = os.environ.get("LOG_FILE")
	if LOG_FILE:
	  if not os.path.exists(LOG_FILE):
	    with open(LOG_FILE, "a"):
	      os.utime(LOG_FILE, None)
	  fileHandler = logging.FileHandler(LOG_FILE)
	  fileHandler.setFormatter(formatter)
	  logger.addHandler(fileHandler)

	# silence some other modules
	logging.getLogger("stravalib").setLevel(logging.WARNING)
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	return logger

def process_arguments():
	description = "Uploads Runkeeper data exports (GPX and CSV) to Strava."
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument(
		"access_token",
		type=str,
		help="Strava API access token."
	)
	parser.add_argument(
		"-d", "--distance_unit",
		choices=["mi", "km"], default="mi",
		help="unit of distance."
	)
	return parser.parse_args()

def main():
	logger = setup_logging()
	args = process_arguments()

	distance_factor = 1000 if args.distance_unit == "km" else 1609.344
	distance_label	= "Distance (" + args.distance_unit + ")"

	logger.debug("distance factor = " + str(distance_factor))
	logger.debug("distance label  = " + str(distance_label))

	# Opening the connection to Strava
	logger.info("Connecting to Strava")
	client = Client()

	# You need to run the strava_local_client.py script - with your application's ID and secret - to generate the access token.
	client.access_token = args.access_token
	try:
		athlete = client.get_athlete()
	except exc.AccessUnauthorized:
		logger.error("Strava authorization error: check your access token.")
		exit(1)
	logger.info("Now authenticated for " + athlete.firstname + " " + athlete.lastname)

	# Creating an archive folder to put uploaded .gpx files
	ARCHIVE = os.environ.get("ARCHIVE")
	if not ARCHIVE:
		ARCHIVE = "archive"
	if not os.path.exists(ARCHIVE):
		os.makedirs(ARCHIVE)

	# Function to convert the HH:MM:SS in the Runkeeper CSV to seconds
	def duration_calc(duration):
		# Splits the duration on the :, so we wind up with a 3-part array
		split_duration = str(duration).split(":")
		# If the array only has 2 elements, we know the activity was less than an hour
		if len(split_duration) == 2:
			hours = 0
			minutes = int(split_duration[0])
			seconds = int(split_duration[1])
		else:
			hours = int(split_duration[0])
			minutes = int(split_duration[1])
			seconds = int(split_duration[2])
		
		total_seconds = seconds + (minutes*60) + (hours*60*60)
		return total_seconds

	# Translate RunKeeper's activity codes to Strava's, could probably be cleverer
	def activity_translator(rk_type):
		if rk_type == "Running":
			return "Run"
		elif rk_type == "Cycling":
			return "Ride"
		elif rk_type == "Hiking":
			return "Hike"
		elif rk_type == "Walking":
			return "Walk"
		elif rk_type == "Swimming":
			return "Swim"
		elif rk_type == "Elliptical":
			return "Elliptical"
		else:
			return "None"
		# feel free to extend if you have other activities in your repertoire; Strava activity codes can be found in their API docs 


	# We open the cardioactivities CSV file and start reading through it
	with open('cardioActivities.csv') as csvfile:
		activities = csv.DictReader(csvfile)
		activity_counter = 0
		for row in activities:
			if activity_counter >= 599:
				logger.info("Upload count at 599 - pausing uploads for 15 minutes to avoid rate-limit")
				time.sleep(900)
				activity_counter = 0
			# used to have to check if we were trying to process the header row
			# no longer necessary when we process as a dictionary
			
			# if there is a gpx file listed, find it and upload it
			if ".gpx" in row['GPX File']:
				gpxfile = row['GPX File']
				strava_activity_type = activity_translator(str(row['Type']))
				if gpxfile in os.listdir('.'):
					logger.info("Uploading " + gpxfile)
					try:
						upload = client.upload_activity(
							activity_file = open(gpxfile,'r'),
							data_type = 'gpx',
							private = False,
							description = row['Notes'],
							activity_type = strava_activity_type
							)
					except exc.ActivityUploadFailed as err:
						errStr = str(err)
						# deal with duplicate type of error, if duplicate then continue with next file, else stop
						if errStr.find('duplicate of activity'):
							logger.info("Moving duplicate activity file {}".format(gpxfile))
							shutil.move(gpxfile,ARCHIVE)
							isDuplicate = True
							logger.warn("Duplicate File " + gpxfile)
						else:
							logger.error("Uploading problem raised: {}".format(err))
							exit(1)

					except ConnectionError as err:
						logger.error("No Internet connection: {}".format(err))
						exit(1)

					logger.info("Upload succeeded.\nWaiting for response...")

					try:
						upResult = upload.wait()
					except HTTPError as err:
						logger.error("Problem raised: {}\nExiting...".format(err))
						exit(1)
					except:
						logger.error("Another problem occured, sorry...")
						exit(1)
					
					logger.info("Uploaded " + gpxfile + " - Activity id: " + str(upResult.id))
					activity_counter += 1

					shutil.move(gpxfile, ARCHIVE)
				else:
					logger.warn("No file found for " + gpxfile + "!")

			#if no gpx file, upload the data from the CSV
			else:
				logger.info("Manually uploading " + row['Activity Id'])
				# convert to total time in seconds
				dur = duration_calc(row['Duration'])
				# convert to meters
				dist = float(row[distance_label]) * distance_factor
				starttime = datetime.strptime(str(row['Date']),"%Y-%m-%d %H:%M:%S")
				strava_activity_type = activity_translator(str(row['Type']))

				# designates part of day for name assignment above, matching Strava convention for GPS activities
				if 3 <= starttime.hour <= 11:
					part = "Morning "
				elif 12 <= starttime.hour <= 4:
					part = "Afternoon "
				elif 5 <= starttime.hour <=7:
					part = "Evening "
				else:
					part = "Night "
				
				try:
					upload = client.create_activity(
						name = part + strava_activity_type + " (Manual)",
						start_date_local = starttime,
						elapsed_time = dur,
						distance = dist,
						description = row['Notes'],
						activity_type = strava_activity_type
						)
						
					logger.info("Manually created " + row['Activity Id'])
					activity_counter += 1

				except ConnectionError as err:
					logger.error("No Internet connection: {}".format(err))
					exit(1)

		logger.info("Complete! Logged " + str(activity_counter) + " activities.")

if __name__ == '__main__':
	main()
