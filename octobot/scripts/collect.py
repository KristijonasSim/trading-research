"""Download Binance candles for OctoBot backtests (same pairs/dates as freqtrade)."""
import asyncio, sys, datetime as dt
import octobot_commons.symbols as symbols
import octobot_commons.enums as cenums
import octobot_trading.enums as tenums
import octobot_tentacles_manager.api as tm_api
import octobot_backtesting.api as bt_api
import octobot.logger  # noqa

GROUPS = {
    "btc_eth": ["BTC/USDT", "ETH/USDT"],
    "alts10": ["XRP/USDT", "BNB/USDT", "SOL/USDT", "DOGE/USDT", "ADA/USDT",
               "TRX/USDT", "LINK/USDT", "AVAX/USDT", "LTC/USDT", "DOT/USDT"],
}
START = int(dt.datetime(2021, 11, 8, tzinfo=dt.timezone.utc).timestamp() * 1000)
END = int(dt.datetime(2026, 11, 8, tzinfo=dt.timezone.utc).timestamp() * 1000)
TFS = [cenums.TimeFrames.ONE_HOUR, cenums.TimeFrames.FOUR_HOURS, cenums.TimeFrames.ONE_DAY]


async def main(group):
    import tentacles  # noqa  load tentacles
    setup = tm_api.get_tentacles_setup_config()
    c = bt_api.exchange_historical_data_collector_factory(
        "binance", tenums.ExchangeTypes.SPOT, setup,
        [symbols.parse_symbol(s) for s in GROUPS[group]],
        time_frames=TFS, start_timestamp=START, end_timestamp=END, config={})
    f = await bt_api.initialize_and_run_data_collector(c)
    print("FILE", group, f)

asyncio.run(main(sys.argv[1]))
