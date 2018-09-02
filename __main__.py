from rebalancer.testers import BackTester, LiveTester
from telethon import TelegramClient, sync

import yaml

tester_types = {
    "backtest": BackTester,
    "livetest": LiveTester
}

config_uri = "./rebalancer/config.yaml"

conf = yaml.load(open(config_uri, "r"))

client = TelegramClient('rebalancer', conf['api_id'], conf['api_hash']).start()

if conf["tester_type"] in tester_types:
    if conf["tester_type"] == "backtest":
        Tester = tester_types[conf["tester_type"]]
        tester1 = Tester(conf)

        tester1.rebalance_backtest()
        tester1.plot()

    elif conf["tester_type"] == "livetest":
        Tester = tester_types[conf["tester_type"]]  # insig time
        tester = Tester(conf)  # ~2.77489 seconds

        tester.client = client

        tester.start()
    else:
        pass
else:
    print("Tester type not implemented\nValid testers are: {}".format(", ".join(tester_types.keys())))
