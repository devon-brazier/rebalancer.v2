Rebalancer.v2
=============

What is this?
-------------

A simple and conservative trading idea applied to a cryptocurrecy portfolio, producing a
consistent and linear percentage profit against no trading (HODLing). Currently supports
Binance (https://www.binance.com/) a popular cryptocurrency exchange and Telegram updates
set to daily. The bot is able to trade any number of BTC pairs and for the exclusion of 
specified assets on the exchange. For example, if you had 1 BTC on the exchange you could
protect 0.5 BTC of that from the bot and it would not be considered in rebalancing. Trades
that do not fill in the user configured time (default: 10 minutes) are auomatically
cancelled. All operation of the bot can be configured from **portfolio.csv** and 
**config.yaml**.

Explained
---------

A portfolio is defined by a series of coins/tokens and their target percentage of the
portoflio in USD. Every hour (user configurable) exchange data is taken and live
percentages are calculated, followed by trades to reacquire target percentages for 
each coin which may have changed due to price action. Simple, right?

Why?
----

Rebalancing from a trading perspective is essentially a profit taker for short term
bullish action and in **all** backtests proves to be profitable against no trading
(HODLing).

This is a strong, consistent and low-risk methid for profit compared to many forms of
technical analysis due to fundamental information regarding a trading pairs price action
against the overall market, i.e. target percentages.

Future Ideas
------------

1. Implement etherscan.io API to include cold stored cryptocurrencies in rebalancing. Whilst
cold stored coins/tokens cannot be readily traded, so long as enough of each asset is
contained on exchange this remains possible.
2. Live plotting of rebalance vs hodling sent to Telegram with daily updates.

Configuring the bot
-------------------

Remember you need to set your *API_KEY*, *API_SECRET*, *api_id* and *api_hash* into environment 
variables. Keep these very secure and **do not share them with anyone**.

**Config.yaml** contains all the information about the timing and type of rebalance for the bot.
Important settings are, *tester_type*, *livetest_test*, *telegram_on* and *username*. If you
want to run a live run on an exchange set *livetest_test* to **False**, this will tell Binance
that order requests *are not* test orders.
