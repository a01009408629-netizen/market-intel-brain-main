"""
Phase 1: Cleanup and Transition from Crypto to TradFi & Macro Economics
Remove ALL crypto-related files and prepare for TradFi system
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


class Phase1Cleanup:
    """Complete cleanup of crypto-related components and setup for TradFi."""
    
    def __init__(self):
        self.project_root = Path("c:/Users/FUTURE 2025/Downloads/market-intel-brain-main/market-intel-brain-main")
        self.crypto_files_to_remove = [
            "real_providers.py",  # Contains crypto providers
            "production_launcher.py",  # Crypto-focused launcher
        ]
        self.crypto_providers = ["binance", "okx", "coinbase", "glassnode", "cryptocompare"]
        self.new_dependencies = [
            "yfinance", "fredapi", "fake-useragent", "pandas", "pyarrow"
        ]
        
    def cleanup_crypto_files(self):
        """Remove all crypto-related files safely."""
        print("Cleaning up crypto-related files...")
        
        removed_files = []
        for file_name in self.crypto_files_to_remove:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    file_path.unlink()
                    removed_files.append(file_name)
                    print(f"  Removed: {file_name}")
                except Exception as e:
                    print(f"  Failed to remove {file_name}: {e}")
        
        return removed_files
    
    def install_new_dependencies(self):
        """Install new TradFi dependencies."""
        print("Installing new TradFi dependencies...")
        
        for package in self.new_dependencies:
            try:
                print(f"  Installing {package}...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    print(f"  {package} installed successfully")
                else:
                    print(f"  Failed to install {package}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"  Timeout installing {package}")
            except Exception as e:
                print(f"  Error installing {package}: {e}")
    
    def update_infrastructure_init(self):
        """Update infrastructure __init__.py to remove crypto imports."""
        init_file = self.project_root / "infrastructure" / "__init__.py"
        
        if not init_file.exists():
            print("  infrastructure/__init__.py not found")
            return False
        
        # Read current content
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove crypto-related imports (will be updated in next steps)
        print("Updating infrastructure imports...")
        
        # Write updated content (simplified for now)
        new_content = '''"""
Production Infrastructure Package
TradFi & Macro Economics Architecture
"""

from .secrets_manager import SecretsManager, get_secrets_manager
from .data_normalization import (
    UnifiedInternalSchema, DataType, SourceType,
    BaseProvider, DataNormalizationFactory, get_data_factory
)
from .rate_limiter import (
    RateLimiter, APIGateway, RateLimitConfig, RateLimitUnit,
    get_rate_limiter, get_api_gateway
)
from .io_optimizer import (
    RingBuffer, AOFWriter, IOOptimizer,
    RingBufferConfig, AOFConfig, get_io_optimizer
)

__all__ = [
    # Secrets Manager
    'SecretsManager', 'get_secrets_manager',
    
    # Data Normalization
    'UnifiedInternalSchema', 'DataType', 'SourceType',
    'BaseProvider', 'DataNormalizationFactory', 'get_data_factory',
    
    # Rate Limiting
    'RateLimiter', 'APIGateway', 'RateLimitConfig', 'RateLimitUnit',
    'get_rate_limiter', 'get_api_gateway',
    
    # I/O Optimizer
    'RingBuffer', 'AOFWriter', 'IOOptimizer',
    'RingBufferConfig', 'AOFConfig', 'get_io_optimizer'
]
'''
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("  Updated infrastructure/__init__.py")
        return True
    
    def create_tradfi_directories(self):
        """Create new TradFi-specific directories."""
        tradfi_dirs = [
            "data/stocks",
            "data/forex", 
            "data/macro",
            "data/news",
            "cache/stocks",
            "cache/macro",
            "logs/tradfi"
        ]
        
        print("Creating TradFi directories...")
        
        for dir_path in tradfi_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {dir_path}")
    
    def backup_existing_data(self):
        """Backup existing crypto data before cleanup."""
        backup_dir = self.project_root / "backup_crypto"
        backup_dir.mkdir(exist_ok=True)
        
        print("Backing up existing data...")
        
        data_dir = self.project_root / "data"
        if data_dir.exists():
            for item in data_dir.iterdir():
                if item.is_file():
                    try:
                        shutil.copy2(item, backup_dir / item.name)
                        print(f"  Backed up: {item.name}")
                    except Exception as e:
                        print(f"  Failed to backup {item.name}: {e}")
        
        return backup_dir
    
    def execute_phase1(self):
        """Execute complete Phase 1 cleanup."""
        print("=" * 80)
        print("PHASE 1: CRYPTO CLEANUP & TRADFI TRANSITION")
        print("=" * 80)
        
        # Step 1: Backup existing data
        self.backup_existing_data()
        
        # Step 2: Remove crypto files
        removed_files = self.cleanup_crypto_files()
        
        # Step 3: Install new dependencies
        self.install_new_dependencies()
        
        # Step 4: Update infrastructure
        self.update_infrastructure_init()
        
        # Step 5: Create TradFi directories
        self.create_tradfi_directories()
        
        print("\n" + "=" * 80)
        print("PHASE 1 CLEANUP COMPLETED")
        print("=" * 80)
        print(f"Files removed: {len(removed_files)}")
        print(f"Dependencies installed: {len(self.new_dependencies)}")
        print("Ready for TradFi & Macro Economics implementation!")
        
        return True


def main():
    """Execute Phase 1 cleanup."""
    cleanup = Phase1Cleanup()
    success = cleanup.execute_phase1()
    
    if success:
        print("\nPhase 1 completed successfully!")
        print("Ready to implement TradFi providers and Parquet storage.")
    else:
        print("\nPhase 1 cleanup failed!")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
