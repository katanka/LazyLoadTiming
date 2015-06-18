from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from multiprocessing import Pool, Manager
import urllib2, json, sys
from time import sleep
import numpy

workers = []
data = Manager().list()

total_calls = 5
current_calls = 0
max_workers = 5
current_workers = 0

url = "http://sandbox-mercury.muppet.wikia.com/wiki/Muppet_caps_(New_Era)"

mobile_emulation = { "deviceName": "Apple iPhone 6" }
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

def processPage(n):

	driver = False
	
	try:
		driver = webdriver.Chrome(chrome_options=chrome_options)
		driver.get(url)

		wait = WebDriverWait(driver, 10)
		element = wait.until(lambda x: (driver.execute_script("return window.performance.timing.loadEventStart") > 0))

		performanceTiming = driver.execute_script("return window.performance.timing")
		navigationStart = performanceTiming['navigationStart']
		domContentLoadedEventStart = performanceTiming['domContentLoadedEventStart'] - navigationStart
		domContentLoadedEventEnd = performanceTiming['domContentLoadedEventEnd'] - navigationStart
		loadEventStart = performanceTiming['loadEventStart'] - navigationStart
	finally:
		if(driver):
			driver.quit()
	
	return {
		'domContentLoadedEventStart': domContentLoadedEventStart,
		'domContentLoadedEventEnd': domContentLoadedEventEnd,
		'loadEventStart': loadEventStart,
	}


def waitMessage():
	i = 0
	while True:
	    if result.ready():
	        break
	    else:
	        sys.stdout.write('\r'+'.'*(i%3 + 1) + ' '*(2-i%3))
	        i += 1
	        sleep(1)
	        sys.stdout.flush()
	sys.stdout.write('\rDone\n')

if __name__ == "__main__":
	try:
		print 'Starting pool...'
		pool = Pool(processes=5)              # start 5 worker processes
		print 'Done'


		print 'Starting testing...'
		result = pool.map_async(processPage, range(total_calls))

		waitMessage()

		data = result.get()

		print 'Starting result processing...'

		data_reformat = dict() # dictionary which holds data for each event

		for key in data[0].keys():
			# for each event, we want the raw data, and then statistics about the data
			data_reformat[key] = {
				'data': [],
				'stats': {
					'mean': 0,
					'median': 0,
					'stdev': 0
				}
			}

		# insert the data
		for result in data:
			for key in result.keys():
				data_reformat[key]['data'].append(result[key])
		
		# compute the stats
		for key in data_reformat.keys():
			data_reformat[key]['stats']['mean'] = numpy.mean(data_reformat[key]['data'])
			data_reformat[key]['stats']['median'] = numpy.median(data_reformat[key]['data'])
			data_reformat[key]['stats']['stdev'] = numpy.std(data_reformat[key]['data'])

		for key in data_reformat.keys():
			print "==== " + key + " ===="
			for stat in data_reformat[key]['stats'].keys():
				print stat + ": " + `data_reformat[key]['stats'][stat]` 

	except Exception as e:
		print e
