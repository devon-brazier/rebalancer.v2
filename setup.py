from setuptools import setup

setup(
    name='rebalancer',
    version='1.4',
    py_modules=['binance_api', 'testers', 'graphics'],

    # metadata
    author='Devon Brazier',
    url='https://github.com/yenille/rebalancer',
    description='Binance rebalance trading bot',
    install_requires=['eventlet', 'requests', 'pandas', 'telegram']
)