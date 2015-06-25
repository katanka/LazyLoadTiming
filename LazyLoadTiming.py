from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from multiprocessing import Process, Queue, Manager
from time import sleep
import urllib2, json, sys, psutil

def processPage(url, data):
	success = False
	try:
		driver = webdriver.Chrome()
		driver.get(url)

		wait = WebDriverWait(driver, 10)
		element = wait.until(lambda x: (driver.execute_script("return window.performance.timing.loadEventStart") > 0))
		performanceTiming = driver.execute_script("return window.performance.timing")
		success = True
		navigationStart = performanceTiming['navigationStart']
		domContentLoadedEventStart = performanceTiming['domContentLoadedEventStart'] - navigationStart
		domContentLoadedEventEnd = performanceTiming['domContentLoadedEventEnd'] - navigationStart
		loadEventStart = performanceTiming['loadEventStart'] - navigationStart
		driver.quit()
	except Exception, e:
		print e
	finally:
		try:
			driver.quit()
		except Exception, e:
			pass

	if success:
		data.append({
			'domContentLoadedEventStart': domContentLoadedEventStart,
			'domContentLoadedEventEnd': domContentLoadedEventEnd,
			'loadEventStart': loadEventStart
		})

# utility functions
def median(data):
    half = len(data) // 2
    data.sort()
    if not len(data) % 2:
        return (data[half - 1] + data[half]) / 2.0
    return data[half]

def mean(data):
    return sum(data)/float(len(data))

def _ss(data):
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss

def std(data):
    ss = _ss(data)
    pvar = ss/float(len(data)) # the population variance
    return pvar**0.5


if __name__ == "__main__":
	print 'Setting up...'
	workers = list()
	queue = Manager().list()

	try:
		config = json.loads(open('config.json').read())
	except IOError, e:
		print "Error: config.json not found"
		exit()

	if not ('URL' in config.keys() and 'noexternals' in config.keys() and 'samplesize' in config.keys() and 'max_cpu_usage_percent' in config.keys() and 'max_worker_threads' in config.keys()):
		print "Error, config file must contain the following keys: URL, noexternals, samplesize, max_cpu_usage_percent, max_worker_threads"
		exit()


	url = config['URL']+"?useskin="+config['skin']+("&noexternals=1" if config['noexternals']==1 else "")
	total_calls = config['samplesize']
	cpu_threshold = config['max_cpu_usage_percent']
	max_worker_threads = config['max_worker_threads']

	print "URL: " + url
	print "Sample size: " + `total_calls`
	print "CPU Threshold: " + `cpu_threshold`
	print "Max worker threads: " + `max_worker_threads`


	print 'Done'

	print 'Starting testing...'

	while len(queue) < total_calls:

		percentDone = len(queue)/float(total_calls)
		linelength = 80
		sys.stdout.write('\r0% |'+'='*(int(percentDone*linelength)) + ' '*(linelength - int(percentDone*linelength)) + '| 100%')


		# add new threads if needed
		if len(workers) < max_worker_threads and psutil.cpu_percent() < cpu_threshold and (len(queue)+1) < total_calls:
			new_worker = Process(target=processPage, args=[url, queue])
			workers.append(new_worker)
			new_worker.start()

		sleep(0.25)

		#remove dead threads from list
		for worker in workers:
			if not worker.is_alive():
				worker.join()
				workers.remove(worker)

		sys.stdout.flush()


	print '\rDone\n'

	for worker in workers:
		worker.join()


	print 'Starting result processing...'
	data = queue[:total_calls]

	if len(data) < 2:
		print "Error: Not enough data"
		exit()

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
		data_reformat[key]['stats']['mean'] = mean(data_reformat[key]['data'])
		data_reformat[key]['stats']['median'] = median(data_reformat[key]['data'])
		data_reformat[key]['stats']['stdev'] = std(data_reformat[key]['data'])

	print "Done"

	print "With a sample size of " + `len(data)`
	for key in data_reformat.keys():
		print "==== " + key + " ===="
		for stat in data_reformat[key]['stats'].keys():
			print stat + ": " + `round(data_reformat[key]['stats'][stat])`
