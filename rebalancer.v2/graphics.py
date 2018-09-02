import matplotlib.pyplot as plt
import numpy as np


def plot_portfolio_backtest(time, rebal, no_rebal, trades, volumes):
    """
    Plots two subplots, 2,1,1 plots hodling and rebalancing portoflio over time, 2,1,2 plots
    percentage gains over hodling for rebalancing.

    Args:
        time (list): number of hours
        rebal (list): dollars
        no_rebal (list): %

    """
    trade = np.array(trades, dtype=np.float)
    volume = np.array(volumes, dtype=np.float)
    time_a = np.array(time, dtype=np.float)
    rebal_b = np.array(rebal, dtype=np.float)
    no_rebal_c = np.array(no_rebal, dtype=np.float)

    time_a = (time_a - time_a[0]) / (1000*60*60)
    plt.subplot(221)
    legend = ["Rebalancing", "Hodling"]
    series = [("Rebalanced", rebal_b),
              ("No_rebalance", no_rebal_c)]

    for series_name, series_values in series:
        plt.plot(time_a, series_values, label=series_name)
    plt.legend(legend)
    plt.ylabel("Portfolio Value $")
    plt.xlabel("Time")
    plt.title("Portfolio value $ over 41.67 days with a 3 coin portfolio.")

    plt.subplot(222)
    plt.plot(time_a, ((rebal_b - no_rebal_c) / no_rebal_c) * 100)
    plt.ylabel("Portfolio difference (%)")
    plt.xlabel("Time (hours)")
    plt.title("Percentage difference between rebalancing and hodling")

    plt.subplot(223)
    plt.plot(trade, volume)
    plt.ylabel('Cumulative Volume $')
    plt.xlabel('Cumulative trades')
    plt.title('Volume against Trades')
    plt.show()
