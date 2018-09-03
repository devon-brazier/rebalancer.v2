from rebalancer.testers import BackTester, LiveTester
from telethon import TelegramClient, sync
import os
import yaml

tester_types = {
    "backtest": BackTester,
    "livetest": LiveTester
}

api_id = os.environ.get('api_id')
api_hash = os.environ.get('api_hash')

if None in [api_id, api_hash]:
    raise ValueError("Check environment variables")

config_uri = "./rebalancer/config.yaml"
conf = yaml.load(open(config_uri, "r"))


if conf['telegram_on']:
    client = TelegramClient('rebalancer', api_id, api_hash).start()
else:
    client = None

if conf["tester_type"] in tester_types:
    if conf["tester_type"] == "backtest":
        Tester = tester_types[conf["tester_type"]]
        tester1 = Tester(conf)

        tester1.rebalance_backtest()
        tester1.plot()

    elif conf["tester_type"] == "livetest":
        Tester = tester_types[conf["tester_type"]]  # insig time
        tester = Tester(conf)  # ~2.77489 seconds

        if conf['telegram_on']:
            tester.client = client

        tester.start()
    else:
        pass
else:
    print("Tester type not implemented\nValid testers are: {}".format(", ".join(tester_types.keys())))
