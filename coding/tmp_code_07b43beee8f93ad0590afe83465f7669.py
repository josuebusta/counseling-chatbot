import yfinance as yf
import datetime

# Get the current date
current_date = datetime.date.today()

# Get the stock data for META and TESLA
meta_data = yf.Ticker("META")
tesla_data = yf.Ticker("TSLA")

# Get the stock price at the start of the year
meta_start_price = meta_data.history(start='2024-01-01')['Close'].iloc[0]
tesla_start_price = tesla_data.history(start='2024-01-01')['Close'].iloc[0]

# Get the current stock price
meta_current_price = meta_data.history(period='1d')['Close'].iloc[-1]
tesla_current_price = tesla_data.history(period='1d')['Close'].iloc[-1]

# Calculate the YTD gain
meta_ytd_gain = ((meta_current_price - meta_start_price) / meta_start_price) * 100
tesla_ytd_gain = ((tesla_current_price - tesla_start_price) / tesla_start_price) * 100

print("META YTD gain:", meta_ytd_gain, "%")
print("TESLA YTD gain:", tesla_ytd_gain, "%")