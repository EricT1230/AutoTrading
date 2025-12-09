"""
OKX 交易所 API 整合

實作 OKX 交易所的具體功能，包含現貨和合約交易
"""

import ccxt
import pandas as pd
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import time
import hmac
import hashlib
import base64
import requests
import websocket
from loguru import logger

from .exchange_base import (
    ExchangeBase, Order, Balance, Position, 
    OrderType, OrderSide, OrderStatus
)


class OKXExchange(ExchangeBase):
    """OKX 交易所實作"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # API 配置
        self.api_key = config.get("api_key")
        self.secret_key = config.get("secret_key") 
        self.passphrase = config.get("passphrase")
        self.testnet = config.get("testnet", True)
        
        # OKX API 端點
        if self.testnet:
            self.base_url = "https://www.okx.com"
            self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
            self.ws_private_url = "wss://ws.okx.com:8443/ws/v5/private"
        else:
            self.base_url = "https://www.okx.com"
            self.ws_url = "wss://ws.okx.com:8443/ws/v5/public" 
            self.ws_private_url = "wss://ws.okx.com:8443/ws/v5/private"
            
        # 初始化 ccxt 客戶端
        self.client = ccxt.okx({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'password': self.passphrase,
            'sandbox': self.testnet,
            'enableRateLimit': True,
            'timeout': 30000
        })
        
        # WebSocket 連接
        self.ws_connection = None
        self.ws_private_connection = None
        
        logger.info(f"OKX Exchange initialized - Testnet: {self.testnet}")
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, 
                          limit: int = 100) -> pd.DataFrame:
        """
        獲取歷史 K 線數據
        
        Args:
            symbol: 交易對符號 (e.g., 'BTC/USDT')
            timeframe: 時間框架 (1m, 5m, 15m, 1h, 4h, 1d)
            limit: 返回數據筆數 (最多300)
            
        Returns:
            包含 OHLCV 數據的 DataFrame
        """
        try:
            # OKX 時間框架映射
            timeframe_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
                '30m': '30m', '1h': '1H', '2h': '2H', '4h': '4H',
                '6h': '6H', '12h': '12H', '1d': '1D', '1w': '1W'
            }
            
            okx_timeframe = timeframe_map.get(timeframe, '5m')
            
            # 獲取數據
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.client.fetch_ohlcv,
                symbol, okx_timeframe, None, limit
            )
            
            # 轉換為 DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 時間戳轉換
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 數據型別轉換
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
                
            logger.info(f"Fetched {len(df)} bars for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    async def create_order(self, symbol: str, order_type: OrderType,
                          side: OrderSide, amount: float,
                          price: Optional[float] = None) -> Order:
        """
        建立訂單
        
        Args:
            symbol: 交易對符號
            order_type: 訂單類型 (market/limit)
            side: 買賣方向
            amount: 交易數量
            price: 限價單價格
            
        Returns:
            Order 物件
        """
        try:
            # 準備訂單參數
            order_params = {
                'symbol': symbol,
                'type': order_type.value,
                'side': side.value,
                'amount': amount
            }
            
            if order_type == OrderType.LIMIT and price:
                order_params['price'] = price
                
            # 提交訂單
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.create_order,
                **order_params
            )
            
            # 轉換為 Order 物件
            order = Order(
                id=response['id'],
                symbol=symbol,
                side=side,
                type=order_type,
                amount=amount,
                price=price,
                status=OrderStatus.OPEN,
                filled_amount=0.0,
                remaining_amount=amount,
                timestamp=pd.Timestamp.now()
            )
            
            logger.info(f"Order created: {order.id} {side.value} {amount} {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消訂單"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.cancel_order,
                order_id, symbol
            )
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """查詢訂單狀態"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_order,
                order_id, symbol
            )
            
            # 狀態映射
            status_map = {
                'open': OrderStatus.OPEN,
                'closed': OrderStatus.FILLED,
                'canceled': OrderStatus.CANCELED,
                'rejected': OrderStatus.REJECTED
            }
            
            order = Order(
                id=response['id'],
                symbol=response['symbol'],
                side=OrderSide(response['side']),
                type=OrderType(response['type']),
                amount=response['amount'],
                price=response['price'],
                status=status_map.get(response['status'], OrderStatus.PENDING),
                filled_amount=response['filled'],
                remaining_amount=response['remaining'],
                timestamp=pd.Timestamp(response['timestamp'])
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            raise
    
    async def fetch_balance(self) -> Dict[str, Balance]:
        """獲取帳戶餘額"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_balance
            )
            
            balances = {}
            for currency, balance_info in response.items():
                if currency != 'info':
                    balances[currency] = Balance(
                        currency=currency,
                        total=balance_info.get('total', 0),
                        free=balance_info.get('free', 0),
                        used=balance_info.get('used', 0)
                    )
            
            return balances
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    async def fetch_positions(self) -> List[Position]:
        """獲取持倉資訊"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_positions
            )
            
            positions = []
            for pos_info in response:
                if pos_info['contracts'] > 0:  # 只返回有持倉的
                    position = Position(
                        symbol=pos_info['symbol'],
                        size=pos_info['contracts'],
                        entry_price=pos_info['entryPrice'],
                        mark_price=pos_info['markPrice'],
                        pnl=pos_info['unrealizedPnl'],
                        percentage=pos_info['percentage']
                    )
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    async def get_ticker(self, symbol: str) -> Dict:
        """獲取單個交易對的即時報價"""
        try:
            ticker = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_ticker,
                symbol
            )
            
            return {
                'symbol': ticker['symbol'],
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'change': ticker['change'],
                'percentage': ticker['percentage'],
                'timestamp': ticker['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """獲取訂單簿數據"""
        try:
            orderbook = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_order_book,
                symbol, limit
            )
            
            return {
                'symbol': symbol,
                'bids': orderbook['bids'][:limit],  # [[price, amount], ...]
                'asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            raise
    
    def _sign_request(self, method: str, endpoint: str, 
                     params: str = '', body: str = '') -> Dict[str, str]:
        """OKX API 簽名"""
        timestamp = str(int(time.time()))
        
        if params:
            message = timestamp + method.upper() + endpoint + params + body
        else:
            message = timestamp + method.upper() + endpoint + body
            
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase
        }
    
    async def start_websocket(self, symbols: List[str], 
                             on_message_callback=None):
        """啟動 WebSocket 連接"""
        try:
            import websocket
            
            def on_message(ws, message):
                data = json.loads(message)
                if on_message_callback:
                    on_message_callback(data)
                    
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
                
            def on_close(ws, close_status_code, close_msg):
                logger.info("WebSocket connection closed")
                
            def on_open(ws):
                logger.info("WebSocket connection opened")
                
                # 訂閱行情數據
                for symbol in symbols:
                    # 訂閱 Ticker
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [{
                            "channel": "tickers",
                            "instId": symbol.replace('/', '-')
                        }]
                    }
                    ws.send(json.dumps(subscribe_msg))
                    
                    # 訂閱 K 線數據
                    subscribe_msg = {
                        "op": "subscribe", 
                        "args": [{
                            "channel": "candle5m",
                            "instId": symbol.replace('/', '-')
                        }]
                    }
                    ws.send(json.dumps(subscribe_msg))
            
            # 創建 WebSocket 連接
            websocket.enableTrace(False)
            self.ws_connection = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # 在背景執行
            import threading
            ws_thread = threading.Thread(
                target=self.ws_connection.run_forever
            )
            ws_thread.daemon = True
            ws_thread.start()
            
            logger.info(f"WebSocket started for symbols: {symbols}")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket: {e}")
            raise
    
    def stop_websocket(self):
        """停止 WebSocket 連接"""
        if self.ws_connection:
            self.ws_connection.close()
            logger.info("WebSocket connection stopped")
    
    async def get_trading_fees(self, symbol: str) -> Dict:
        """獲取交易手續費"""
        try:
            fees = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fetch_trading_fee,
                symbol
            )
            
            return {
                'symbol': symbol,
                'maker': fees['maker'],
                'taker': fees['taker'],
                'percentage': True,  # OKX 使用百分比費率
                'tierBased': True
            }
            
        except Exception as e:
            logger.error(f"Error fetching trading fees for {symbol}: {e}")
            return {'maker': 0.001, 'taker': 0.0015}  # 默認費率
    
    async def get_markets(self) -> Dict[str, Dict]:
        """獲取所有可交易市場"""
        try:
            markets = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.load_markets
            )
            
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            raise