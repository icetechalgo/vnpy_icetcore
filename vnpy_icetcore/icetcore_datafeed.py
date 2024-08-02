from datetime import datetime, timedelta
from typing import Dict, List,  Optional, Callable

from numpy import ndarray
from icetcore import TCoreAPI

from vnpy.trader.setting import SETTINGS
from vnpy.trader.constant import Exchange, Interval,Product
from vnpy.trader.object import BarData, TickData, HistoryRequest,ContractData
from vnpy.trader.utility import ZoneInfo
from vnpy.trader.datafeed import BaseDatafeed

from .icetcore_gateway import symbol_contract_map,EXCHANGE_VT2ICE,EXCHANGE_ICE2VT

INTERVAL_VT2ICE: Dict[Interval, int] = {
    Interval.TICK: 2,
    Interval.MINUTE: 4,
    Interval.DAILY: 5,
}

INTERVAL_ADJUSTMENT_MAP: Dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.TICK: timedelta(),
    Interval.DAILY: timedelta()         # no need to adjust for daily bar
}



CHINA_TZ = ZoneInfo("Asia/Shanghai")

class IceTCoreDatafeed(BaseDatafeed):
    exchanges: List[str] = list(EXCHANGE_ICE2VT.values())

    def __init__(self):
        """"""
        if "datafeed.apppath" not in SETTINGS.keys():
            SETTINGS["datafeed.apppath"]="C:/AlgoMaster2/APPs64"
        self.username: str = SETTINGS["datafeed.apppath"]
        self.api: "TCoreAPI" =None
        self.inited: bool = False
        self.symbols: ndarray = None

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        if self.inited:
            return True
        self.api=TCoreAPI(apppath=self.username)
        self.api.connect()
        self.inited = True
        return True


    def write_error(self, msg: str, error: dict) -> None:
        """输出错误信息日志"""
        error_id: int = error["ErrorID"]
        error_msg: str = error["ErrorMsg"]
        msg: str = f"{msg}，代码：{error_id}，信息：{error_msg}"
        self.write_log(msg)

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[BarData]]:
        if not self.inited:
            n: bool = self.init(output)
            if not n:
                return []

        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        interval: Interval = req.interval
        start: datetime = req.start
        end: datetime = req.end
        # start: str = req.start.strftime('%Y%m%d%H')
        # end: str = req.end.strftime('%Y%m%d%H')

        contract: ContractData = symbol_contract_map.get(EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol, None)
        # 检查查询的代码在范围内
        if not contract:
            output(f"查询K线数据失败：不支持的合约代码{req.vt_symbol}")
            return []

        rq_interval: int = INTERVAL_VT2ICE.get(interval)
        if not rq_interval:
            output(f"查询K线数据失败：不支持的时间周期{req.interval.value}")
            return []
        #print(symbol,"  ",exchange,"  ",interval,"  ",start,"  ",end,"  ",contract.name)
        symbolhead="TC.S."
        if contract.product==Product.FUTURES:
            symbolhead="TC.F."
        elif contract.product==Product.OPTION:
            symbolhead="TC.O." 

        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[interval]

        # 只对衍生品合约才查询持仓量数据
        fields: list = ["open", "high", "low", "close", "volume"]
        if symbolhead=="TC.F." or symbolhead=="TC.O.":
            fields.append("open_interest")

        stime=start.date()
        df=[]
        if rq_interval<5:
            while(True):
                if stime<end.date()+timedelta(days=1):
                    his=self.api.getquotehistory(rq_interval,1,symbolhead+contract.name,stime.strftime('%Y%m%d')+"01",(stime+timedelta(days=1)).strftime('%Y%m%d')+"08")
                    if his:
                        df=df+his
                    stime=stime+timedelta(days=1)
                else:
                    break
        else:
            df=self.api.getquotehistory(rq_interval,1,symbolhead+contract.name,stime.strftime('%Y%m%d')+"01",(end+timedelta(days=2)).date().strftime('%Y%m%d')+"08")
        data: List[BarData] = []
        if df:
            for row in df:
                dt: datetime = (row["DateTime"]- adjustment).replace(tzinfo=CHINA_TZ)
                bar: BarData = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=row["Open"],
                    high_price=row["High"],
                    low_price=row["Low"],
                    close_price=row["Close"],
                    volume=row["Volume"],
                    open_interest=row["OpenInterest"],
                    gateway_name="ICETCore"
                )
                data.append(bar)
        return data

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[TickData]]:
        """查询Tick数据"""
        if not self.inited:
            n: bool = self.init(output)
            if not n:
                return []

        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        interval: Interval = req.interval
        start: datetime = req.start
        end: datetime = req.end
        # start: str = req.start.strftime('%Y%m%d%H')
        # end: str = req.end.strftime('%Y%m%d%H')

        contract: ContractData = symbol_contract_map.get(EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol, None)
        # 检查查询的代码在范围内
        if not contract:
            output(f"查询K线数据失败：不支持的合约代码{req.vt_symbol}")
            return []

        rq_interval: int = INTERVAL_VT2ICE.get(interval)
        if not rq_interval:
            output(f"查询K线数据失败：不支持的时间周期{req.interval.value}")
            return []
        #print(symbol,"  ",exchange,"  ",interval,"  ",start,"  ",end,"  ",contract.name)
        symbolhead="TC.S."
        if contract.product==Product.FUTURES:
            symbolhead="TC.F."
        elif contract.product==Product.OPTION:
            symbolhead="TC.O." 

        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[interval]

        # 只对衍生品合约才查询持仓量数据

        fields: list = [
            "open",
            "high",
            "low",
            "last",
            "volume",
            "b1",
            "a1",
            "b1_v",
            "a1_v"]
        if symbolhead=="TC.F." or symbolhead=="TC.O.":
            fields.append("open_interest")

        stime=start.date()
        df=[]
        while(True):
            if stime<end.date():
                print()
                his=self.api.getquotehistory(rq_interval,1,symbolhead+contract.name,stime.strftime('%Y%m%d')+"10",(stime+timedelta(days=1)).strftime('%Y%m%d')+"10")
                if his:
                    df=df+his
                stime=stime+timedelta(days=1)
            else:
                break
        #df=self.api.getquotehistory(rq_interval,1,symbolhead+contract.name,start,end)
        data: List[TickData] = []
        if df:
            for row in df:
                dt: datetime = row["DateTime"].replace(tzinfo=CHINA_TZ)

                tick: TickData = TickData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt,
                    open_price=row["Last"],
                    high_price=row["Last"],
                    low_price=row["Last"],
                    last_price=row["Last"],
                    volume=row["Quantity"],
                    open_interest=row["OpenInterest"],
                    bid_price_1=row["Bid"],
                    ask_price_1=row["Ask"],
                    bid_volume_1=row["OpenInterest"],
                    ask_volume_1=row["OpenInterest"],

                    gateway_name="ICETCore"
                )

                data.append(tick)

        return data
