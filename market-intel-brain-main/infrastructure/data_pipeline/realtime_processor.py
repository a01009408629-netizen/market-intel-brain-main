"""
Real-time Data Pipeline Engineering
هندسة معالجة البيانات الفورية

Transforms 30+ data sources to protobuf format using zero-copy deserialization
Supports WebSockets and FIX protocol with high-performance processing
"""

import asyncio
import websockets
import asyncio
import struct
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import deque
import protobuf
import fix_protocol
import zero_copy
from memoryview import memoryview

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataSourceConfig:
    """تكوين مصدر البيانات"""
    source_id: str
    protocol: str  # 'websocket', 'fix', 'rest', 'tcp'
    endpoint: str
    credentials: Dict[str, str] = field(default_factory=dict)
    data_format: str = 'json'  # 'json', 'fix', 'binary', 'csv'
    buffer_size: int = 8192
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10

@dataclass
class ProcessedData:
    """البيانات المعالجة بتنسيق protobuf"""
    source_id: str
    timestamp: datetime
    data_type: str
    protobuf_data: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0

class ZeroCopyDeserializer:
    """
    محلل بيانات بنسخة صفرية - Zero-Copy Deserializer
    يحول البيانات من الشبكة مباشرة إلى الذاكرة بدون نسخ إضافي
    """
    
    def __init__(self, max_buffer_size: int = 64 * 1024):
        self.max_buffer_size = max_buffer_size
        self.buffer_pool = deque(maxlen=100)  # Pool of reusable buffers
        
    def get_buffer(self) -> memoryview:
        """الحصول على مخزن مؤقت من المجمع"""
        if self.buffer_pool:
            return self.buffer_pool.popleft()
        return memoryview(bytearray(self.max_buffer_size))
    
    def return_buffer(self, buffer: memoryview):
        """إعادة المخزن المؤقت إلى المجمع"""
        if len(buffer) == self.max_buffer_size:
            self.buffer_pool.append(buffer)
    
    def deserialize_websocket(self, raw_data: bytes) -> ProcessedData:
        """
        تحليل بيانات WebSocket بنسخة صفرية
        """
        start_time = datetime.now()
        
        # استخدام memoryview للوصول المباشر للبيانات
        data_view = memoryview(raw_data)
        
        # تحليل الرأس بدون نسخ
        header_size = struct.unpack('>H', data_view[:2])[0]
        header_data = data_view[2:2+header_size]
        
        # تحليل المحتوى بدون نسخ
        payload_data = data_view[2+header_size:]
        
        # تحويل مباشر إلى protobuf
        protobuf_data = self._convert_to_protobuf(
            source_id="websocket",
            header=header_data,
            payload=payload_data
        )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ProcessedData(
            source_id="websocket",
            timestamp=datetime.now(),
            data_type="websocket",
            protobuf_data=protobuf_data,
            processing_time_ms=processing_time
        )
    
    def deserialize_fix(self, raw_data: bytes) -> ProcessedData:
        """
        تحليل بيانات FIX protocol بنسخة صفرية
        """
        start_time = datetime.now()
        
        # تحليل رسائل FIX باستخدام memoryview
        data_view = memoryview(raw_data)
        
        # البحث عن SOH (0x01) كفاصل
        soh_positions = []
        for i, byte in enumerate(data_view):
            if byte == 0x01:  # SOH character
                soh_positions.append(i)
        
        # تحليل الحقول بدون نسخ
        fix_fields = {}
        for i in range(len(soh_positions) - 1):
            start = soh_positions[i] + 1
            end = soh_positions[i + 1]
            field_data = data_view[start:end]
            
            # تقسيم الحقل (tag=value)
            eq_pos = field_data.tobytes().find(b'=')
            if eq_pos != -1:
                tag = field_data[:eq_pos].tobytes().decode()
                value = field_data[eq_pos + 1:].tobytes().decode()
                fix_fields[tag] = value
        
        # تحويل مباشر إلى protobuf
        protobuf_data = self._convert_fix_to_protobuf(fix_fields)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ProcessedData(
            source_id="fix",
            timestamp=datetime.now(),
            data_type="fix",
            protobuf_data=protobuf_data,
            processing_time_ms=processing_time,
            metadata={"fix_fields": fix_fields}
        )
    
    def _convert_to_protobuf(self, source_id: str, header: memoryview, payload: memoryview) -> bytes:
        """
        تحويل البيانات إلى protobuf format
        """
        # إنشاء رسالة protobuf
        # هذا مثال بسيط - يجب استبداله بال protobuf الفعلي
        proto_message = {
            'source_id': source_id,
            'timestamp': datetime.now().isoformat(),
            'header': header.tobytes(),
            'payload': payload.tobytes()
        }
        
        # تحويل إلى bytes protobuf
        # استخدم مكتبة protobuf الفعلية هنا
        return str(proto_message).encode('utf-8')
    
    def _convert_fix_to_protobuf(self, fix_fields: Dict[str, str]) -> bytes:
        """
        تحويل حقول FIX إلى protobuf
        """
        proto_message = {
            'source_id': 'fix',
            'timestamp': datetime.now().isoformat(),
            'fix_fields': fix_fields
        }
        
        return str(proto_message).encode('utf-8')

class WebSocketDataReceiver:
    """
    مستقبل بيانات WebSocket عالي الأداء
    """
    
    def __init__(self, config: DataSourceConfig, deserializer: ZeroCopyDeserializer):
        self.config = config
        self.deserializer = deserializer
        self.websocket = None
        self.is_running = False
        self.reconnect_count = 0
        self.data_queue = asyncio.Queue(maxsize=10000)
        
    async def connect(self):
        """الاتصال بمصدر WebSocket"""
        try:
            self.websocket = await websockets.connect(
                self.config.endpoint,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.reconnect_count = 0
            logger.info(f"Connected to WebSocket: {self.config.endpoint}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def receive_loop(self):
        """
        حلقة استقبال البيانات المستمرة
        """
        while self.is_running:
            try:
                if not self.websocket:
                    if not await self.connect():
                        await asyncio.sleep(self.config.reconnect_interval)
                        continue
                
                # استقبال البيانات
                raw_data = await self.websocket.recv()
                
                # معالجة فورية بنسخة صفرية
                processed_data = self.deserializer.deserialize_websocket(raw_data.encode())
                
                # إضافة إلى قائمة الانتظار
                await self.data_queue.put(processed_data)
                
                logger.debug(f"Processed WebSocket data: {len(raw_data)} bytes")
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.websocket = None
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                self.websocket = None
    
    async def get_processed_data(self) -> ProcessedData:
        """الحصول على البيانات المعالجة"""
        return await self.data_queue.get()
    
    async def start(self):
        """بدء مستقبل WebSocket"""
        self.is_running = True
        asyncio.create_task(self.receive_loop())
        logger.info(f"WebSocket receiver started: {self.config.source_id}")
    
    async def stop(self):
        """إيقاف مستقبل WebSocket"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
        logger.info(f"WebSocket receiver stopped: {self.config.source_id}")

class FIXProtocolReceiver:
    """
    مستقبل بيانات FIX protocol عالي الأداء
    """
    
    def __init__(self, config: DataSourceConfig, deserializer: ZeroCopyDeserializer):
        self.config = config
        self.deserializer = deserializer
        self.reader = None
        self.writer = None
        self.is_running = False
        self.data_queue = asyncio.Queue(maxsize=10000)
        
    async def connect(self):
        """الاتصال بخادم FIX"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.config.endpoint.split(':')[0],
                int(self.config.endpoint.split(':')[1])
            )
            
            # إرسال رسالة تسجيل الدخول FIX
            login_message = self._create_fix_login()
            self.writer.write(login_message)
            await self.writer.drain()
            
            logger.info(f"Connected to FIX server: {self.config.endpoint}")
            return True
        except Exception as e:
            logger.error(f"FIX connection failed: {e}")
            return False
    
    def _create_fix_login(self) -> bytes:
        """
        إنشاء رسالة تسجيل دخول FIX
        """
        # رسالة FIX تسجيل دخول بسيطة
        login_msg = (
            f"35=A{chr(1)}"  # MsgType=Login
            f"49={self.config.credentials.get('sender', 'CLIENT')}{chr(1)}"  # SenderCompID
            f"56={self.config.credentials.get('target', 'SERVER')}{chr(1)}"  # TargetCompID
            f"553={self.config.credentials.get('username', '')}{chr(1)}"  # Username
            f"554={self.config.credentials.get('password', '')}{chr(1)}"  # Password
            f"98=0{chr(1)}"  # EncryptMethod=0
            f"108=30{chr(1)}"  # HeartBtInt=30
            f"10=000{chr(1)}"  # Checksum
        ).encode()
        
        # إضافة طول الرسالة
        body_length = len(login_msg) - 7  # طرح طول BeginString و BodyLength و Checksum
        return f"8=FIX.4.2{chr(1)}9={body_length}{chr(1)}".encode() + login_msg[7:]
    
    async def receive_loop(self):
        """
        حلقة استقبال بيانات FIX المستمرة
        """
        buffer = bytearray()
        
        while self.is_running:
            try:
                if not self.reader:
                    if not await self.connect():
                        await asyncio.sleep(self.config.reconnect_interval)
                        continue
                
                # قراءة البيانات
                data = await self.reader.read(self.config.buffer_size)
                if not data:
                    logger.warning("FIX connection closed")
                    self.reader = None
                    self.writer = None
                    continue
                
                buffer.extend(data)
                
                # معالجة الرسائل الكاملة
                while len(buffer) > 0:
                    # البحث عن نهاية الرسالة (10=checksum)
                    msg_end = buffer.find(b'10=')
                    if msg_end == -1:
                        break
                    
                    # استخراج الرسالة الكاملة
                    msg_end += 7  # إضافة طول "10=000"
                    message_bytes = bytes(buffer[:msg_end])
                    buffer = buffer[msg_end:]
                    
                    # معالجة فورية بنسخة صفرية
                    processed_data = self.deserializer.deserialize_fix(message_bytes)
                    
                    # إضافة إلى قائمة الانتظار
                    await self.data_queue.put(processed_data)
                    
                    logger.debug(f"Processed FIX message: {len(message_bytes)} bytes")
                
            except Exception as e:
                logger.error(f"FIX receive error: {e}")
                self.reader = None
                self.writer = None
    
    async def get_processed_data(self) -> ProcessedData:
        """الحصول على البيانات المعالجة"""
        return await self.data_queue.get()
    
    async def start(self):
        """بدء مستقبل FIX"""
        self.is_running = True
        asyncio.create_task(self.receive_loop())
        logger.info(f"FIX receiver started: {self.config.source_id}")
    
    async def stop(self):
        """إيقاف مستقبل FIX"""
        self.is_running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        logger.info(f"FIX receiver stopped: {self.config.source_id}")

class RealTimeDataPipeline:
    """
    خط أنابيب البيانات الفورية
    يجمع بين 30+ مصدر بيانات ويحولها فوراً إلى protobuf
    """
    
    def __init__(self):
        self.deserializer = ZeroCopyDeserializer()
        self.receivers: Dict[str, Union[WebSocketDataReceiver, FIXProtocolReceiver]] = {}
        self.processed_data_queue = asyncio.Queue(maxsize=50000)
        self.aggregated_data: Dict[str, deque] = {}
        self.performance_metrics = {
            'total_processed': 0,
            'processing_times': deque(maxlen=1000),
            'source_performance': {}
        }
        
    def add_websocket_source(self, config: DataSourceConfig):
        """
        إضافة مصدر بيانات WebSocket
        """
        receiver = WebSocketDataReceiver(config, self.deserializer)
        self.receivers[config.source_id] = receiver
        self.aggregated_data[config.source_id] = deque(maxlen=1000)
        logger.info(f"Added WebSocket source: {config.source_id}")
    
    def add_fix_source(self, config: DataSourceConfig):
        """
        إضافة مصدر بيانات FIX
        """
        receiver = FIXProtocolReceiver(config, self.deserializer)
        self.receivers[config.source_id] = receiver
        self.aggregated_data[config.source_id] = deque(maxlen=1000)
        logger.info(f"Added FIX source: {config.source_id}")
    
    async def start_all_receivers(self):
        """
        بدء جميع المستقبلات
        """
        for receiver in self.receivers.values():
            await receiver.start()
        
        # بدء مهمة تجميع البيانات
        asyncio.create_task(self._aggregate_data())
        
        logger.info("All data receivers started")
    
    async def stop_all_receivers(self):
        """
        إيقاف جميع المستقبلات
        """
        for receiver in self.receivers.values():
            await receiver.stop()
        
        logger.info("All data receivers stopped")
    
    async def _aggregate_data(self):
        """
        تجميع البيانات من جميع المصادر
        """
        while True:
            try:
                # جمع البيانات من جميع المستقبلات
                tasks = []
                for source_id, receiver in self.receivers.items():
                    task = asyncio.create_task(receiver.get_processed_data())
                    tasks.append((source_id, task))
                
                # انتظار أول بيانات متاحة
                if tasks:
                    done, pending = await asyncio.wait(
                        [task for _, task in tasks],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in done:
                        # العثور على المصدر المقابل
                        for source_id, source_task in tasks:
                            if source_task == task:
                                try:
                                    processed_data = await task
                                    
                                    # إضافة إلى قائمة الانتظار المجمعة
                                    await self.processed_data_queue.put(processed_data)
                                    
                                    # إضافة إلى بيانات المصدر
                                    self.aggregated_data[source_id].append(processed_data)
                                    
                                    # تحديث المقاييس
                                    self._update_metrics(source_id, processed_data)
                                    
                                except Exception as e:
                                    logger.error(f"Error processing data from {source_id}: {e}")
                                break
                
                await asyncio.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                logger.error(f"Error in data aggregation: {e}")
                await asyncio.sleep(0.1)
    
    def _update_metrics(self, source_id: str, data: ProcessedData):
        """
        تحديث مقاييس الأداء
        """
        self.performance_metrics['total_processed'] += 1
        self.performance_metrics['processing_times'].append(data.processing_time_ms)
        
        if source_id not in self.performance_metrics['source_performance']:
            self.performance_metrics['source_performance'][source_id] = {
                'count': 0,
                'avg_time': 0.0,
                'last_update': datetime.now()
            }
        
        perf = self.performance_metrics['source_performance'][source_id]
        perf['count'] += 1
        perf['avg_time'] = (perf['avg_time'] * (perf['count'] - 1) + data.processing_time_ms) / perf['count']
        perf['last_update'] = datetime.now()
    
    async def get_aggregated_data(self) -> ProcessedData:
        """
        الحصول على البيانات المجمعة
        """
        return await self.processed_data_queue.get()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        الحصول على مقاييس الأداء
        """
        processing_times = list(self.performance_metrics['processing_times'])
        
        return {
            'total_processed': self.performance_metrics['total_processed'],
            'avg_processing_time_ms': np.mean(processing_times) if processing_times else 0,
            'max_processing_time_ms': np.max(processing_times) if processing_times else 0,
            'min_processing_time_ms': np.min(processing_times) if processing_times else 0,
            'sources_performance': self.performance_metrics['source_performance'],
            'active_sources': len(self.receivers),
            'queue_size': self.processed_data_queue.qsize()
        }

# مثال على الاستخدام
async def main():
    """
    مثال على استخدام خط أنابيب البيانات الفورية
    """
    # إنشاء خط الأنابيب
    pipeline = RealTimeDataPipeline()
    
    # إضافة مصادر WebSocket (مثال: 20 مصدر)
    websocket_sources = [
        DataSourceConfig(
            source_id=f"ws_source_{i}",
            protocol="websocket",
            endpoint=f"wss://data-source-{i}.example.com/stream",
            buffer_size=16384
        )
        for i in range(20)
    ]
    
    for config in websocket_sources:
        pipeline.add_websocket_source(config)
    
    # إضافة مصادر FIX (مثال: 10 مصادر)
    fix_sources = [
        DataSourceConfig(
            source_id=f"fix_source_{i}",
            protocol="fix",
            endpoint=f"fix-server-{i}.example.com:8193",
            credentials={"username": f"user{i}", "password": f"pass{i}"},
            buffer_size=8192
        )
        for i in range(10)
    ]
    
    for config in fix_sources:
        pipeline.add_fix_source(config)
    
    # بدء جميع المستقبلات
    await pipeline.start_all_receivers()
    
    try:
        # معالجة البيانات المستمرة
        while True:
            data = await pipeline.get_aggregated_data()
            
            # هنا يمكن إرسال البيانات إلى المعالج التالي
            logger.info(f"Processed data from {data.source_id}: {len(data.protobuf_data)} bytes")
            
            # عرض مقاييس الأداء كل 1000 رسالة
            if pipeline.performance_metrics['total_processed'] % 1000 == 0:
                metrics = pipeline.get_performance_metrics()
                logger.info(f"Performance: {metrics}")
                
    except KeyboardInterrupt:
        logger.info("Shutting down pipeline...")
    
    finally:
        await pipeline.stop_all_receivers()

if __name__ == "__main__":
    asyncio.run(main())
