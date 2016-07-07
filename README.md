# ticker
RSI and histogram alerting based on stock ticker symbol

<b>What is ticker?</b><br>
A python script that loops through ticker symbols and generates RSI (14 day average) and histogram (MACD-based metrics)
and emails a summary of thresholds met to an email address.

<b>How do I use ticker?</b><br>
These are basic instructions, ping me on Reddit (/u/roundqube) if you need further instructions specific to your situation...<br><br>

Pre-requisite:<br>
1. Ability to run Python on your system<br>
2. Ability to schedule jobs (cron, etc...)<br>
3. Ability to email through local system (sendmail, etc...)<br>
4. Python yahoo-finance library<br><br>

Configuration:<br>
1. Update the first line to point to your Python path i.e. on my system it is: #!/opt/local/bin/python<br>
2. Update the <b>user</b>, <b>pwd</b> and <b>recipient</b> variables within the generateNotification function.  This should be your Gmail details so the email can be proxied through the Google servers to your inbox.
3. Store both files in same directory, <i><b>stocks.py</b></i> and <i><b>stocks.db</b></i> (DB is provided for you with schema defined)<br>
4. Add all of the tickers you wish to track to the <i><b>tickers.csv</b></i> file<br>
5. Add tickers you wish to alert on to the <i><b>alert_tickers.csv</b></i> file.  The threshold for RSI is below 30 or above 70.  
The threshold for histogram is when it goes from positive to negative or negative to positive i.e. the MACD and signal line converge<br>
6. Schedule the script to run daily (sometime before midnight).  The script can be run daily even through weekends and holidays because it
uses some logic to determine that data is redudant and will skip the dataset based on date changes.
