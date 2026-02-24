"""
MAIFA v3 Helper Utilities - Common utility functions
Provides shared helper functions across the system
"""

import asyncio
import json
import hashlib
import time
import uuid
import re
import base64
import pickle
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

T = TypeVar('T')

class SerializationHelper:
    """Helper for serialization and deserialization"""
    
    @staticmethod
    def serialize(obj: Any) -> str:
        """Serialize object to JSON string"""
        try:
            if hasattr(obj, '__dict__'):
                return json.dumps(obj.__dict__, default=str)
            return json.dumps(obj, default=str)
        except Exception as e:
            logging.error(f"Serialization failed: {e}")
            return "{}"
    
    @staticmethod
    def deserialize(json_str: str, target_class: type = None) -> Any:
        """Deserialize JSON string to object"""
        try:
            data = json.loads(json_str)
            if target_class and hasattr(target_class, '__annotations__'):
                return target_class(**data)
            return data
        except Exception as e:
            logging.error(f"Deserialization failed: {e}")
            return None
    
    @staticmethod
    def serialize_binary(obj: Any) -> bytes:
        """Serialize object to binary using pickle"""
        try:
            return pickle.dumps(obj)
        except Exception as e:
            logging.error(f"Binary serialization failed: {e}")
            return b""
    
    @staticmethod
    def deserialize_binary(data: bytes) -> Any:
        """Deserialize binary data using pickle"""
        try:
            return pickle.loads(data)
        except Exception as e:
            logging.error(f"Binary deserialization failed: {e}")
            return None

class HashHelper:
    """Helper for hashing operations"""
    
    @staticmethod
    def generate_hash(data: Union[str, bytes, Dict], algorithm: str = "md5") -> str:
        """Generate hash for data"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data, sort_keys=True)
            elif isinstance(data, str):
                data = data.encode('utf-8')
            
            if algorithm == "md5":
                return hashlib.md5(data).hexdigest()
            elif algorithm == "sha1":
                return hashlib.sha1(data).hexdigest()
            elif algorithm == "sha256":
                return hashlib.sha256(data).hexdigest()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
        except Exception as e:
            logging.error(f"Hash generation failed: {e}")
            return ""
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """Generate short random ID"""
        return base64.urlsafe_b64encode(uuid.uuid4().bytes)[:length].decode('ascii')

class TimeHelper:
    """Helper for time operations"""
    
    @staticmethod
    def now_timestamp() -> float:
        """Get current timestamp"""
        return time.time()
    
    @staticmethod
    def now_iso() -> str:
        """Get current time in ISO format"""
        return datetime.now().isoformat()
    
    @staticmethod
    def timestamp_to_iso(timestamp: float) -> str:
        """Convert timestamp to ISO format"""
        return datetime.fromtimestamp(timestamp).isoformat()
    
    @staticmethod
    def iso_to_timestamp(iso_str: str) -> float:
        """Convert ISO string to timestamp"""
        try:
            return datetime.fromisoformat(iso_str.replace('Z', '+00:00')).timestamp()
        except Exception as e:
            logging.error(f"ISO to timestamp conversion failed: {e}")
            return 0.0
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human readable format"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def parse_duration(duration_str: str) -> float:
        """Parse duration string to seconds"""
        try:
            # Handle formats like "1h 30m", "45s", "2.5m"
            total_seconds = 0.0
            
            # Pattern to match number + unit
            pattern = r'(\d+\.?\d*)\s*([smhd])'
            matches = re.findall(pattern, duration_str.lower())
            
            for value, unit in matches:
                value = float(value)
                if unit == 's':
                    total_seconds += value
                elif unit == 'm':
                    total_seconds += value * 60
                elif unit == 'h':
                    total_seconds += value * 3600
                elif unit == 'd':
                    total_seconds += value * 86400
            
            return total_seconds
        except Exception as e:
            logging.error(f"Duration parsing failed: {e}")
            return 0.0
    
    @staticmethod
    def is_expired(timestamp: float, ttl_seconds: int) -> bool:
        """Check if timestamp is expired"""
        return time.time() - timestamp > ttl_seconds

class ValidationHelper:
    """Helper for validation operations"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        """Validate financial symbol format"""
        # Basic validation for stock/crypto symbols
        pattern = r'^[A-Z]{1,5}(-USD)?$'
        return bool(re.match(pattern, symbol.upper()))
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """Sanitize text input"""
        if not text:
            return ""
        
        # Remove potentially harmful characters
        text = re.sub(r'[<>"\']', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    @staticmethod
    def validate_json(json_str: str) -> Tuple[bool, Any]:
        """Validate JSON string"""
        try:
            data = json.loads(json_str)
            return True, data
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate required fields in dictionary"""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields

class FileHelper:
    """Helper for file operations"""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def safe_file_write(file_path: Union[str, Path], content: str, backup: bool = True) -> bool:
        """Safely write file with backup"""
        try:
            file_path = Path(file_path)
            
            # Create backup if requested and file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                file_path.rename(backup_path)
            
            # Write new content
            file_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logging.error(f"File write failed: {e}")
            return False
    
    @staticmethod
    def safe_file_read(file_path: Union[str, Path]) -> Optional[str]:
        """Safely read file"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            return None
        except Exception as e:
            logging.error(f"File read failed: {e}")
            return None
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size in bytes"""
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return 0
    
    @staticmethod
    def list_files(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
        """List files in directory with pattern"""
        try:
            dir_path = Path(directory)
            if dir_path.exists() and dir_path.is_dir():
                return list(dir_path.glob(pattern))
            return []
        except Exception as e:
            logging.error(f"File listing failed: {e}")
            return []

class AsyncHelper:
    """Helper for async operations"""
    
    @staticmethod
    async def run_with_timeout(coro, timeout_seconds: float, default: Any = None) -> Any:
        """Run coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logging.warning(f"Operation timed out after {timeout_seconds}s")
            return default
    
    @staticmethod
    async def gather_with_errors(*coros, return_exceptions: bool = True) -> List[Any]:
        """Gather coroutines with error handling"""
        results = await asyncio.gather(*coros, return_exceptions=return_exceptions)
        
        # Log exceptions if any
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Coroutine {i} failed: {result}")
        
        return results
    
    @staticmethod
    async def retry_async(coro, max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Any:
        """Retry async coroutine with exponential backoff"""
        last_exception = None
        current_delay = delay
        
        for attempt in range(max_attempts):
            try:
                return await coro
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                else:
                    logging.error(f"All {max_attempts} attempts failed: {e}")
        
        raise last_exception
    
    @staticmethod
    async def batch_process(items: List[T], 
                          processor: Callable[[T], Any], 
                          batch_size: int = 10,
                          delay_between_batches: float = 0.1) -> List[Any]:
        """Process items in batches"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[processor(item) for item in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
            
            # Delay between batches
            if i + batch_size < len(items):
                await asyncio.sleep(delay_between_batches)
        
        return results

class DataHelper:
    """Helper for data operations"""
    
    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataHelper.deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        
        for key, value in d.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(DataHelper.flatten_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))
        
        return dict(items)
    
    @staticmethod
    def filter_dict(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """Filter dictionary to only include specified keys"""
        return {key: d[key] for key in keys if key in d}
    
    @staticmethod
    def remove_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values from dictionary"""
        return {key: value for key, value in d.items() if value is not None}
    
    @staticmethod
    def safe_get(data: Any, path: str, default: Any = None) -> Any:
        """Safely get nested value using dot notation"""
        try:
            keys = path.split('.')
            current = data
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif hasattr(current, key):
                    current = getattr(current, key)
                else:
                    return default
            
            return current
        except Exception:
            return default
    
    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

class ConfigHelper:
    """Helper for configuration operations"""
    
    @staticmethod
    def load_config(config_path: Union[str, Path], default_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                content = config_file.read_text(encoding='utf-8')
                config = json.loads(content)
                
                # Merge with default config
                if default_config:
                    return DataHelper.deep_merge(default_config, config)
                
                return config
            else:
                return default_config or {}
        except Exception as e:
            logging.error(f"Config loading failed: {e}")
            return default_config or {}
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: Union[str, Path]) -> bool:
        """Save configuration to file"""
        try:
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            content = json.dumps(config, indent=2, default=str)
            config_file.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logging.error(f"Config saving failed: {e}")
            return False
    
    @staticmethod
    def get_env_var(key: str, default: Any = None, var_type: type = str) -> Any:
        """Get environment variable with type conversion"""
        value = os.getenv(key, default)
        
        if value is None:
            return default
        
        try:
            if var_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            else:
                return var_type(value)
        except ValueError:
            logging.warning(f"Failed to convert env var {key} to {var_type}, using default")
            return default

# Convenience functions for common operations
def generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = {"args": args, "kwargs": kwargs}
    return HashHelper.generate_hash(key_data, "sha256")

def format_bytes(bytes_count: int) -> str:
    """Format bytes in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def is_json_serializable(obj: Any) -> bool:
    """Check if object is JSON serializable"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False

async def measure_time(coro: Callable) -> Tuple[Any, float]:
    """Measure execution time of coroutine"""
    start_time = time.time()
    result = await coro()
    execution_time = time.time() - start_time
    return result, execution_time

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logging.warning(f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"All {max_attempts} attempts failed: {e}")
            
            raise last_exception
        return wrapper
    return decorator
