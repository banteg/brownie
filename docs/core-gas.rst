.. _core-accounts:

==============
Gas Strategies
==============

Gas strategies are objects that dynamically generate a gas price for a transaction. They can also be used to automatically replace pending transactions within the mempool.

Gas strategies come in three basic types:

* **Simple** strategies provide a gas price once, but do not replace pending transactions.
* **Block** strategies provide an initial price, and optionally replace pending transactions based on the number of blocks that have been mined since the first transaction was broadcast.
* **Time** strategies provide an initial price, and optionally replace pending transactions based on the amount of time that has passed since the first transaction was broadcast.

Using a Gas Strategy
====================

To use a gas strategy, first import it from ``brownie.network.gas.strategies``:

.. code-block:: python

    >>> from brownie.network.gas.strategies import GasNowStrategy
    >>> gas_strategy = GasNowStrategy("fast")

You can then provide the object in the ``gas_price`` field when making a transaction:

.. code-block:: python

    >>> accounts[0].transfer(accounts[1], "1 ether", gas_price=gas_strategy)

When the strategy replaces a pending transaction, the returned :func:`TransactionReceipt <brownie.network.transaction.TransactionReceipt>` object will be for the transaction that confirms.

During :ref:`non-blocking transactions <core-accounts-non-blocking>`, all pending transactions are available within the :func:`history <brownie.network.state.TxHistory>` object. As soon as one transaction confirms, the remaining dropped transactions are removed.

Setting a Default Gas Strategy
==============================

You can use :func:`network.gas_price <main.gas_price>` to set a gas strategy as the default for all transactions:

.. code-block:: python

    >>> from brownie.network import gas_price
    >>> gas_price(gas_strategy)

Available Gas Strategies
========================

.. py:class:: brownie.network.gas.strategies.GasNowStrategy(speed="fast")

    Simple gas strategy for determing a price using the `GasNow <https://www.gasnow.org/>`_ API.

    * ``speed``: The gas price to use based on the API call. Options are rapid, fast, standard and slow.

    .. code-block:: python

        >>> from brownie.network.gas.strategies import GasNowStrategy
        >>> gas_strategy = GasNowStrategy("fast")

        >>> accounts[0].transfer(accounts[1], "1 ether", gas_price=gas_strategy)

.. py:class:: brownie.network.gas.strategies.GasNowScalingStrategy(initial_speed="standard", max_speed="rapid", increment=1.125, block_duration=2)

    Block based scaling gas strategy using the GasNow API.

    * ``initial_speed``: The initial gas price to use when broadcasting the first transaction. Options are rapid, fast, standard and slow.
    * ``max_speed``: The maximum gas price to use when replacing the transaction. Options are rapid, fast, standard and slow.
    * ``increment``: A multiplier applied to the most recently used gas price in order to determine the new gas price. If the incremented value is less than or equal to the current ``max_speed`` rate, a new transaction is broadcasted. If the current rate for ``initial_speed`` is greater than the incremented rate, it is used instead.
    * ``block_duration``: The number of blocks to wait between broadcasting new transactions.

    .. code-block:: python

        >>> from brownie.network.gas.strategies import GasNowScalingStrategy
        >>> gas_strategy = GasNowScalingStrategy("fast", increment=1.2)

        >>> accounts[0].transfer(accounts[1], "1 ether", gas_price=gas_strategy)

Building your own Gas Strategy
==============================

To implement your own gas strategy you must subclass from one of the :ref:`gas strategy abstract base classes <api-network-gas-abc>`.
