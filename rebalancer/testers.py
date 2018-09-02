import csv
import time
import sched
import os
import datetime
import rebalancer.binance_api as api
import pandas as pd

from rebalancer.graphics import plot_portfolio_backtest as plt


class Tester(object):
    """
    This object processes the information needed for a rebalance. Information is collected using the binance_api
    module.

    All common information needed for the two different testers are initialised within the Binance superclass.
    """
    def __init__(self, config):
        """
        Remember to set your environment variables for API_KEY and SERCET_KEY. Use os.environ["API_KEY"] = ... and
        os.environ["SECRT_KEY"] = ... to set environment variables, input must be a string.

        Sets the api and secret for the binance account. Initialises required information for backtester and
        livetester. If no key, secret is supplied an error will raise.

        Args:
            config (dict): configuration dictionary from config.yaml

        :transaction_fee (float): percentage fee for binance from config.yaml
        :min_btc_order (float): as stated
        :maxOrdertime (int): maximum amount of time an open order can exist before cancellation
        :portfolio_lot_sizes (dict): minimum pair orders in buy coin, from exchange info
        :current_time (float): used for cancelling open orders.

        :open_orders (dict): saved to open_orders.csv

        :key (str): api_key needed for signedRequest, found in environment variables
        :secret (str): secret_key needed for signedRequest, found in environment variables
        """

        self.data = self.portfolio_csv()

        self.all_balances = {}
        self.all_prices = {}

        self.exchange_info = api.get_exchange_info()
        self.transaction_fee = config["transaction_fee"]
        self.min_btc_order = config["minimum_btc_order"]
        self.maxOrdertime = config["open_order_time_limit"]
        self.candle_time = config["candle_time"]
        self.get_portfolio_lot_sizes()
        self.current_time = 0

        self.open_orders = []
        self.timestamps = []

        self.portfolio_klines = []

        self.number_of_trades = 0
        self.volume_of_trades = 0

        key = os.environ.get("API_KEY")
        secret = os.environ.get("SECRET_KEY")

        if None in [key, secret]:
            raise ValueError("Check environment variables")

        api.set(key, secret)

        self.portfolio_total = 0
        self.hodl_total = 0

    def update(self):
        """
        Used for live tester only.
        Takes prices and balances on exchange, calculates required info, puts into one dataframe.
        """
        print("Fetching balances:")
        self.all_balances = api.balances()

        print("Fetching prices: ")
        self.all_prices = api.prices()

        self.data['binance_balances'] = pd.Series({symbols: float(self.all_balances[coin]["free"])
                                                   for symbols, coin in zip(self.data.index, self.data['coin_name'])})

        self.data['portfolio_balances'] = pd.Series({symbols: self.data.loc[symbols, 'binance_balances']
                                                     - float(self.data.loc[symbols, 'protected_balance'])
                                                     for symbols in self.data.index})

        # Filters all_prices to portfolio prices
        self.data['portfolio_prices'] = pd.Series({symbols: float(self.all_prices[symbols]) for symbols in self.data.index})

        # Converts all prices to USD value
        self.get_portfolio_prices_usd()

        # Calculate amount of each coin held in terms of USD
        self.data['total_usd'] = pd.Series({symbols: self.data['portfolio_balances'][symbols] *
                                            self.data['portfolio_prices_usd'][symbols] for symbols in self.data.index})
        self.data['total_usd_hodl'] = pd.Series({symbols: self.data['hodl_balances'][symbols] *
                                                 self.data['portfolio_prices_usd'][symbols] for symbols in self.data.index})

        # Calculates the total value of the portfolio
        self.portfolio_total = sum(self.data['total_usd'])
        self.hodl_total = sum(self.data['total_usd_hodl'])

        # Calculates the percentages of each coin in portfolio in USD
        self.data['percentages'] = pd.Series({symbols: self.data['portfolio_prices_usd'][symbols] *
                                              self.data['portfolio_balances'][symbols] / self.portfolio_total
                                              for symbols in self.data.index})

        # Calculate percentage differences from target percentages for each coin
        self.data['percentage_diffs'] = pd.Series({symbols: float(self.data['target'][symbols]) -
                                                   self.data['percentages'][symbols]
                                                   for symbols in self.data.index})

        # Calculate required purchase volume for each coin
        self.data['purchase_volumes'] = pd.Series({symbols: self.data['percentage_diffs'][symbols] *
                                                   self.portfolio_total /
                                                   self.data['portfolio_prices_usd'][symbols]
                                                   for symbols in self.data.index})

        # Calculate USD value of purchase volume
        self.data['trade_volumes'] = pd.Series({symbols: self.data['purchase_volumes'][symbols] * self.data['portfolio_prices_usd'][symbols]
                                                for symbols in self.data.index})

        self.buy_or_sell()

    def get_portfolio_prices_usd(self):
        """Calculates the dollar value of each coin, the currency the portfolio is matched against"""
        usd_values = {}

        for symbol in self.data.index:
            if symbol != "BTCUSDT":
                usd_values[symbol] = self.data['portfolio_prices'][symbol] \
                                     * self.data['portfolio_prices']["BTCUSDT"]
            else:
                usd_values[symbol] = self.data['portfolio_prices'][symbol]
        self.data['portfolio_prices_usd'] = pd.Series(usd_values)

    def buy_or_sell(self):
        """Determines whether the coin needs to be bought or sold"""
        if_buy = {}
        for symbols in self.data.index:
            if self.data['trade_volumes'][symbols] >= self.min_btc_order * self.data['portfolio_prices_usd']["BTCUSDT"]:
                if_buy[symbols] = True
            elif self.data['trade_volumes'][symbols] <= -self.min_btc_order * \
                    self.data['portfolio_prices_usd']["BTCUSDT"]:
                if_buy[symbols] = False
            else:
                if_buy[symbols] = None
        self.data['if_buy'] = pd.Series(if_buy)

    def get_portfolio_lot_sizes(self):
        """Extracts useful information of LOT_SIZE from exchange_info for portfolio coins only"""
        lot_size_dict = {}
        for symbols in self.exchange_info["symbols"]:
            for filters in symbols["filters"]:
                if filters["filterType"] == "LOT_SIZE":
                    lot_size_dict[symbols["symbol"]] = {"maxQty": filters["maxQty"],
                                                        "minQty": filters["minQty"],
                                                        "stepSize": filters["stepSize"]}
        self.data['portfolio_lot_sizes'] = pd.Series({symbols:
                                                      lot_size_dict[symbols]['minQty'] for symbols in self.data.index})

    def portfolio_csv(self):
        """Gets list of relevant tradings symbols for rebalancing algorithm form portfolio.csv"""
        reader = pd.read_csv("./rebalancer/portfolio.csv", index_col=1)
        if len(reader) < 2:
            raise ValueError("The number of coins/tokens in portfolio must be greater than 1.")
        return reader

    def get_portfolio_klines(self):
        """Uses get_previous_closes() to make a single dict for backtest price information"""
        self.portfolio_klines = [api.klines(symbols, interval=self.candle_time, limit=1000) for symbols in self.data.index]

        format_portfolio_klines = pd.DataFrame()

        for names, info in zip(self.data.index, self.portfolio_klines):
            format_portfolio_klines[names] = pd.Series({close['closeTime']: close['close'] for close in info})
        return format_portfolio_klines


class LiveTester(Tester):
    def __init__(self, config_uri):
        super().__init__(config_uri)

        self.init_time = datetime.datetime.now()

        self.config = config_uri
        self.tick_duration = self.config["tick_duration"]
        self.rebalance_duration = self.tick_duration * self.config["rebalance_ticks"]
        self.open_order_check_duration = self.tick_duration * self.config["open_order_check_ticks"]
        self.telegram_time_per_message = self.tick_duration * self.config['telegram_ticks']
        self.is_test = self.config["livetest_test"]
        self.no_rebalances = 0

        self.all_open_orders = []

        self.data['hodl_balances'] = self.data['protected_balance']
        self.trunk_quantity()

        self.time_binance = []
        self.rebalance = []
        self.hodl = []

        self.update()
        self.data['hodl_balances'] = self.data['portfolio_balances']
        self.data['total_usd_hodl'] = pd.Series({symbols: self.data['hodl_balances'][symbols] *
                                                 self.data['portfolio_prices_usd'][symbols] for symbols in
                                                 self.data.index})
        self.hodl_total = sum(self.data['total_usd_hodl'])

        self.username = self.config['username']
        self.client = ''

        self.s = sched.scheduler(time.time, time.sleep)

    def trunk_quantity(self):
        for k, v in self.data['portfolio_lot_sizes'].items():
            num = v.find("1")
            if num == 0:
                self.data.loc[k, 'portfolio_lot_sizes'] = int(float(v))
            elif num > 1:
                num -= 1
                format_string = ("%.{}f".format(num))
                self.data.loc[k, 'portfolio_lot_sizes'] = float(format_string % float(v))

    def execute_buy_or_sell(self, symbol):
        if self.data.loc[symbol, "if_buy"] is None:
            pass
        elif self.data.loc[symbol, 'if_buy'] is True:
            print("Posting BUY order: ")
            infos = api.order(symbol, api.BUY, self.data.loc[symbol, 'purchase_volume'],
                              '{0:.8f}'.format(self.data.loc[symbol, "portfolio_prices"]), test=self.is_test)
            print("Order placed to BUY {0} {1} for {2} BTC per unit.".format(self.data.loc[symbol, "purchase_volumes"],
                                                                             symbol[:3],
                                                                             '{0:.8f}'.format(self.data.loc[symbol, "portfolio_prices"])))

            print(infos)
            print()
        elif self.data.loc[symbol, "if_buy"] is False:
            print("Posting {0} order: ".format(self.data.loc[symbol, "if_buy"]))
            infos = api.order(symbol, api.SELL, -1 * self.data.loc[symbol, "purchase_volume"],
                              '{0:.8f}'.format(self.data.loc[symbol, "portfolio_prices"]), test=self.is_test)
            print("Order placed to SELL {0} {1} for {2} BTC per unit.".format((-1 * self.data.loc[symbol, "purchase_volumes"]),
                                                                              symbol[0][:3],
                                                                              '{0:.8f}'.format(self.data.loc[symbol, "portfolio_prices"])))
            print(infos)
            print()
        self.volume_of_trades += abs(self.data.loc[symbol, 'trade_volumes'])
        self.number_of_trades += 1

    def get_all_open_orders(self):
        self.all_open_orders = []

        for symbols in self.data.index:
            if symbols != "BTCUSDT":
                print("Fetching open orders for {0}: ".format(symbols))
                orders = api.openOrders(symbols)
                if orders is not None:
                    for elems in orders:
                        self.all_open_orders.append({"orderId": elems["orderId"],
                                                     "origQty": elems["origQty"],
                                                     "price": elems["price"],
                                                     "side": elems["side"],
                                                     "symbol": elems["symbol"],
                                                     "time": elems["time"]})
        self.all_open_orders.sort(key=lambda x: x["time"])

    def check_cancel(self):
        for elems in self.all_open_orders:
            if (time.time() * 1000) - elems["time"] >= self.maxOrdertime:
                print("Cancelling {0} order: ".format(elems["side"]))
                api.cancel(elems["symbol"], orderId=elems["orderId"])
                print("Order CANCELLED for {0}ing of {1} {2} at {3} BTC per unit. \n".format(elems["side"],
                                                                                             elems["origQty"],
                                                                                             elems["symbol"][:3],
                                                                                             elems["price"]))
                self.all_open_orders.remove(elems)

    def write_open_orders(self):
        with open("./rebalancer/open_orders.csv", 'r') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames

        with open("./rebalancer/open_orders.csv", 'w') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for rows in self.all_open_orders:
                writer.writerow(rows)

    def open_orders_handling(self):
        start_time = time.time()

        self.get_all_open_orders()
        self.check_cancel()
        self.write_open_orders()
        elapsed_time = time.time() - start_time
        print("Open orders checked & printed to open_orders.csv in {0} seconds.\n".format(elapsed_time))

    def make_info_and_execute(self):
        start_time = time.time()

        self.update()
        self.data.sort_values(by='percentage_diffs', ascending=False, inplace=True)
        self.trunk_quantity()
        for symbols in self.data.index:
            self.execute_buy_or_sell(symbols)

        elapsed_time = time.time() - start_time
        print("Orders found and executed, in {0} seconds.\n".format(elapsed_time))

    def portfolio_tracker(self):
        self.time_binance.append(time.time() * 1000)
        self.rebalance.append(self.portfolio_total)
        self.hodl.append(self.hodl_total)
        self.no_rebalances += 1

        print("Rebalance tracking saved.")
        print("Number of rebalances since run start: {0}.\n".format(self.no_rebalances))

    def sched_builder_rebalance(self, sc):
        self.make_info_and_execute()
        self.portfolio_tracker()
        self.s.enter(self.rebalance_duration, 1, self.sched_builder_rebalance, (sc,))

    def sched_builder_open(self, sc):
        self.current_time = time.time() * 1000
        self.open_orders_handling()
        self.s.enter(self.open_order_check_duration, 1, self.sched_builder_open, (sc,))

    def sched_builder_telegram(self, sc):
        self.data['Balance Portfolio'] = self.data['portfolio_balances'] - self.data['hodl_balances']
        self.client.send_message(self.username,
                                 'REBALANCING BOT INFO\n' + str(datetime.date.today()) +
                                 '\n\nTotal run time: ' + str(datetime.datetime.now() - self.init_time) +
                                 '\n\nTrades today: ' + str(self.number_of_trades) +
                                 '\nVolumes of trades today: ' + str(self.volume_of_trades)
                                 + '\n\nDifference in balances since start time: \n\n' +
                                 pd.DataFrame(self.data['Balance Portfolio'].values, index=self.data['coin_name'],
                                              columns=['Profit'], ).to_string(col_space=15)
                                 + '\n\nProfit against HODLing: $' + str(self.portfolio_total - self.hodl_total) +
                                 '\nProfit against HODLing: ' + str((self.portfolio_total / self.hodl_total) - 1)
                                 + '%')
        self.number_of_trades = 0
        self.volume_of_trades = 0
        self.s.enter(self.telegram_time_per_message, 1, self.sched_builder_telegram, (sc,))

    def start(self):
        self.s.enter(self.rebalance_duration, 1, self.sched_builder_rebalance, (self.s,))
        self.s.enter(self.telegram_time_per_message, 2, self.sched_builder_telegram, (self.s,))
        self.s.enter(self.open_order_check_duration, 3, self.sched_builder_open, (self.s,))
        self.s.run()


class BackTester(Tester):
    def __init__(self, config_uri):
        super().__init__(config_uri)

        self.volumes = []
        self.trades = []

        self.data['portfolio_balances'] = pd.Series({"BTCUSDT": 0, "QSPBTC": 0, "XLMBTC": 0,
                                                     "NEOBTC": 0, "MODBTC": 0, "ETHBTC": 0.1,
                                                     "MTLBTC": 0, "XRPBTC": 0, "OMGBTC": 10000,
                                                     "LTCBTC": 0})
        self.data['hodl_balances'] = self.data['portfolio_balances']

        self.all_prices = api.prices()
        self.data['portfolio_prices'] = pd.Series({symbols: float(self.all_prices[symbols]) for symbols in self.data.index})
        self.update()
        self.update_portfolio_balances()
        self.data['hodl_balances'] = self.data['portfolio_balances']

        self.previous_klines = self.get_portfolio_klines()
        self.timestamps = list(self.previous_klines.index)

        self.hodl = []
        self.rebalance = []

    def update_portfolio_balances(self):
        self.data.sort_values(by=['percentage_diffs'], ascending=False, inplace=True)
        for symbols in self.data.index:
            if (self.data.loc[symbols, "if_buy"] or not self.data.loc[symbols, "if_buy"]) and symbols != "BTCUSDT":
                self.volume_of_trades += abs(self.data.loc[symbols, 'trade_volumes'])
                self.volumes.append(self.volume_of_trades)
                # self.number_of_trades += 1
                # self.trades.append(self.number_of_trades)
                self.number_of_trades = self.portfolio_total / self.hodl_total - 1
                self.trades.append(self.number_of_trades)
                self.data.loc[symbols, 'portfolio_balances'] += self.data.loc[symbols, "purchase_volumes"] * (1 - self.transaction_fee)
                self.data.loc['BTCUSDT', 'portfolio_balances'] -= \
                    self.data.loc[symbols, "trade_volumes"] / self.data.loc['BTCUSDT', 'portfolio_prices_usd']

    def update(self):
        """
        Used for backtester only.
        Takes prices form kline data and balances from previous dict, calculates required info,
        overwrites previous dict
        """
        # Convert BTC values to USD values
        self.get_portfolio_prices_usd()
        # Calculate amount of each coin held in terms of USD
        self.data['total_usd'] = pd.Series({symbols: self.data['portfolio_balances'][symbols] *
                                            self.data['portfolio_prices_usd'][symbols] for symbols in self.data.index})
        self.data['total_usd_hodl'] = pd.Series({symbols: self.data['hodl_balances'][symbols] *
                                            self.data['portfolio_prices_usd'][symbols] for symbols in self.data.index})

        # Calculates the total value of the portfolio
        self.portfolio_total = sum(self.data['total_usd'])
        self.hodl_total = sum(self.data['total_usd_hodl'])

        # Calculates the percentages of each coin in portfolio in USD
        self.data['percentages'] = pd.Series({symbols: self.data['portfolio_prices_usd'][symbols] *
                                              self.data['portfolio_balances'][symbols] / self.portfolio_total
                                              for symbols in self.data.index})

        # Calculate percentage differences from target percentages for each coin
        self.data['percentage_diffs'] = pd.Series({symbols: float(self.data['target'][symbols]) -
                                                   self.data['percentages'][symbols]
                                                   for symbols in self.data.index})

        # Calculate required purchase volume for each coin
        self.data['purchase_volumes'] = pd.Series({symbols: self.data['percentage_diffs'][symbols] *
                                                            self.portfolio_total /
                                                            self.data['portfolio_prices_usd'][symbols]
                                                   for symbols in self.data.index})

        # Calculate USD value of purchase volume
        self.data['trade_volumes'] = pd.Series({symbols: self.data['purchase_volumes'][symbols] *
                                                         self.data['portfolio_prices_usd'][symbols]
                                                for symbols in self.data.index})

        self.buy_or_sell()

    def rebalance_backtest(self):
        for ticks in self.previous_klines.index:
            self.current_time = ticks

            self.data['portfolio_prices'] = pd.Series({symbols: float(self.previous_klines.loc[ticks, symbols])
                                                       for symbols in self.data.index})

            self.update()
            self.update_portfolio_balances()
            self.update()
            self.rebalance.append(self.portfolio_total)
            self.hodl.append(self.hodl_total)

    def plot(self):
        plt(self.timestamps, self.rebalance, self.hodl, self.volumes, self.trades)
