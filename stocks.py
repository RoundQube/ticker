#!/opt/local/bin/python

import json
import time
import sqlite3
from datetime import date, timedelta
from yahoo_finance import Share

'''
Function:
	calculate
Notes:
	Calculates EMA, MACD, RSI etc..
'''
def calculate(ticker):
	stockDB = "stocks.db"
	dateTime = date.today()
	d = date.today() - timedelta(days=90)
	stock = Share(ticker)
	closePrice = float(stock.get_price())
	jsonData = stock.get_historical(d.strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"))
	jsonData = json.dumps(jsonData)
	jsonData = json.loads(jsonData)

	# ticker not in DB yet so we have to perform avg; ignore MACD, Signal & Histogram since there is no historical data to base our calculations on
	if(inDB(ticker)) == False:

		slowEMAAvg = 0.0
		fastEMAAvg = 0.0

		for i in range(1, 13):
			fastEMAAvg += float(jsonData[i]["Close"])

		fastEMAAvg /= 12

		for i in range(1, 27):
			slowEMAAvg += float(jsonData[i]["Close"])

		slowEMAAvg /= 26
		# end slowEMAAvg

		rsi14day = calculateRSI(ticker)
	
		writeDB(dateTime, ticker, closePrice, fastEMAAvg, slowEMAAvg, 0, 0, 0, rsi14day)

	# record exists in DB so we use exiting data as a precursor to generating values for the new record
	else:
		conn = sqlite3.connect(stockDB)
		cursor = conn.cursor()

		# pull latest row related to ticket being processed (hence the limit 1)
		cursor.execute('SELECT closeprice, fastema, slowema, signal FROM stocks WHERE ticker = ? ORDER BY id DESC limit 1', (ticker, ))
		rows = cursor.fetchall()

		# store the row data into variables we can work with
		for row in rows:
			closePriceFromDB, fastEMAFromDB, slowEMAFromDB, signalFromDB  = row

		# init variables
		fastema = 0.0
		slowema = 0.0
		macd = 0.0
		signal = 0.0
		histogram = 0.0

		# 12-Day: EMA(n) = Closing_Price(n) * (2 / 13) + EMA(n-1) * (1 - (2 / 13))
		fastema = (float(closePrice) * (2 / float(13))) + (float(fastEMAFromDB) * (1 - (2 / float(13))))
		
		# 26-Day: EMA(n) = Closing_Price(n) * (2 / 26) + EMA(n-1) * (1 - (2 / 26))
		slowema = (float(closePrice) * (2 / float(27))) + (float(slowEMAFromDB) * (1 - (2 / float(27))))
	
		# MACD: 12_Day_EMA(n) - 26_Day_EMA(n)
		macd = fastema - slowema

		# Signal: Signal(n) = MACD(n) * (2 / 10) + Signal(n-1) * (1 - (2 / 10))
		signal = (macd * (2 / float(10))) + (float(signalFromDB) * (1 - (2 / float(10))))

		# Histogram: MACD(n) - Signal(n)
		histogram = float(macd) - float(signal)

		rsi14day = calculateRSI(ticker)

		writeDB(dateTime, ticker, closePrice, fastema, slowema, macd, signal, histogram, rsi14day)

		# only allow notifications to be sent if data exists in the DB
		sendNotification()
'''
Function:
	calculateRSI
Notes:
	Calculate the 14 day RSI based on historical data
'''
def calculateRSI(ticker):

	stock = Share(ticker)
	closePrice = float(stock.get_price())
	d = date.today() - timedelta(days=90)
	dateTime = date.today()
	
	# init variables
	avgGain = 0.0
	avgLoss = 0.0
	rs = 0.0
	rsi14day = 0.0

	jsonData = stock.get_historical(d.strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"))
	jsonData = json.dumps(jsonData)
	jsonData = json.loads(jsonData)

	for i in range(0, 15):
		currentPrice = float(jsonData[i]["Close"])
		prevPrice = float(jsonData[i+1]["Close"])
		change = currentPrice - prevPrice

		# sum our avg gains and losses
		if change > 0:
			avgGain += abs(change)
		else:
			avgLoss += abs(change)
	
	# needs to be positive value
	avgGain = abs(avgGain) / 14
	avgLoss = abs(avgLoss) / 14

	# this is the RSI calculation method
	if avgLoss != 0:
		rs = float(avgGain) / float(avgLoss)
		if rs >= 0:
			rsi14day = 100 - (100 / (1 + float(rs)))

	return rsi14day
'''
Function:
	sendNotification
Notes:
	Read csv of tickers one is interested in and send email summary. NOTE: the seperation between tickers.csv and alert_tickers.csv is to allow the user to allow ths script to pull data for a variety of tickers to keep building historical data, however, only send notifications for the tickers in alert_tickers.csv to allow the user some flexibility 

'''
def sendNotification():
	
	emailBody = ''

	# read through alert tickers file
	with open("alert_tickers.csv") as f:
		for line in f:
			ticker = line.rstrip('\n')

			# open DB connection, read contents and alert based on RSI or MACD approach thresholds
			# for RSI: we alert on >= (greater than / equal to) 30 and <= (less than / equal to) 70
			stockDB = 'stocks.db'
			conn = sqlite3.connect(stockDB)
			cursor = conn.cursor()

			cursor.execute('SELECT rsi14day FROM stocks WHERE id = (SELECT MAX(id) FROM stocks) AND ticker = ?', (ticker, ))
			rows = cursor.fetchall()
			
			# iterate through rows with the ticker filter for RSI threshold
			for row in rows:
				rsiFromDB = row
				
				if rsiFromDB[0] >= 70:
					emailBody = "%s\n%s - RSI is above 70" % (emailBody, ticker)
				elif rsiFromDB[0] <= 30:
					emailBody = "%s\n%s - RSI is below 30" % (emailBody, ticker)

			cursor.execute('SELECT histogram FROM stocks WHERE ticker = ? ORDER BY id DESC limit 2', (ticker, ))
			rows = cursor.fetchall()

			# iterate through rows with the ticker filter for histogram threshold
			prevHistogram = rows[1]
			currentHistogram = rows[0]

			# if histogram went from negative to positive
			if prevHistogram[0] != 0.0:
				if prevHistogram[0] <= 0 and currentHistogram[0] >= 0:
					emailBody = "%s\n%s - Histogram changed from negative to positive" % (emailBody, ticker)
				# if histogram went from positive to negative
				elif prevHistogram[0] >= 0 and currentHistogram[0] <= 0:
					emailBody = "%s\n%s - Histogram changed from positive to negative" % (emailBody, ticker)

			# close DB gracefully
			conn.close()

			# send the email summary
			print emailBody

'''
Function:
	inDB
Notes:
	validate if ticker being processed is already in DB
	we run an init-style function if ticker is new because we have no established data to work with
	otherwise, we run code that is relevant to pulling existing data from the DB
'''
def inDB(ticker):
	stockDB = 'stocks.db'
	conn = sqlite3.connect(stockDB)
	cursor = conn.cursor()

	cursor.execute('SELECT * FROM stocks WHERE ticker = ?', (ticker, ))

	length = len(cursor.fetchall())

	if length > 0:
		return True
	else:
		return False

'''
Function: 
	writeDB
Notes:
	only purpose of this function is to commit new records to the DB
'''
def writeDB(dateTime, ticker, closePrice, day12Avg, day26Avg, macd, signalAvg, histogram, rsi14day):
	stockDB = 'stocks.db'
	conn = sqlite3.connect(stockDB)

	# normalize data
	day12Avg = "{:.3f}".format(day12Avg)
	day26Avg = "{:.3f}".format(day26Avg)
	macd = "{:.3f}".format(macd)
	signalAvg = "{:.3f}".format(signalAvg)
	histogram = "{:.3f}".format(histogram)
	rsi14day = "{:.3f}".format(rsi14day)

	query = "INSERT INTO stocks(dateTime, ticker, closeprice, fastema, slowema, macd, signal, histogram, rsi14day) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
	conn.execute(query, (dateTime, ticker, closePrice, day12Avg, day26Avg, macd, signalAvg, histogram, rsi14day))
	
	# write and close DB
	conn.commit()
	conn.close()

'''
Function:
	main
'''
# set email address here
email = 'naushad.kasu@gmail.com'

# pull info for a well known ticker to establish date of pulled stock data
seedDate = Share('SPY')
currentTradeDate = seedDate.get_trade_datetime()[:10]
currentRunDate  = date.today().strftime('%Y-%m-%d')

# only run the script/code if the current date matches the current trade date from the above well known ticker (SPY).
# this allows us to ensure multiple runs of the script does not produce redundant data
if currentTradeDate == currentRunDate:
	with open("tickers.csv") as f:
		for line in f:
			ticker = line.rstrip('\n')
			calculate(ticker)
