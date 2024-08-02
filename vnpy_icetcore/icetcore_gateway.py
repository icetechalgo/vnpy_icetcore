import sys
from datetime import datetime
from time import sleep
from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta


from vnpy.trader.setting import SETTINGS
from vnpy.trader.utility import ZoneInfo, ZoneInfo
from vnpy.event import EventEngine
from vnpy.trader.constant import (
    Direction,
    Offset,
    Exchange,
    OrderType,
    Product,
    Status,
    OptionType
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    PositionData,
    AccountData,
    ContractData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest
)

from vnpy.trader.datafeed import BaseDatafeed
from icetcore import (TCoreAPI,
                    QuoteEvent,
                    TradeEvent,
                    OrderStruct)


# 委托状态映射



Status.FROZEN="锁券成功"
STATUS_ICE2VT: Dict[int, Status] = {
    0: Status.NOTTRADED,
    1: Status.NOTTRADED,
    2: Status.NOTTRADED,
    3: Status.ALLTRADED,
    4: Status.PARTTRADED,
    5: Status.PARTTRADED,
    6: Status.NOTTRADED,
    7: Status.PARTTRADED,
    8: Status.CANCELLED,
    9: Status.NOTTRADED,
    10: Status.REJECTED,
    11: Status.SUBMITTING,
    12: Status.SUBMITTING,
    13: Status.NOTTRADED,
    14: Status.SUBMITTING,
    15: Status.SUBMITTING,
    16: Status.SUBMITTING,
    17: Status.FROZEN,
    18: Status.REJECTED,
    19: Status.SUBMITTING,
    20: Status.SUBMITTING,
    21: Status.REJECTED,
    22: Status.SUBMITTING,
    23: Status.SUBMITTING,
    24: Status.SUBMITTING,
    31: Status.SUBMITTING
}

# 多空方向映射
DIRECTION_VT2ICE: Dict[Direction, int] = {
    Direction.LONG: 1,
    Direction.SHORT:2
}
DIRECTION_ICE2VT: Dict[int, Direction] = {v: k for k, v in DIRECTION_VT2ICE.items()}
# DIRECTION_ICE2VT[1] = Direction.LONG
# DIRECTION_ICE2VT[2] = Direction.SHORT

# 委托类型映射
OrderType.STOPLIMIT="停损限价"
ORDERTYPE_VT2ICE: Dict[OrderType, tuple] = {
    OrderType.LIMIT: (2, 1),
    OrderType.MARKET: (1, 2),
    OrderType.FAK: (2, 2),
    OrderType.FOK: (2, 3),
    OrderType.STOP: (3, 2),
    OrderType.STOPLIMIT: (4, 1)
}
ORDERTYPE_ICE2VT: Dict[Tuple, OrderType] = {#{v: k for k, v in ORDERTYPE_VT2ICE.items()}
    (1, 2): OrderType.MARKET ,
    (1, 1): OrderType.MARKET ,
    (2, 1): OrderType.LIMIT,
    (2, 2): OrderType.FAK,
    (2, 3): OrderType.FOK,
    (22, 2): OrderType.FAK,
    (3, 1): OrderType.STOP,
    (3, 2): OrderType.STOP,
    (5, 2): OrderType.STOP,
    (5, 1): OrderType.STOP,
    (6, 1): OrderType.STOPLIMIT,
    (6, 2): OrderType.STOPLIMIT,
    (4, 2): OrderType.STOPLIMIT,
    (4, 1): OrderType.STOPLIMIT
}
# 开平方向映射
Offset.COVEREDCALLWRITING="备兑开仓"
Offset.COVEREDCALLCLOSE="备兑平仓"
OFFSET_VT2ICE: Dict[Offset, int] = {
    Offset.OPEN: 0,
    Offset.CLOSE: 1,
    Offset.CLOSETODAY: 2,
    Offset.CLOSEYESTERDAY: 3,
    Offset.NONE: 4,
    Offset.COVEREDCALLWRITING:10,
    Offset.COVEREDCALLCLOSE:11
}
OFFSET_ICE2VT: Dict[int, Offset] = {v: k for k, v in OFFSET_VT2ICE.items()}

# 交易所映射
EXCHANGE_ICE2VT: Dict[str, Exchange] = {
    "CFFEX": Exchange.CFFEX,
    "SHFE": Exchange.SHFE,
    "CZCE": Exchange.CZCE,
    "DCE": Exchange.DCE,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX,
    "SSE":Exchange.SSE,
    "SZSE":Exchange.SZSE,
    "CME":Exchange.CME,
    "CBOT":Exchange.CBOT,
    "EUREX":Exchange.EUNX,
    "ENXT_PAR":Exchange.EUNX,
    "LIFFE":Exchange.NYSE,
    "LME":Exchange.LME,
    "ICE":Exchange.ICE,
    "NYBOT":Exchange.NYMEX,
    "SGXQ":Exchange.SGX,
    "TOCOM":Exchange.TOCOM,
    "OSE":Exchange.TOCOM,
    "TSE":Exchange.TSE,
    "BMD":Exchange.BMD,
    "HKEX":Exchange.HKFE,
    "CFE":Exchange.CFE
}
EXCHANGE_VT2ICE: Dict[Exchange, str] = {v: k for k, v in EXCHANGE_ICE2VT.items()}
# 产品类型映射
PRODUCT_ICE2VT: Dict[str, Product] = {
    "FUT": Product.FUTURES,
    "OPT": Product.OPTION,
    "STK": Product.EQUITY
}

# 期权类型映射
OPTIONTYPE_ICE2VT: Dict[str, OptionType] = {
    "C": OptionType.CALL,
    "P": OptionType.PUT
}


# 其他常量
MAX_FLOAT = sys.float_info.max                  # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")       # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: Dict[str, ContractData] = {}


class IceTCoreGateway(BaseGateway,BaseDatafeed):
    default_name: str = "ICETCore"
    default_setting: Dict[str, str] = {
        "客户端路径": "C:/AlgoMaster2/APPs64"
    }

    exchanges: List[str] = list(EXCHANGE_ICE2VT.values())

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        """构造函数"""
        super().__init__(event_engine, gateway_name)
        self.eventobj=IceTCoreAPI(self)
        if "datafeed.apppath" not in SETTINGS.keys():
            SETTINGS["datafeed.apppath"]="C:/AlgoMaster2/APPs64"
        self.username: str = SETTINGS["datafeed.apppath"]
        self.api: "TCoreAPI" =None
        self.reqid: int = 0

        self.subscribed: set = set()

        self.order_ref: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False

        self.login_failed: bool = False
        self.auth_failed: bool = False
        self.contract_inited: bool = False

        self.userid: str = ""
        self.brokerid: str = ""
        self.auth_code: str = ""

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        self.api=TCoreAPI(apppath=setting["客户端路径"],eventclass=self.eventobj)
        # 禁止重复发起连接，会导致异常崩溃
        if not self.connect_status:
            self.api.connect()#(self.appid,self.auth_code)
            self.connect_status = True
            self.qryInstrument()
        #self.init_query()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.write_log("订阅行情"+req.symbol)

        contract: ContractData = symbol_contract_map.get(EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol, None)
        symbolhead="TC.S."
        if contract.product==Product.FUTURES:
            symbolhead="TC.F."
        elif contract.product==Product.OPTION:
            symbolhead="TC.O."
        elif contract.product==Product.SPREAD:
            symbolhead="TC.F2." 
        self.api.subquote(symbolhead+contract.name)
        self.subscribed.add(symbolhead+contract.name)
        #print(symbolhead+EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol)
        #self.api.subquote(symbolhead+EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol)
        #self.subscribed.add(symbolhead+EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        if req.offset not in OFFSET_VT2ICE:
            self.write_log("请选择开平方向")
            return ""

        if req.type not in ORDERTYPE_VT2ICE:
            self.write_log(f"当前接口不支持该类型的委托{req.type.value}")
            return ""

        self.order_ref += 1
        contract: ContractData = symbol_contract_map.get(EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol, None)
        symbolhead="TC.S."
        if contract.product==Product.FUTURES:
            symbolhead="TC.F."
        elif contract.product==Product.OPTION:
            symbolhead="TC.O." 
        elif contract.product==Product.SPREAD:
            symbolhead="TC.F2." 
        tp: tuple = ORDERTYPE_VT2ICE[req.type]
        price_type, time_condition = tp
        OrderStruct.Symbol=symbolhead+contract.name#EXCHANGE_VT2ICE[req.exchange]+"."+req.symbol
        OrderStruct.BrokerID=self.brokerid
        OrderStruct.Account=self.userid
        OrderStruct.Price=req.price
        OrderStruct.TimeInForce=time_condition
        OrderStruct.Side= DIRECTION_VT2ICE.get(req.direction, "")
        OrderStruct.OrderType=price_type
        OrderStruct.OrderQty=int(req.volume)
        OrderStruct.PositionEffect=OFFSET_VT2ICE.get(req.offset, "")#PositionEffect.Auto
        OrderStruct.Synthetic=0
        OrderStruct.SelfTradePrevention=3

        ordid,msg = self.api.neworder(OrderStruct)
        if not ordid:
            self.write_log(f"委托请求发送失败，错误代码：{msg}")
            return ""
        while True:
            if self.api.getorderinfo(ordid):
                orderidlist: str = self.api.getorderinfo(ordid)
                break
        for orderid in orderidlist:
            order: OrderData = req.create_order_data(orderid['ReportID'], self.default_name)
            self.on_order(order)
        return order.vt_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
       #print(req.orderid)
        #self.api.getorderinfo(req.orderid)['ReportID']
        self.api.cancelorder(req.orderid)

    def query_account(self) -> None:
        """查询资金"""
        self.api.getaccmargin(self.brokerid+"-"+self.userid)

    def query_position(self) -> None:
        """查询持仓"""
        if not symbol_contract_map:
            return
        self.api.getposition(self.brokerid+"-"+self.userid)

    def close(self) -> None:
        """关闭连接"""
        if self.connect_status:
            self.api.disconnect()

    def write_error(self, msg: str, error: dict) -> None:
        """输出错误信息日志"""
        error_id: int = error["ErrorID"]
        error_msg: str = error["ErrorMsg"]
        msg: str = f"{msg}，代码：{error_id}，信息：{error_msg}"
        self.write_log(msg)

    def qryInstrument(self):
        """合约查询回报"""
        data=self.api.getallsymbol()
        if data:
            for symb in data:
                symbcheck=symb.split(".")
                if len(symbcheck)>=4:
                    if "TC.O." in symb:
                        product: Product = Product.OPTION
                    elif "TC.S.SSE.60" in symb or "TC.S.SSE.90" in symb or "TC.S.SZSE.00" in symb or "TC.S.SZSE.30" in symb or "TC.S.SZSE.20" in symb:
                        product: Product = Product.EQUITY
                    elif "TC.S.SSE.000" in symb or "TC.S.SZSE.399" in symb:
                        product: Product = Product.INDEX
                    elif "TC.S.SSE.51" in symb or "TC.S.SZSE.15" in symb:
                        product: Product = Product.ETF
                    elif "TC.S.SSE.01" in symb or "TC.S.SSE.11" in symb or "TC.S.SSE.20" in symb or "TC.S.SZSE.10" in symb or "TC.S.SZSE.12" in symb or "TC.S.SZSE.13" in symb:
                        product: Product = Product.BOND
                    elif "TC.S.SSE.50" in symb or "TC.S.SZSE.16" in symb:
                        product: Product = Product.FUND
                    elif  "TC.F2." in symb:
                        product: Product = Product.SPREAD
                    else:
                        product: Product = Product.FUTURES
                    symbol_id=self.api.getsymbol_id(symb)
                    volume_multiple=self.api.getsymbolvolume_multiple(symb)
                    symbol_ticksize=self.api.getsymbol_ticksize(symb)
                    contract: ContractData = ContractData(
                        symbol=symbol_id if "TC.F2." not in symb else symb.replace("TC.F2.",""),
                        exchange=EXCHANGE_ICE2VT[symbcheck[2]] if symbcheck[2] in EXCHANGE_ICE2VT.keys() else Exchange.LOCAL,
                        name=symb.replace(symbcheck[0]+"."+symbcheck[1]+".","") if "TC.F2." not in symb else symb.replace("TC.F2.",""),
                        product=product,
                        size=float(volume_multiple) if volume_multiple else 0.001,
                        pricetick=float(symbol_ticksize) if symbol_ticksize else 1000,
                        gateway_name=self.default_name
                    )
                    underlymap={"IO":"IF","HO":"IH","MO":"IM"}

                    # 期权相关
                    if contract.product == Product.OPTION:
                        underlying=""
                        if ".CFFEX." in symb:
                            underlying=underlymap[symbcheck[3]]+symbcheck[4]
                        else:
                            underlying=symbcheck[3]+symbcheck[4]
                        portfolio=""
                        if ".CFFEX." in symb or "CZCE" in symb:
                            portfolio=symbcheck[3]
                        elif "SSE" in symb or "SZSE" in symb:
                            portfolio=symbcheck[3]+"_O"
                        else:
                            portfolio=symbcheck[3]+"_o"

                        strick=symb.replace(symbcheck[0]+"."+symbcheck[1]+"."+symbcheck[2]+"."+symbcheck[3]+"."+symbcheck[4]+"."+symbcheck[5]+".","")
                        contract.option_portfolio =portfolio
                        contract.option_underlying =underlying
                        contract.option_type = OPTIONTYPE_ICE2VT.get(symbcheck[5], None)
                        contract.option_strike = float(strick)
                        contract.option_index = strick
                        contract.option_expiry = datetime.strptime(self.api.getexpirationdate(symb), "%Y%m%d")
                    symbol_contract_map[symbcheck[2]+"."+contract.symbol] = contract
                    self.on_contract(contract)
      
            self.contract_inited = True
            self.write_log("合约信息查询成功")
            for acc in self.api.getaccountlist():
                data2=self.api.getposition(acc["AccMask"])
                for data1 in data2:
                    if data1["Side"]!=0:
                        symbsplit=data1["Symbol"].split(".")
                        symbol: str =(symbsplit[2]+"."+self.api.getsymbol_id(data1["Symbol"])) if "TC.F2." not in data1["Symbol"] else (data1["Exchange"]+"."+data1["Symbol"].replace("TC.F2.",""))
                        contract1: ContractData= symbol_contract_map.get(symbol, None)
                        # else:
                        #     contract1 = symbol_contract_map.get(symbsplit[2]+"."+symbol, None)
                        if contract1:
                            if data1["SumLongQty"]!=0:
                                position: PositionData = PositionData(
                                    symbol=contract1.symbol,
                                    exchange=contract1.exchange,
                                    direction=Direction.LONG,
                                    volume=float(data1["SumLongQty"]),
                                    price=float(data1["LongOpenPrice"]),
                                    frozen=float(data1["LongFrozen"]),
                                    pnl=float(data1["LongFloatProfitByDate"]),
                                    yd_volume=float(data1["YdLongQty"]),
                                    gateway_name=self.default_name
                                )
                                self.on_position(position)
                            if data1["SumShortQty"]!=0:
                                position: PositionData = PositionData(
                                    symbol=contract1.symbol,
                                    exchange=contract1.exchange,
                                    direction=Direction.SHORT,
                                    volume=float(data1["SumShortQty"]),
                                    price=float(data1["ShortOpenPrice"]),
                                    frozen=data1["ShortFrozen"],
                                    pnl=data1["ShortFloatProfitByDate"],
                                    yd_volume=data1["YdShortQty"],
                                    gateway_name=self.default_name
                                )
                                self.on_position(position)
                        else:
                            self.write_log(f"持仓合约不存在:{data1['Symbol']}")
                            position: PositionData = PositionData(
                                symbol=data1["Symbol"],
                                exchange=Exchange.LOCAL,
                                direction=DIRECTION_ICE2VT[data1["Side"]],
                                volume=float(data1["Quantity"]),
                                price=float(data1["AvgPrice"]),
                                frozen=data1["LongFrozen"] if data1["Side"]==1 else data1["ShortFrozen"],
                                pnl=data1["FloatProfitByDate"],
                                yd_volume=data1["YdLongQty"] if data1["Side"]==1 else data1["YdShortQty"],
                                gateway_name=self.default_name
                            )
                            self.on_position(position)
                          
            orderreport=self.api.getorderreport()
            for orderdata in orderreport:
                if orderdata["ExecType"]!=10 and orderdata['ExecType']!=12:
                    symbsplit=orderdata["Symbol"].split(".")
                    symbol: str =(symbsplit[2]+"."+self.api.getsymbol_id(orderdata["Symbol"])) if "TC.F2." not in orderdata["Symbol"] else (orderdata["Exchange"]+"."+orderdata["Symbol"].replace("TC.F2.",""))
                    contract: ContractData= symbol_contract_map.get(symbol, None)

                    timestamp: str = f"{orderdata['TransactDate']} {orderdata['TransactTime']}"
                    dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
                    dt: datetime = dt.replace(tzinfo=CHINA_TZ)+timedelta(hours=8)

                    tp: tuple = (orderdata["OrderType"], orderdata["TimeInForce"])

                    order: OrderData = OrderData(
                        symbol=contract.symbol,
                        exchange=contract.exchange,
                        orderid=orderdata["ReportID"],
                        type=ORDERTYPE_ICE2VT[tp] if tp in ORDERTYPE_ICE2VT.keys() else OrderType.LIMIT,
                        direction=DIRECTION_ICE2VT[orderdata["Side"]],
                        offset=OFFSET_ICE2VT[orderdata["PositionEffect"]] if orderdata["PositionEffect"] in OFFSET_ICE2VT.keys() else Offset.NONE,
                        price=float(orderdata["Price"] if orderdata["Price"] else 0),
                        volume=float(orderdata["OrderQty"]),
                        traded=float(orderdata["CumQty"]),
                        status=STATUS_ICE2VT[orderdata["ExecType"]] if orderdata["ExecType"] in STATUS_ICE2VT.keys() else Status.REJECTED,
                        datetime=dt,
                        reference=orderdata["UserKey1"],
                        gateway_name=self.default_name
                    )
                    self.on_order(order)
                    self.eventobj.sysid_orderid_map[orderdata["UserKey1"]] = orderdata["ReportID"]

            fillreport=self.api.getfilledreport()
            for filldata in fillreport:
                symbsplit=filldata["Symbol"].split(".")
                symbol: str =(symbsplit[2]+"."+self.api.getsymbol_id(filldata["Symbol"])) if "TC.F2." not in filldata["Symbol"] else (filldata["Exchange"]+"."+filldata["Symbol"].replace("TC.F2.",""))
                contract: ContractData= symbol_contract_map.get(symbol, None)

                timestamp: str = f"{filldata['TransactDate']} {filldata['TransactTime']}"
                dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
                dt: datetime = dt.replace(tzinfo=CHINA_TZ)+timedelta(hours=8)
                
                trade: TradeData = TradeData(
                    symbol=contract.symbol,
                    exchange=contract.exchange,
                    orderid=filldata["ReportID"],
                    tradeid=filldata["OrderID"],
                    direction=DIRECTION_ICE2VT[filldata["Side"]],
                    offset=OFFSET_ICE2VT[filldata["PositionEffect"]] if filldata["PositionEffect"] in OFFSET_ICE2VT.keys() else Offset.NONE,
                    price=float(filldata["AvgPrice"] if filldata["AvgPrice"] else 0),
                    volume=float(filldata["CumQty"]),
                    datetime=dt,
                    gateway_name=self.default_name
                )
                self.on_trade(trade)
class IceTCoreAPI(TradeEvent,QuoteEvent):
    """"""
    def __init__(self, gateway: IceTCoreGateway) -> None:
        """构造函数"""
        self.subscribed: set = set()
        self.gateway: IceTCoreGateway = gateway
        self.gateway_name: str = gateway.gateway_name
        self.default_name: str = "ICETCore"
        self.sysid_orderid_map: Dict[str, str] = {}
        self.current_date: str = datetime.now().strftime("%Y%m%d")

    def onconnected(self,apitype:str) -> None:
        """服务器连接成功回报"""
        if "quote"==apitype:
            self.login_status = True
            self.gateway.write_log("行情接口连线成功")
            for symbol in self.subscribed:
                self.gateway.subscribe(symbol)
        if "trade"== apitype:
            self.gateway.write_log("交易接口连线成功")
            self.gateway.api.submargin()
            self.gateway.api.subposition()

    def ondisconnected(self,apitype:str) -> None:
        """服务器连接断开回报"""
        if "quote" in apitype:
            self.login_status = False
            self.gateway.write_log("行情接口连接断开")
        if "trade" in apitype:
            self.login_status = False
            self.gateway.write_log(f"交易接口连线断开")

    # def onbar(self,datatype,interval,symbol,data:list,isreal:bool)-> None:
    #     pass
    # def ongreeksreal(self,datatype,symbol,data:dict):
    #     pass
    # def ongreeksline(self,datatype,interval,symbol,data,isreal):
    #     pass
    def onquote(self,data)-> None:
        """行情数据推送"""
        # 过滤没有时间戳的异常行情数据
        # if not data["DateTime"]:
        #     return
        # # 过滤还没有收到合约数据前的行情推送
        symbsplit=data["Symbol"].split(".")
        symbol: str =(symbsplit[2]+"."+self.gateway.api.getsymbol_id(data["Symbol"])) if "TC.F2." not in data["Symbol"] else (data["Exchange"]+"."+data["Symbol"].replace("TC.F2.",""))
        contract: ContractData= symbol_contract_map.get(symbol, None)

        if not contract:
            return
        tick: TickData = TickData(
            symbol=contract.symbol,
            exchange=contract.exchange,
            datetime=data["DateTime"].replace(tzinfo=CHINA_TZ),
            #name=contract.name,
            volume=data["Volume"]if data["Volume"] else 0,
            turnover=data["Turnover"] if data["Turnover"] else 0,
            open_interest=data["OpenInterest"] if "OpenInterest" in data.keys() else 0,
            last_price=adjust_price(data["Last"]) if adjust_price(data["Last"]) else 0,
            limit_up=data["UpperLimit"] if data["UpperLimit"] else 0,
            limit_down=data["LowerLimit"] if data["LowerLimit"] else 0,
            open_price=adjust_price(data["Open"]) if adjust_price(data["Open"]) else 0,
            high_price=adjust_price(data["High"]) if adjust_price(data["High"]) else 0,
            low_price=adjust_price(data["Low"]) if adjust_price(data["Low"]) else 0,
            pre_close=adjust_price(data["YClosedPrice"]) if adjust_price(data["YClosedPrice"]) else 0,
            bid_price_1=adjust_price(data["Bid"]) if adjust_price(data["Bid"]) else 0,
            ask_price_1=adjust_price(data["Ask"]) if adjust_price(data["Ask"]) else 0,
            bid_volume_1=data["BidVolume"] if data["BidVolume"] else 0,
            ask_volume_1=data["AskVolume"] if data["AskVolume"] else 0,
            gateway_name=self.gateway_name
        )

        if data["BidVolume1"] or data["AskVolume1"]:
            tick.bid_price_2 = adjust_price(data["Bid1"])
            tick.bid_price_3 = adjust_price(data["Bid2"])
            tick.bid_price_4 = adjust_price(data["Bid3"])
            tick.bid_price_5 = adjust_price(data["Bid4"])

            tick.ask_price_2 = adjust_price(data["Ask1"])
            tick.ask_price_3 = adjust_price(data["Ask2"])
            tick.ask_price_4 = adjust_price(data["Ask3"])
            tick.ask_price_5 = adjust_price(data["Ask4"])

            tick.bid_volume_2 = data["BidVolume1"]
            tick.bid_volume_3 = data["BidVolume2"]
            tick.bid_volume_4 = data["BidVolume3"]
            tick.bid_volume_5 = data["BidVolume4"]

            tick.ask_volume_2 = data["AskVolume1"]
            tick.ask_volume_3 = data["AskVolume2"]
            tick.ask_volume_4 = data["AskVolume3"]
            tick.ask_volume_5 = data["AskVolume4"]

        self.gateway.on_tick(tick)

    # def onATM(self,datatype,symbol,data:dict):
    #     pass
    def onservertime(self, serverdt):
        self.current_date = serverdt.strftime("%Y%m%d")#.replace(tzinfo=CHINA_TZ)
    def onaccountlist(self,data,count):
        if count>0:
            self.gateway.userid=data[0]["Account"]
            self.gateway.brokerid=data[0]["BrokerID"]
    def onordereportreal(self,data):
        """委托更新推送"""
        if not self.gateway.contract_inited:
            return
        # if data["ExecType"]==10:
        #     self.gateway.write_error("交易委托失败",data["ReportID"])
        #     return
        # elif data['ExecType']==12:
        #     self.gateway.write_log("删改单失败："+data["ReportID"])
        #     return
        symbsplit=data["Symbol"].split(".")
        symbol: str =(symbsplit[2]+"."+self.gateway.api.getsymbol_id(data["Symbol"])) if "TC.F2." not in data["Symbol"] else (data["Exchange"]+"."+data["Symbol"].replace("TC.F2.",""))
        contract: ContractData= symbol_contract_map.get(symbol, None)
        timestamp: str = f"{data['TransactDate']} {data['TransactTime']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
        dt: datetime = dt.replace(tzinfo=CHINA_TZ)+timedelta(hours=8)

        tp: tuple = (data["OrderType"], data["TimeInForce"])

        order: OrderData = OrderData(
            symbol=contract.symbol,
            exchange=contract.exchange,
            orderid=data["ReportID"],
            type=ORDERTYPE_ICE2VT[tp] if tp in ORDERTYPE_ICE2VT.keys() else OrderType.LIMIT,
            direction=DIRECTION_ICE2VT[data["Side"]],
            offset=OFFSET_ICE2VT[data["PositionEffect"]] if data["PositionEffect"] in OFFSET_ICE2VT.keys() else Offset.NONE,
            price=float(data["Price"] if data["Price"] else 0),
            volume=float(data["OrderQty"]),
            traded=float(data["CumQty"]),
            status=STATUS_ICE2VT[data["ExecType"]] if data["ExecType"] in STATUS_ICE2VT.keys() else Status.REJECTED,
            datetime=dt,
            reference=data["UserKey1"],
            gateway_name=self.gateway_name
        )
        self.gateway.on_order(order)

        self.sysid_orderid_map[data["UserKey1"]] = data["ReportID"]
    def onfilledreportreal(self,data):
        """成交数据推送"""
        if not self.gateway.contract_inited:
            return
        symbsplit=data["Symbol"].split(".")
        symbol: str =(symbsplit[2]+"."+self.gateway.api.getsymbol_id(data["Symbol"])) if "TC.F2." not in data["Symbol"] else (data["Exchange"]+"."+data["Symbol"].replace("TC.F2.",""))
        contract: ContractData= symbol_contract_map.get(symbol, None)

        orderid: str = self.sysid_orderid_map[data["UserKey1"]]

        timestamp: str = f"{data['TransactDate']} {data['TransactTime']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H%M%S")
        dt: datetime = dt.replace(tzinfo=CHINA_TZ)+timedelta(hours=8)
        
        trade: TradeData = TradeData(
            symbol=contract.symbol,
            exchange=contract.exchange,
            orderid=data["DetailReportID"],
            tradeid=data["OrderID"],
            direction=DIRECTION_ICE2VT[data["Side"]],
            offset=OFFSET_ICE2VT[data["PositionEffect"]] if data["PositionEffect"] in OFFSET_ICE2VT.keys() else Offset.NONE,
            price=float(data["MatchedPrice"] if data["MatchedPrice"] else 0),
            volume=float(data["MatchedQty"]),
            datetime=dt,
            gateway_name=self.gateway_name
        )
        self.gateway.on_trade(trade)
    # def onorderreportreset(self):
    #     self.positions.clear()
    # def onpositionmoniter(self,data):
    #     pass
    def onmargin(self,accmask,data):
        """资金查询回报"""
        # if "Account" not in data[0].keys():
        #     return
        for data1 in data:
            if "Account" not in data1.keys():
                return
            account: AccountData = AccountData(
                accountid=data1["Account"],
                balance=float(data1["TotalEquity"]),
                frozen=data1["FrozenCash"] if data1["FrozenCash"] else 0,
                gateway_name=self.gateway_name
            )
            account.available = data1["ExcessEquity"]
            self.gateway.on_account(account)

    def onposition(self,accmask,data):
        if not data:
            return
        if not self.gateway.contract_inited:
            return
        for data1 in data:
            if data1["Side"]!=0:
                symbsplit=data1["Symbol"].split(".")
                symbol: str =(symbsplit[2]+"."+self.gateway.api.getsymbol_id(data1["Symbol"])) if "TC.F2." not in data1["Symbol"] else (data1["Exchange"]+"."+data1["Symbol"].replace("TC.F2.",""))
                contract: ContractData= symbol_contract_map.get(symbol, None)
                if contract:
                    if data1["SumLongQty"]!=0:
                        position: PositionData = PositionData(
                            symbol=contract.symbol,
                            exchange=contract.exchange,
                            direction=Direction.LONG,
                            volume=float(data1["SumLongQty"]),
                            price=float(data1["LongOpenPrice"]),
                            frozen=float(data1["LongFrozen"]),
                            pnl=float(data1["LongFloatProfitByDate"]),
                            yd_volume=float(data1["YdLongQty"]),
                            gateway_name=self.default_name
                        )
                        self.gateway.on_position(position)
                    if data1["SumShortQty"]!=0:
                        position: PositionData = PositionData(
                            symbol=contract.symbol,
                            exchange=contract.exchange,
                            direction=Direction.SHORT,
                            volume=float(data1["SumShortQty"]),
                            price=float(data1["ShortOpenPrice"]),
                            frozen=data1["ShortFrozen"],
                            pnl=data1["ShortFloatProfitByDate"],
                            yd_volume=data1["YdShortQty"],
                            gateway_name=self.default_name
                        )
                        self.gateway.on_position(position)
                else:
                    self.gateway.write_log(f"持仓合约不存在:{data1['Symbol']}")
                    position: PositionData = PositionData(
                        symbol=data1["Symbol"],
                        exchange=Exchange.LOCAL,
                        direction=DIRECTION_ICE2VT[data1["Side"]],
                        volume=float(data1["Quantity"]),
                        price=float(data1["AvgPrice"]),
                        frozen=data1["LongFrozen"] if data1["Side"]==1 else data1["ShortFrozen"],
                        pnl=data1["FloatProfitByDate"],
                        yd_volume=data1["YdLongQty"] if data1["Side"]==1 else data1["YdShortQty"],
                        gateway_name=self.gateway_name
                    )
                    self.gateway.on_position(position)


def adjust_price(price: float) -> float:
    """将异常的浮点数最大值（MAX_FLOAT）数据调整为0"""
    if price == MAX_FLOAT:
        price = 0
    return price
