# Runkeeper to Strava Uploader

Uses the Strava v3 API (documented [here](http://strava.github.io/api/)) to upload GPX and CSV activities exported from RunKeeper.

Borrows liberally from @anthonywu's [Strava API Experiment](https://github.com/anthonywu/strava-api-experiment) and @marthinsen's [Strava Upload](https://github.com/marthinsen/stravaupload) projects. Uses @hozn's [stravalib](https://github.com/hozn/stravalib) to interact with the Strava API. Thanks to all.

## Usage:
1. First, you need to **register an application with the Strava API service.** Go to the [Strava API Management Page](https://www.strava.com/settings/api), and create a new application. Note the Client ID and Client Secret - you will need them later.
2. Next, you need to **get your data from Runkeeper.** Go to the Settings page, and look for "Export Data" near the bottom. Define your time range, wait a minute or two, and then click download. Unzip the file - the directory should have .gpx files for all of your GPS-tracked runs, and two spreadsheets - "measurements.csv" and "cardio_activities.csv". 
3. Open a shell (accessed by using the "Terminal" application on MacOS) and `cd` to the data directory (the folder you just downloaded - should be something like "runkeeper-data-export-1234567")
4. (Optional but advised) Create a virtual Python environment: `virtualenv venv` and activate it: `. venv/bin/activate`. (When done, deactivate the environment: `deactivate`)
4. Install the requirements - from any shell run `pip install -r <path to strava uploader folder>/requirements.txt`
5. Next, we need to **get an Authorization Token from Strava** for your Athlete account. Run the command `python <path to strava uploader folder>/strava_local_client.py get_write_token <client_id> <client_secret>`, where you replace `<client_id>` and `<client_secret>` with the codes you pulled from the [Strava API Management Page](https://www.strava.com/settings/api). It should open a browser and ask you to log in to Strava. You should then be shown an access code - copy this.
6. Now we're ready to upload. Run `python <path to strava uploader folder>/uploader.py <the access code you just obtained>`, and let it run!

**A few notes on how this works:**
- The script will crawl through the cardio activities csv file line for line, uploading each event.
- Right now it handles runs, rides, walks, swims, hikes and elliptical exercises. You can add more - be sure to grab the RunKeeper definition and the Strava definition and add to the `activity_translator` function.
- If there is a GPX file listed in the last column, it will look for that file in the directory. If there is no GPX file, it will manually upload using the distance and duration data listed in the spreadsheet.
- Strava's API [rate-limits you to 600 requests every 15 minutes](http://strava.github.io/api/#rate-limiting). The `uploader.py` script will automatically wait for 15 minutes when the upload count hits 599. This is probably too conservative - feel free to adjust.
- It will move successfully uploaded GPX files to a sub-folder called archive.
- It will try to catch various errors, and ignore duplicate files.
- The level of detail of logging can be adjusted using the `LOG_LEVEL` environment variable.
- It can log everything in a file. Use the `LOG_FILE` environment variable to specify the location.

## Misc other notes:
- Do NOT modify or even save (without modification) the CSV from Excel. Even if you just open it and save it with no modification, Excel changes the date formatting which will break this script. If you do need to modify the CSV for some reason (e.g., mine had a run with a missing distance, not clear why), do it in Sublime or another text editor.
- I personally ran into a few errors of "malformed GPX files". You can try opening the file in a text editor and looking for issues - look for missing or redundant closure tags (e.g., `</trkseg>`) - that was the issue with one of my files. You could also try to use other solutions - some ideas that solved other issues [here](https://support.strava.com/hc/en-us/articles/216942247-How-to-Fix-GPX-File-Errors).

## Updates specific to this forked repository

You can use this script to upload a non-Runkeeper file in CSV format.  The current Runkeeper CSV file format includes the following columns: Activity Id, Date,Type, Route Name, Distance (mi), Duration, Average Pace, Average Speed (mph), Calories Burned, Climb (ft), Average Heart Rate (bpm), Friend's Tagged, Notes, GPX File.  If you wish to upload a non-Runkeeper file you have to create a cardioActivities.csv in this folder containing at least the following columns: Activity Id, Date, Type, Distance (mi), Duration.  The non-Runkeeper file must have matching column names to the Runkeeper original!  The GPX file if included should be a filename located in the same folder.

### Some specific information about formatting requirements
- The Activity Id is just an internal identifier that must be unique per activity.  You can use numbers, letters, whatever.
- Date format must be: YYYY-MM-DD HH:MM:SS.
- Distance can be decimal formatted in miles or km. Default this is miles, but with the `--distance_unit` command argument, this can be changed to km. This is converted to meters for Strava.
- Duration must be formatted as MM:SS even for times over 1 hour!  So 1 hour 5 minutes 3 seconds = 65:03.  This is converted to total duration in seconds in the duration_calc function if you want to use a different format.
- Some attribute errors are returned when running this script which seem to be related to missing pieces in the create_activity API call; however, the activity is still successfully uploaded if these errors are received.
- Pip install requirements only works with versions of pip < 9.0.3.  I did not update the strava_local_client.py file to work with the updated pip as it was very simple to downgrade pip to a workable version.
- When manually creating an activity (no GPX file), only the following information is saved: Date, Type, Distance (mi), and Duration.  The rest of the file row contents are ignored.

### Patches merged from [https://github.com/possibilityleft/strava-uploader](https://github.com/possibilityleft/strava-uploader)
The primary changes from the original branch are updating the CSV file to be read as a dictionary, allowing Runkeeper to change their file format all they want as long as they keep the important column headers the same.  I did this because they added some new columns since the original script was written and it was difficult to figure out what the old file format was, and what updates needed to be made to accomodate the new format.

### Patches in this branch
* added required command argument to provide access token without changing the script
* added optional command argument to select distance unit
* replaced logger function by logging module
* fixed archive to be folder and not a file (last archived GPX)
* handle Stravalib authorization error a bit nicer
