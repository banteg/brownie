import threading
import time
from typing import Dict

import requests

from .bases import BlockGasStrategy, SimpleGasStrategy
from brownie import web3
from brownie.exceptions import RPCRequestError

_gasnow_update = 0
_gasnow_data: Dict[str, int] = {}
_gasnow_lock = threading.Lock()


def _fetch_gasnow(key: str) -> int:
    global _gasnow_update
    with _gasnow_lock:
        if time.time() - _gasnow_update > 15:
            data = None
            for i in range(12):
                response = requests.get(
                    "https://www.gasnow.org/api/v3/gas/price?utm_source=brownie"
                )
                if response.status_code != 200:
                    time.sleep(5)
                    continue
                data = response.json()["data"]
            if data is None:
                raise ValueError
            _gasnow_update = data.pop("timestamp") // 1000
            _gasnow_data.update(data)

    return _gasnow_data[key]


class GasNowStrategy(SimpleGasStrategy):
    """
    Gas strategy for determing a price using the GasNow API.

    GasNow returns 4 possible prices:

    rapid: the median gas prices for all transactions currently included
           in the mining block
    fast: the gas price transaction "N", the minimum priced tx currently
          included in the mining block
    standard: the gas price of the Max(2N, 500th) transaction in the mempool
    slow: the gas price of the max(5N, 1000th) transaction within the mempool

    Visit https://www.gasnow.org/ for more information on how GasNow
    calculates gas prices.
    """

    def __init__(self, speed: str = "fast"):
        if speed not in ("rapid", "fast", "standard", "slow"):
            raise ValueError("`speed` must be one of: rapid, fast, standard, slow")
        self.speed = speed

    def get_gas_price(self) -> int:
        return _fetch_gasnow(self.speed)


class GasNowScalingStrategy(BlockGasStrategy):
    """
    Block based scaling gas strategy using the GasNow API.

    The initial gas price is set according to `initial_speed`. The gas price
    for each subsequent transaction is increased by multiplying the previous gas
    price by `increment`, or increasing to the current `initial_speed` gas price,
    whichever is higher. No repricing occurs if the new gas price would exceed
    the current `max_speed` price as given by the API.
    """

    def __init__(
        self,
        initial_speed: str = "standard",
        max_speed: str = "rapid",
        increment: float = 1.125,
        block_duration: int = 2,
    ):
        super().__init__(block_duration)
        if initial_speed not in ("rapid", "fast", "standard", "slow"):
            raise ValueError("`initial_speed` must be one of: rapid, fast, standard, slow")
        self.initial_speed = initial_speed
        self.max_speed = max_speed
        self.increment = increment

    def update_gas_price(self, last_gas_price: int, elapsed_blocks: int) -> int:
        initial_gas_price = _fetch_gasnow(self.initial_speed)
        max_gas_price = _fetch_gasnow(self.max_speed)

        incremented_gas_price = int(last_gas_price * self.increment)
        new_gas_price = max(initial_gas_price, incremented_gas_price)
        return min(max_gas_price, new_gas_price)

    def get_gas_price(self) -> int:
        return _fetch_gasnow(self.initial_speed)


class GethMempoolStrategy(BlockGasStrategy):
    def __init__(self, position: int = 500, increment: float = 1.05, graphql_endpoint: str = None):
        self.position = position
        self.increment = increment
        self.graphql_endpoint = graphql_endpoint or f"{web3.provider.endpoint_uri}/graphql"

    def mempool_price(self) -> int:
        query = "{ pending { transactions { gasPrice }}}"
        response = requests.post(self.graphql_endpoint, json={"query": query})
        response.raise_for_status()
        if "error" in response.json():
            raise RPCRequestError("could not fetch mempool, run geth with `--graphql` flag")
        data = response.json()["data"]["pending"]["transactions"]
        prices = [int(x["gasPrice"], 16) for x in data]
        return sorted(prices, reverse=True)[: self.position][-1]

    def get_gas_price(self) -> int:
        last = 0
        height = web3.eth.blockNumber
        while True:
            elapsed_blocks = web3.eth.blockNumber - height
            yield max(self.mempool_price(), last * self.increment ** elapsed_blocks)
            height = web3.eth.blockNumber