"""
Protobuf Schemas for Real-time Data Processing
مخططات Protobuf لمعالجة البيانات الفورية

Optimized binary schemas for high-performance data transformation
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import struct
import json

# Protobuf message definitions (simplified for demonstration)
# في التطبيق الفعلي، استخدم مكتبة protobuf الرسمية

@dataclass
class MarketDataProto:
    """
    رسالة بيانات السوق بتنسيق protobuf
    """
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    exchange: str
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    
    def to_binary(self) -> bytes:
        """
        تحويل إلى صيغة ثنائية محسّنة
        """
        # استخدام struct للتغليف الفعال
        # Format: symbol_len(1) + symbol + price(8) + volume(4) + timestamp(8) + exchange_len(1) + exchange + ...
        
        symbol_bytes = self.symbol.encode('utf-8')
        exchange_bytes = self.exchange.encode('utf-8')
        
        # رأس الرسالة
        header = struct.pack(
            '>B',  # symbol length
            len(symbol_bytes)
        )
        
        # بيانات السوق
        market_data = struct.pack(
            '>8sI8sB',  # price(8), volume(4), timestamp(8), exchange_len(1)
            struct.pack('>d', self.price),  # price as double
            self.volume,
            struct.pack('>d', self.timestamp.timestamp()),
            len(exchange_bytes)
        )
        
        # بيانات العرض والطلب
        bid_ask_data = struct.pack(
            '>8s8sI',  # bid_price(8), ask_price(8), bid_size(4)
            struct.pack('>d', self.bid_price),
            struct.pack('>d', self.ask_price),
            self.bid_size
        )
        
        # تجميع كل شيء
        return (
            header + 
            symbol_bytes + 
            market_data + 
            exchange_bytes + 
            bid_ask_data +
            struct.pack('>I', self.ask_size)  # ask_size(4)
        )
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'MarketDataProto':
        """
        تحليل من الصيغة الثنائية (zero-copy)
        """
        offset = 0
        
        # قراءة طول الرمز
        symbol_len = data[offset]
        offset += 1
        
        # قراءة الرمز
        symbol = data[offset:offset + symbol_len].decode('utf-8')
        offset += symbol_len
        
        # قراءة بيانات السوق
        price, volume, timestamp, exchange_len = struct.unpack('>dI8sB', data[offset:offset + 21])
        offset += 21
        
        price = struct.unpack('>d', price)[0]
        timestamp = datetime.fromtimestamp(struct.unpack('>d', timestamp)[0])
        
        # قراءة اسم البورصة
        exchange = data[offset:offset + exchange_len].decode('utf-8')
        offset += exchange_len
        
        # قراءة بيانات العرض والطلب
        bid_price, ask_price, bid_size = struct.unpack('>8s8sI', data[offset:offset + 20])
        offset += 20
        
        bid_price = struct.unpack('>d', bid_price)[0]
        ask_price = struct.unpack('>d', ask_price)[0]
        
        # قراءة ask_size
        ask_size = struct.unpack('>I', data[offset:offset + 4])[0]
        
        return cls(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp,
            exchange=exchange,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=bid_size,
            ask_size=ask_size
        )

@dataclass
class FIXMessageProto:
    """
    رسالة FIX بتنسيق protobuf
    """
    msg_type: str
    sender_comp_id: str
    target_comp_id: str
    timestamp: datetime
    fields: Dict[str, str]
    
    def to_binary(self) -> bytes:
        """
        تحويل رسالة FIX إلى صيغة ثنائية
        """
        # تحويل الحقول إلى JSON للتبسيط
        fields_json = json.dumps(self.fields).encode('utf-8')
        
        sender_bytes = self.sender_comp_id.encode('utf-8')
        target_bytes = self.target_comp_id.encode('utf-8')
        msg_type_bytes = self.msg_type.encode('utf-8')
        
        # رأس الرسالة
        header = struct.pack(
            '>BBB',  # msg_type_len, sender_len, target_len
            len(msg_type_bytes),
            len(sender_bytes),
            len(target_bytes)
        )
        
        # بيانات الرسالة
        message_data = struct.pack(
            '>8sI',  # timestamp(8), fields_len(4)
            struct.pack('>d', self.timestamp.timestamp()),
            len(fields_json)
        )
        
        return (
            header +
            msg_type_bytes +
            sender_bytes +
            target_bytes +
            message_data +
            fields_json
        )
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'FIXMessageProto':
        """
        تحليل رسالة FIX من الصيغة الثنائية
        """
        offset = 0
        
        # قراءة أطوال الحقول
        msg_type_len, sender_len, target_len = struct.unpack('>BBB', data[offset:offset + 3])
        offset += 3
        
        # قراءة الحقول
        msg_type = data[offset:offset + msg_type_len].decode('utf-8')
        offset += msg_type_len
        
        sender_comp_id = data[offset:offset + sender_len].decode('utf-8')
        offset += sender_len
        
        target_comp_id = data[offset:offset + target_len].decode('utf-8')
        offset += target_len
        
        # قراءة بيانات الرسالة
        timestamp, fields_len = struct.unpack('>8sI', data[offset:offset + 12])
        offset += 12
        
        timestamp = datetime.fromtimestamp(struct.unpack('>d', timestamp)[0])
        
        # قراءة الحقول
        fields_json = data[offset:offset + fields_len].decode('utf-8')
        fields = json.loads(fields_json)
        
        return cls(
            msg_type=msg_type,
            sender_comp_id=sender_comp_id,
            target_comp_id=target_comp_id,
            timestamp=timestamp,
            fields=fields
        )

@dataclass
class WebSocketMessageProto:
    """
    رسالة WebSocket بتنسيق protobuf
    """
    message_type: str
    source_id: str
    timestamp: datetime
    payload: bytes
    metadata: Dict[str, Any]
    
    def to_binary(self) -> bytes:
        """
        تحويل رسالة WebSocket إلى صيغة ثنائية
        """
        source_bytes = self.source_id.encode('utf-8')
        msg_type_bytes = self.message_type.encode('utf-8')
        metadata_json = json.dumps(self.metadata).encode('utf-8')
        
        # رأس الرسالة
        header = struct.pack(
            '>BB',  # source_len, msg_type_len
            len(source_bytes),
            len(msg_type_bytes)
        )
        
        # بيانات الرسالة
        message_data = struct.pack(
            '>8sII',  # timestamp(8), payload_len(4), metadata_len(4)
            struct.pack('>d', self.timestamp.timestamp()),
            len(self.payload),
            len(metadata_json)
        )
        
        return (
            header +
            source_bytes +
            msg_type_bytes +
            message_data +
            self.payload +
            metadata_json
        )
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'WebSocketMessageProto':
        """
        تحليل رسالة WebSocket من الصيغة الثنائية
        """
        offset = 0
        
        # قراءة أطوال الحقول
        source_len, msg_type_len = struct.unpack('>BB', data[offset:offset + 2])
        offset += 2
        
        # قراءة الحقول
        source_id = data[offset:offset + source_len].decode('utf-8')
        offset += source_len
        
        message_type = data[offset:offset + msg_type_len].decode('utf-8')
        offset += msg_type_len
        
        # قراءة بيانات الرسالة
        timestamp, payload_len, metadata_len = struct.unpack('>8sII', data[offset:offset + 16])
        offset += 16
        
        timestamp = datetime.fromtimestamp(struct.unpack('>d', timestamp)[0])
        
        # قراءة المحتوى والبيانات الوصفية
        payload = data[offset:offset + payload_len]
        offset += payload_len
        
        metadata_json = data[offset:offset + metadata_len].decode('utf-8')
        metadata = json.loads(metadata_json)
        
        return cls(
            message_type=message_type,
            source_id=source_id,
            timestamp=timestamp,
            payload=payload,
            metadata=metadata
        )

class ProtobufConverter:
    """
    محول بيانات عالي الأداء إلى protobuf
    """
    
    def __init__(self):
        self.converters = {
            'market_data': self._convert_market_data,
            'fix_message': self._convert_fix_message,
            'websocket_message': self._convert_websocket_message,
            'generic': self._convert_generic
        }
    
    def convert_to_protobuf(self, data_type: str, raw_data: bytes, metadata: Dict[str, Any] = None) -> bytes:
        """
        تحويل البيانات الخام إلى protobuf
        """
        if metadata is None:
            metadata = {}
        
        converter = self.converters.get(data_type, self.converters['generic'])
        return converter(raw_data, metadata)
    
    def _convert_market_data(self, raw_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """
        تحويل بيانات السوق
        """
        # تحليل البيانات الخام (JSON مثلاً)
        try:
            data = json.loads(raw_data.decode('utf-8'))
            
            market_data = MarketDataProto(
                symbol=data.get('symbol', ''),
                price=float(data.get('price', 0.0)),
                volume=int(data.get('volume', 0)),
                timestamp=datetime.now(),
                exchange=data.get('exchange', ''),
                bid_price=float(data.get('bid_price', 0.0)),
                ask_price=float(data.get('ask_price', 0.0)),
                bid_size=int(data.get('bid_size', 0)),
                ask_size=int(data.get('ask_size', 0))
            )
            
            return market_data.to_binary()
            
        except Exception as e:
            # في حالة الخطأ، تحويل إلى رسالة عامة
            return self._convert_generic(raw_data, {'error': str(e)})
    
    def _convert_fix_message(self, raw_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """
        تحويل رسالة FIX
        """
        # تحليل رسالة FIX
        fields = {}
        parts = raw_data.split(b'\x01')  # SOH separator
        
        for part in parts:
            if b'=' in part:
                key, value = part.split(b'=', 1)
                fields[key.decode('utf-8')] = value.decode('utf-8')
        
        fix_message = FIXMessageProto(
            msg_type=fields.get('35', ''),  # MsgType
            sender_comp_id=fields.get('49', ''),  # SenderCompID
            target_comp_id=fields.get('56', ''),  # TargetCompID
            timestamp=datetime.now(),
            fields=fields
        )
        
        return fix_message.to_binary()
    
    def _convert_websocket_message(self, raw_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """
        تحويل رسالة WebSocket
        """
        ws_message = WebSocketMessageProto(
            message_type=metadata.get('message_type', 'unknown'),
            source_id=metadata.get('source_id', 'websocket'),
            timestamp=datetime.now(),
            payload=raw_data,
            metadata=metadata
        )
        
        return ws_message.to_binary()
    
    def _convert_generic(self, raw_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """
        تحويل عام للبيانات
        """
        # تغليف البيانات الخام في رسالة عامة
        generic_message = WebSocketMessageProto(
            message_type='generic',
            source_id=metadata.get('source_id', 'unknown'),
            timestamp=datetime.now(),
            payload=raw_data,
            metadata=metadata
        )
        
        return generic_message.to_binary()

# مصنع Protobuf لإنشاء محولات محسّنة
class ProtobufFactory:
    """
    مصنع لإنشاء محولات protobuf محسّنة
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._converter = ProtobufConverter()
        return cls._instance
    
    @property
    def converter(self) -> ProtobufConverter:
        """الحصول على المحول"""
        return self._converter
    
    def create_market_data_converter(self) -> callable:
        """
        إنشاء محول بيانات السوق
        """
        return lambda data, meta: self.converter.convert_to_protobuf('market_data', data, meta)
    
    def create_fix_converter(self) -> callable:
        """
        إنشاء محول رسائل FIX
        """
        return lambda data, meta: self.converter.convert_to_protobuf('fix_message', data, meta)
    
    def create_websocket_converter(self) -> callable:
        """
        إنشاء محول رسائل WebSocket
        """
        return lambda data, meta: self.converter.convert_to_protobuf('websocket_message', data, meta)

# مثال على الاستخدام
def example_usage():
    """
    مثال على استخدام محولات protobuf
    """
    factory = ProtobufFactory()
    
    # تحويل بيانات السوق
    market_data_json = json.dumps({
        'symbol': 'AAPL',
        'price': 150.25,
        'volume': 1000,
        'exchange': 'NASDAQ',
        'bid_price': 150.20,
        'ask_price': 150.30,
        'bid_size': 500,
        'ask_size': 500
    }).encode('utf-8')
    
    market_protobuf = factory.converter.convert_to_protobuf(
        'market_data', 
        market_data_json
    )
    
    # تحويل رسالة FIX
    fix_message = b'35=D\x0149=CLIENT\x0156=SERVER\x0111=123456\x0155=AAPL\x0154=1\x0138=100\x0144=150.25\x0110=123\x01'
    
    fix_protobuf = factory.converter.convert_to_protobuf(
        'fix_message',
        fix_message
    )
    
    print(f"Market data protobuf size: {len(market_protobuf)} bytes")
    print(f"FIX message protobuf size: {len(fix_protobuf)} bytes")
    
    # التحقق من التحويل العكسي
    market_data = MarketDataProto.from_binary(market_protobuf)
    print(f"Decoded market data: {market_data.symbol} @ {market_data.price}")
    
    fix_msg = FIXMessageProto.from_binary(fix_protobuf)
    print(f"Decoded FIX message: {fix_msg.msg_type} from {fix_msg.sender_comp_id}")

if __name__ == "__main__":
    example_usage()
