from datetime import datetime, timedelta
from typing import Optional, Callable

from icetcore import TCoreAPI

from vnpy.trader.setting import SETTINGS
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest, TickData
from vnpy.trader.utility import ZoneInfo
from vnpy.trader.datafeed import BaseDatafeed


INTERVAL_VT2ICE: dict[Interval, tuple] = {
    Interval.MINUTE: (4, 1),
    Interval.HOUR: (4, 60),
    Interval.DAILY: (5, 1)
}

INTERVAL_ADJUSTMENT_MAP: dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta()
}

# 交易所映射
EXCHANGE_ICE2VT: dict[str, Exchange] = {
    "CFFEX": Exchange.CFFEX,
    "SHFE": Exchange.SHFE,
    "CZCE": Exchange.CZCE,
    "DCE": Exchange.DCE,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX,
    "SSE": Exchange.SSE,
    "SZSE": Exchange.SZSE,
}
EXCHANGE_VT2ICE: dict[Exchange, str] = {v: k for k, v in EXCHANGE_ICE2VT.items()}

CHINA_TZ = ZoneInfo("Asia/Shanghai")


class IceTCoreDatafeed(BaseDatafeed):
    """"""

    def __init__(self):
        """"""
        if "datafeed.apppath" not in SETTINGS.keys():
            SETTINGS["datafeed.apppath"] = "C:/AlgoMaster2/APPs64"
        self.username: str = SETTINGS["datafeed.apppath"]

        self.inited: bool = False

        self.api: "TCoreAPI" = None
        self.symbol_name_map: dict[str, str] = {}

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        if self.inited:
            return True

        self.api = TCoreAPI(apppath=self.username)
        self.api.connect()

        self.query_symbols()
        self.inited = True

        return True

    def query_symbols(self) -> None:
        """查询合约"""
        for exchange_str in EXCHANGE_ICE2VT.keys():
            symbols: list = self.api.getallsymbol(exchange=exchange_str)
            for symbol_str in symbols:

                if "/" in symbol_str or "HOT" in symbol_str or "_" in symbol_str:    # 没有过滤期货指数合约
                    continue

                symbol_id: str = self.api.getsymbol_id(symbol_str)
                self.symbol_name_map[symbol_id] = symbol_str

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[list[BarData]]:
        """查询K线数据"""
        if not self.inited:
            n: bool = self.init(output)
            if not n:
                return []

        name: str = self.symbol_name_map.get(req.symbol, None)
        if not name:
            output(f"查询K线数据失败：不支持的合约代码{req.vt_symbol}")
            return []

        interval, window = INTERVAL_VT2ICE.get(req.interval, ("", ""))
        if not interval:
            output(f"查询K线数据失败：不支持的时间周期{req.interval.value}")
            return []

        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[req.interval]

        quote_history: list = self.api.getquotehistory(
            interval,
            window,
            name,
            req.start.strftime("%Y%m%d%H"),
            req.end.strftime("%Y%m%d%H")
        )

        if not quote_history:
            self.output(f"获取{req.symbol}合约{req.start}-{req.end}历史数据失败")
            return []

        bars: list[BarData] = []
        for history in quote_history:
            dt: datetime = (history["DateTime"] - adjustment).replace(tzinfo=CHINA_TZ)
            if req.interval == Interval.DAILY:
                dt = dt.replace(hour=0, minute=0)

            bar: BarData = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                datetime=dt,
                open_price=history["Open"],
                high_price=history["High"],
                low_price=history["Low"],
                close_price=history["Close"],
                volume=history["Volume"],
                open_interest=history["OpenInterest"],
                gateway_name="ICETCORE"
            )
            bars.append(bar)

        return bars

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> Optional[list[TickData]]:
        """查询Tick数据"""
        return []
