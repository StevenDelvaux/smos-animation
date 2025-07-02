import numpy as np
from datetime import date, datetime, timedelta
import requests
import os
import time
import contextlib
from PIL import Image, ImageFont, ImageDraw
#import subprocess

import upload_to_dropbox

putOnDropbox = True
prefix = 'images/'

def rounded(n):
	"""Transform a number into a string with 2 decimal digits. 
    """
	return ("{:.2f}".format(n))
	
def padzeros(n):
	"""
	Left pad a number with zeros. 
    """
	return str(n) if n >= 10 else '0'+str(n)

def downloadImage(date, north, smap):
	filename = getImageFilename(date, north, smap)
	path = 'https://data.seaice.uni-bremen.de/smos/png/' + filename;
	if smap:
		path = 'https://data.seaice.uni-bremen.de/smos_smap/png/' + ('north' if north else 'south') + '/' + str(date.year) + '/' + filename;
	localfilename = prefix + filename
	file_object = requests.get(path) 
	with open(localfilename, 'wb') as local_file:
		local_file.write(file_object.content)
	print('downloaded', filename)	
	
def makeAnimation(enddate, frames, animationFileName, getFileNameFromDate, missingDates, north=True):
	date = enddate - timedelta(days = frames)
	date = datetime(date.year, date.month, date.day)
	
	filenames = []
	endpause = 5
	for k in range(frames):
		#missing = False
		date = date + timedelta(days = 1)
		print('plotting date: ',date)
		if False: #date in missingDates:
			print('missing date: ', date)
			continue
			#date = date - timedelta(days = 1)
			#missing = True
		localfilename = getFileNameFromDate(date)
		if not os.path.isfile(localfilename):
			downloadImage(date, north, smap)
		img = Image.open(localfilename)
		img1 = ImageDraw.Draw(img)
		if smap:
		    img1.rectangle(((1063, 2095), (1460, 2150)), fill ="#ffffff", outline ="white")
		elif north:
			img1.rectangle(((360, 725), (530, 755)), fill ="#ffffff", outline ="white")
		else:
			img1.rectangle(((314, 555), (475, 583)), fill ="#ffffff", outline ="white")
		localfilenamebis = localfilename.replace(".png", "_bis.png" )
		img.save(fp=localfilenamebis)	
		filenames.append(localfilenamebis)
		#if missing:
		#	date = date + timedelta(days = 1)		
	print(filenames)
	lastfilename = filenames[-1]
	for k in range(endpause):
		filenames.append(lastfilename)
	with contextlib.ExitStack() as stack:
		imgs = (stack.enter_context(Image.open(f)) for f in filenames)
		img = next(imgs)
		# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
		startdate = enddate - timedelta(days = frames-1)
		img.save(fp=animationFileName, format='GIF', append_images=imgs, save_all=True, duration=500, loop=0) #, quality=25, optimize=True, compress_level=9)
		#compress_string = "magick mogrify -layers Optimize -fuzz 7% " + animationFileName
		#subprocess.run(compress_string, shell=True)

def getDateIsoString(date):
	 return str(date.year) + str(padzeros(date.month)) + str(padzeros(date.day))

def getImageFilename(date, north, smap):
	if smap:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_' + ('north' if north else 'south') + '_mix_sit_v300.png'
	else:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_hv' + ('north' if north else 'south') + '_rfi_l1c.png'

def getanimationFileName(north, smap):	
	return 'animation_smos_' + ('smap_' if smap else '') + ('' if north else 'south_') + 'latest' + '.gif'
		
north = True
smap = True

today = datetime.today()
today = datetime(today.year, today.month, today.day)
yesterday = today - timedelta(days = 1)
date = today
	
animationFileName = getanimationFileName(north, smap)

count = 7
skipend = 0
makeAnimation(yesterday - timedelta(days = skipend), count, animationFileName, lambda date: prefix + getImageFilename(date, north, smap), [], north) #missingDates
filenames = [animationFileName]
if putOnDropbox:
	dropbox_client.uploadToDropbox(filenames)