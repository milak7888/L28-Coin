#!/usr/bin/env python3
"""
L28 Safe Ledger Operations
File locking, atomic writes, corruption prevention
"""
import fcntl
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional
from contextlib import contextmanager


class SafeLedger:
    """Thread-safe, process-safe ledger operations"""
    
    def __init__(self, ledger_path: str):
        self.ledger_path = Path(ledger_path)
        self.lock_path = Path(str(ledger_path) + '.lock')
        
    @contextmanager
    def write_lock(self, timeout: int = 30):
        """
        Acquire exclusive write lock
        Prevents multiple miners from corrupting ledger
        """
        lock_fd = None
        try:
            # Create lock file
            lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
            
            # Try to acquire exclusive lock
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(f"⏳ Waiting for ledger lock...")
                fcntl.flock(lock_fd, fcntl.LOCK_EX)  # Wait
            
            yield
            
        finally:
            if lock_fd is not None:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
    
    def append_entry_safe(self, entry: Dict) -> bool:
        """
        Atomically append entry to ledger
        Uses temp file + rename for atomicity
        """
        with self.write_lock():
            try:
                # Write to temp file first
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.ledger_path.parent,
                    prefix='.l28_temp_'
                )
                
                try:
                    # Copy existing ledger
                    if self.ledger_path.exists():
                        shutil.copy2(self.ledger_path, temp_path)
                    
                    # Append new entry
                    with os.fdopen(temp_fd, 'a') as f:
                        f.write(json.dumps(entry) + '\n')
                    
                    # Atomic rename
                    os.replace(temp_path, self.ledger_path)
                    return True
                    
                except Exception as e:
                    # Cleanup temp file on error
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                    raise e
                    
            except Exception as e:
                print(f"❌ Failed to append entry: {e}")
                return False
    
    def verify_integrity(self) -> Dict[str, any]:
        """
        Verify ledger integrity
        Checks hash chain, duplicate heights, etc.
        """
        results = {
            'valid': True,
            'total_entries': 0,
            'hash_chain_intact': True,
            'duplicate_heights': [],
            'broken_links': [],
            'errors': []
        }
        
        if not self.ledger_path.exists():
            results['valid'] = False
            results['errors'].append('Ledger file not found')
            return results
        
        prev_hash = None
        heights_seen = set()
        
        try:
            with open(self.ledger_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                        results['total_entries'] += 1
                        
                        height = entry.get('entry_height')
                        current_hash = entry.get('hash')
                        entry_prev = entry.get('prev')
                        
                        # Check for duplicate heights
                        if height in heights_seen:
                            results['duplicate_heights'].append(height)
                            results['valid'] = False
                        heights_seen.add(height)
                        
                        # Verify hash chain (skip genesis)
                        if prev_hash is not None:
                            if entry_prev != prev_hash:
                                results['broken_links'].append({
                                    'height': height,
                                    'expected': prev_hash,
                                    'got': entry_prev
                                })
                                results['hash_chain_intact'] = False
                                results['valid'] = False
                        
                        prev_hash = current_hash
                        
                    except json.JSONDecodeError:
                        results['errors'].append(f'Invalid JSON at line {line_num}')
                        results['valid'] = False
                        
        except Exception as e:
            results['errors'].append(f'Error reading ledger: {e}')
            results['valid'] = False
        
        return results
    
    def create_backup(self, backup_dir: Optional[str] = None) -> str:
        """Create timestamped backup of ledger"""
        import datetime
        
        if backup_dir is None:
            backup_dir = self.ledger_path.parent / 'backups'
        else:
            backup_dir = Path(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"l28_ledger_{timestamp}.jsonl"
        backup_path = backup_dir / backup_name
        
        with self.write_lock():
            shutil.copy2(self.ledger_path, backup_path)
        
        return str(backup_path)
    
    def rollback_to_height(self, target_height: int) -> bool:
        """
        Rollback ledger to specific height
        Creates backup first
        """
        # Create backup
        backup_path = self.create_backup()
        print(f"📦 Backup created: {backup_path}")
        
        with self.write_lock():
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.ledger_path.parent,
                prefix='.l28_rollback_'
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as temp_f:
                    with open(self.ledger_path, 'r') as ledger_f:
                        for line in ledger_f:
                            if not line.strip():
                                continue
                            
                            entry = json.loads(line)
                            if entry['entry_height'] <= target_height:
                                temp_f.write(line)
                            else:
                                break
                
                # Atomic replace
                os.replace(temp_path, self.ledger_path)
                print(f"✅ Rolled back to height {target_height}")
                return True
                
            except Exception as e:
                print(f"❌ Rollback failed: {e}")
                try:
                    os.remove(temp_path)
                except:
                    pass
                return False


def main():
    """CLI for ledger operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="L28 Safe Ledger Operations")
    parser.add_argument('--ledger', required=True, help='Path to ledger file')
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Verify
    subparsers.add_parser('verify', help='Verify ledger integrity')
    
    # Backup
    backup = subparsers.add_parser('backup', help='Create backup')
    backup.add_argument('--dir', help='Backup directory')
    
    # Rollback
    rollback = subparsers.add_parser('rollback', help='Rollback to height')
    rollback.add_argument('height', type=int, help='Target height')
    
    args = parser.parse_args()
    ledger = SafeLedger(args.ledger)
    
    if args.command == 'verify':
        print("🔍 Verifying ledger integrity...")
        results = ledger.verify_integrity()
        
        print(f"\nTotal entries: {results['total_entries']}")
        print(f"Hash chain: {'✅ Intact' if results['hash_chain_intact'] else '❌ Broken'}")
        
        if results['duplicate_heights']:
            print(f"\n⚠️  Duplicate heights found: {len(results['duplicate_heights'])}")
            for h in results['duplicate_heights'][:10]:
                print(f"  - Height {h}")
        
        if results['broken_links']:
            print(f"\n❌ Broken hash links: {len(results['broken_links'])}")
            for link in results['broken_links'][:5]:
                print(f"  - Height {link['height']}")
        
        if results['errors']:
            print(f"\n❌ Errors:")
            for err in results['errors']:
                print(f"  - {err}")
        
        print(f"\nOverall: {'✅ VALID' if results['valid'] else '❌ INVALID'}")
    
    elif args.command == 'backup':
        backup_path = ledger.create_backup(args.dir)
        print(f"✅ Backup created: {backup_path}")
    
    elif args.command == 'rollback':
        ledger.rollback_to_height(args.height)


if __name__ == "__main__":
    main()
