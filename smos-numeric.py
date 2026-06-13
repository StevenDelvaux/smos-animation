import numpy as np
from netCDF4 import Dataset
from datetime import date, datetime, timedelta
import requests
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
import time
import contextlib
from PIL import Image, ImageFont, ImageDraw
#import subprocess

import dropbox_client

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

def downloadNetcdf(date, north, smap):
	filename = getNcFilename(date, north, smap)
	path = 'https://data.seaice.uni-bremen.de/smos/ncs/' + filename;
	if smap:
		path = 'https://data.seaice.uni-bremen.de/smos_smap/netCDF/' + ('north' if north else 'south') + '/' + str(date.year) + '/' + filename;
	localfilename = prefix + filename
	file_object = requests.get(path) 
	with open(localfilename, 'wb') as local_file:
		local_file.write(file_object.content)
	print('downloaded', filename)

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
	
def dayvol(date, north,smap):
	matrix = getThickness(date, north, smap)
	
	ocean = 0
	land = 0
	beige = 0
	colored = 0
	other = 0 
	weighted = 0
	
	for row in range(rows):
		#print('process row', row)
		for col in range(columns):
			thickness = getPixelThickness(row,col,matrix)
			if thickness == 51:
				beige += 1
				weighted += 0.6
			elif thickness > 0 and thickness < 51:
				colored += 1
				weighted += thickness/100.0
			elif thickness == 0:
				ocean += 1
			elif thickness == -2:
				land += 1
			else:
				other += 1
		
	print('processed ', date, beige, colored, weighted, ocean, land, other)
	return [beige, round(weighted)]

def getPixelThickness(row,col,matrix):
			
	if (row > 530 and col < 128) or (row > 564 and col < 163) or row > 610 or col < 80 or col > 490 or row < 110 or (row < 150 and col > 270) or (row < 180 and col > 360) or (row < 450 and col > 420) or (col < 120 and row > 280 and row < 450): # or row < 400:
		return -2

	refpoint = refThickness[row,col]
	#print(refpoint, type(refpoint))
	if (smap and not type(refpoint) is np.float32) or refpoint == -2:
		return -2

	thickness = matrix[row, col]
	if thickness != -2:
		return thickness
		
	radius = 1
	nradius = 0
	rowcorrection = -1
	colcorrection = 0
	
	while(True):
		if row+rowcorrection >=0 and row+rowcorrection < rows and col+colcorrection >=0 and col+colcorrection < columns:
			thickness = matrix[row+rowcorrection, col+colcorrection]
			#print(thickness)
			if thickness != -2:
				return thickness
		nradius += 1
		#print('radius', nradius)
		if(nradius >= 4*radius):
			radius += 1
			#print('radius', row, col, thickness, radius)
			nradius = 0
			rowcorrection = -radius
			colcorrection = 0
		elif(nradius > 3*radius):
			rowcorrection -= 1
			colcorrection += 1
		elif(nradius > 2* radius):
			rowcorrection -= 1
			colcorrection -= 1
		elif(nradius > radius):
			rowcorrection += 1
			colcorrection -= 1
		else:
			rowcorrection += 1
			colcorrection += 1	
	
def getThickness(date, north, smap):
	filename = getNcFilename(date, north, smap)
	try:
		localfilename = prefix + filename
		print(localfilename, smap)
		f = Dataset(localfilename, 'r', format="NETCDF4")		
		result = f.variables['thickness' if not smap else 'combined_thickness'][:]#.squeeze()	combined_thickness
		print('got result', filename)
		f.close()
	except:
		print('hola exception')
		os.remove(localfilename)
		f.close()
		
	if result.shape[0] != rows:
		raise Exception("Matrix row count should be " + str(rows) + " but was " + str(result.shape[0]))
	if result.shape[1] != columns:
		raise Exception("Matrix column count should be " + str(columns) + " but was " + str(result.shape[1]))
		
	return result
	
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

def plotGraphSmap(inputFileName, outputFileName, title, ymin, ymax, ylabel, days, skip, all = False):
	fig, ax = plt.subplots(figsize=(8, 5))
	dates = np.arange(1,days+1)	
	with open(inputFileName, 'r') as f:
		lines = f.readlines()
	if(all):
		plotLine(ax, lines, dates, -17, '2010 (SMOS)', (0.65,0.65,0.65), days, skip, 'dashed')
		plotLine(ax, lines, dates, -16, '2011 (SMOS)', (0.44,0.19,0.63), days, skip, 'dashed')
		plotLine(ax, lines, dates, -15, '2012 (SMOS)', (0.0,0.13,0.38), days, skip, 'dashed')
		plotLine(ax, lines, dates, -14, '2013 (SMOS)', (0,0.44,0.75), days, skip, 'dashed')
		plotLine(ax, lines, dates, -13, '2014 (SMOS)', (0.0,0.69,0.94), days, skip, 'dashed')
		plotLine(ax, lines, dates, -12, '2015', (0,0.69,0.31), days, skip)
		plotLine(ax, lines, dates, -11, '2016', (0.57,0.82,0.31), days, skip)
		plotLine(ax, lines, dates, -10, '2017', (1.0,0.75,0), days, skip)
		plotLine(ax, lines, dates, -9, '2018', (0.9,0.4,0.05), days, skip)
		plotLine(ax, lines, dates, -8, '2019', (1.0,0.5,0.5), days, skip)
		plotLine(ax, lines, dates, -7, '2020', (0.58,0.54,0.33), days, skip)
		#plotLine(ax, lines, dates, -4, '2021', (0.4,0.19,0.2), days, skip) #(0.4,0,0.2)
		#plotLine(ax, lines, dates, -3, '2022', (0.2,0.5,0.7), days, skip) #(0.7,0.2,0.3)
		#plotLine(ax, lines, dates, -2, '2023', (0.6,0,0), days, skip)
		#plotLine(ax, lines, dates, -1, '2024', (1.0,0,0), days, skip)
		plotLine(ax, lines, dates, -6, '2021', (0.4,0,0.2), days, skip)
		plotLine(ax, lines, dates, -5, '2022', (0.7,0.2,0.3), days, skip)
		plotLine(ax, lines, dates, -4, '2023', (0.5,0.3,0.1), days, skip)
		plotLine(ax, lines, dates, -3, '2024', (0.3,0.3,0.3), days, skip)
		plotLine(ax, lines, dates, -2, '2025', (0.75,0,0), days, skip)
		plotLine(ax, lines, dates, -1, '2026', (1,0,0), days, skip)
		
	ax.set_ylabel(ylabel)
	ax.set_title(title)
	ax.legend(loc=1, prop={'size': 8})
	ax.axis([1, days, ymin, ymax])
	ax.grid(True);
	
	if skip == 0:
		months = ['1 Jun', '11 Jun', '21 Jun', '1 Jul', '11 Jul', '21 Jul', '31 Jul', '10 Aug', '20 Aug', '30 Aug']
		ax.set_xticks([1,11,21,31,41,51,61,71,81,91], ['', '', '', '', '', '', '', '', '', ''])
		ax.xaxis.set_minor_locator(ticker.FixedLocator([1.1,10.9,20.9,30.9,40.9,50.9,60.9,70.9,80.9,90.9]))
	ax.xaxis.set_minor_formatter(ticker.FixedFormatter(months))
	ax.tick_params(which='minor', length=0)	
	
	fig.savefig(outputFileName)

def plotLine(ax, lines, dates, idx, label, color, days, skip, linestyle = 'solid'):
	line = lines[idx].split(",")			
	row =  np.array([i.lstrip() for i in np.array(line[skip+1:skip+days+1])])
	numberOfDays = len(row)
	row = row.astype(float)
	if numberOfDays < days:
		row = np.pad(row, (0, days - numberOfDays), 'constant', constant_values=(np.nan,))	
	ax.plot(dates, row, label=label, color=color, linestyle=linestyle, linewidth=(3 if idx==-1 else 1));	

def getDateIsoString(date):
	 return str(date.year) + str(padzeros(date.month)) + str(padzeros(date.day))

def getNcFilename(date, north, smap):
	if smap:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_' + ('north' if north else 'south') + '_mix_sit_v300.nc'
	else:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_hv' + ('north' if north else 'south') + '_rfi_l1c.nc'

def getImageFilename(date, north, smap):
	if smap:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_' + ('north' if north else 'south') + '_mix_sit_v300.png'
	else:
		return str(date.year)+ padzeros(date.month) + padzeros(date.day) + '_hv' + ('north' if north else 'south') + '_rfi_l1c.png'

def getCsvFilename(north, smap, weighted = True):	
	return 'smos-' + ('smap-' if smap else '') + ('' if north else 'south') + ('weighted' if weighted else 'beige') + ('' if north else '-daily') + '.csv'

def getGraphFilename(north, smap, weighted = True):	
	return 'smos-' + ('smap-' if smap else '') + ('' if north else 'south') + ('weighted' if weighted else 'beige') + ('' if smap else '-2023') + '.png'

def getanimationFileName(north, smap):	
	return 'animation_smos_' + ('smap_' if smap else '') + ('' if north else 'south_') + 'latest' + '.gif'
		
def appendToCsvFile(filename, data):
	print('inside appendToCsvFile', filename, data)
	if len(data) == 0:
		return
	with open(filename, "a") as myfile:
		myfile.write( ',' + ','.join(map(str,data)))
		
north = True
smap = True


rows = 896 if north else 664
columns = 608 if north else 632
allweighted = []
allbeige = []
abeige = []
aweighted = []

refDate = datetime(2017, 6, 25) if north else datetime(2017, 11, 25)
refThickness = getThickness(refDate, north, smap)
missingDates = [datetime(2025, 6, 27),datetime(2025, 6, 26),datetime(2025, 6, 25),datetime(2025, 6, 24),datetime(2025, 6, 23),datetime(2025, 6, 22),datetime(2025, 6, 21),datetime(2025, 6, 20),datetime(2025, 6, 19),datetime(2025, 6, 18),datetime(2025, 6, 17),datetime(2025, 6, 8),datetime(2025, 6, 6),datetime(2025, 6, 4), datetime(2022, 8, 19), datetime(2024, 6, 28), datetime(2024, 6, 23), datetime(2024, 6, 18), datetime(2024, 6, 16), datetime(2024, 6, 13), datetime(2015, 6, 16), datetime(2015, 6, 17), datetime(2018, 6, 27), datetime(2023, 6, 22), datetime(2019, 6, 19), datetime(2019, 6, 20), datetime(2019, 6, 21), datetime(2019, 6, 22), datetime(2019, 6, 23), datetime(2019, 6, 24), datetime(2019, 6, 25), datetime(2019, 6, 26), datetime(2019, 6, 27), datetime(2019, 6, 28), datetime(2019, 6, 29), datetime(2019, 6, 30)] #[datetime(2010, 6, 6), datetime(2011, 5, 18), datetime(2015, 6, 30), datetime(2016, 6, 11), datetime(2017, 5, 10), datetime(2022, 6, 9)]

today = datetime.today()
today = datetime(today.year, today.month, today.day)
yesterday = today - timedelta(days = 1)
date = yesterday

while date < today - timedelta(days = 0):
	print('checking date',date)
	downloadNetcdf(date, north, smap)
	[beige, weighted] = [0,0] if date in missingDates else dayvol(date,north,smap)
	if not date in missingDates:
		aweighted.append(weighted)
		abeige.append(beige)
	date = date + timedelta(days = 1)
	
csvFilename = getCsvFilename(north, smap)
csvBeigeFilename = getCsvFilename(north, smap, False)
graphFilename = getGraphFilename(north, smap)
animationFileName = getanimationFileName(north, smap)

appendToCsvFile(csvFilename, aweighted)
appendToCsvFile(csvBeigeFilename, abeige)
time.sleep(5)
	
plotGraphSmap(csvFilename, graphFilename, "SMOS/SMAP Arctic sea ice: weighted pixel count", 3000, 32400, "pixels",92,0,True)
time.sleep(5)
if putOnDropbox:
	dropbox_client.uploadToDropbox([csvFilename,graphFilename])
	
animationFileName = getanimationFileName(north, smap)

count = 7
skipend = 0
makeAnimation(yesterday - timedelta(days = skipend), count, animationFileName, lambda date: prefix + getImageFilename(date, north, smap), [], north) #missingDates
filenames = [animationFileName]
if putOnDropbox:
	dropbox_client.uploadToDropbox(filenames)