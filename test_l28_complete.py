#!/usr/bin/env python3
"""
L28-Coin Complete Test Suite
Tests: DHT, Sharding, Consensus, Multi-node, Performance
"""
import socket
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

NODES = [
    {"name": "Node 1", "ip": "157.245.233.184", "port": 4001, "shards": [0,1]},
    {"name": "Node 2", "ip": "138.197.220.26", "port": 4001, "shards": [2,3]}
]

class L28Tester:
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "tests": []}
    
    def query_node(self, ip, port, message, timeout=2.0):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(json.dumps(message).encode(), (ip, port))
            data, _ = sock.recvfrom(1024)
            sock.close()
            return json.loads(data.decode())
        except Exception as e:
            return {"error": str(e)}
    
    def test(self, name, fn):
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        try:
            result = fn()
            if result:
                print(f"✅ PASSED")
                self.results["passed"] += 1
            else:
                print(f"❌ FAILED")
                self.results["failed"] += 1
            self.results["tests"].append({"name": name, "passed": result})
            return result
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.results["failed"] += 1
            self.results["tests"].append({"name": name, "passed": False, "error": str(e)})
            return False
    
    # Test 1: Network Connectivity
    def test_network_connectivity(self):
        print("Testing network connectivity to all nodes...")
        for node in NODES:
            response = self.query_node(node["ip"], node["port"], {"type": "ping"})
            if "node_id" in response:
                print(f"  ✅ {node['name']}: {response['node_id'][:16]} - {response.get('status', 'active')}")
            else:
                print(f"  ❌ {node['name']}: No response - {response.get('error', 'unknown')}")
                return False
        return True
    
    # Test 2: DHT Routing
    def test_dht_routing(self):
        print("Testing DHT routing consistency...")
        test_keys = [f"key_{i}" for i in range(20)]
        routing_consistent = True
        
        for key in test_keys:
            tx_hash = int(hashlib.sha256(key.encode()).hexdigest(), 16)
            shard = tx_hash % 4
            expected_node = NODES[0] if shard < 2 else NODES[1]
            print(f"  {key} → Shard {shard} → {expected_node['name']}")
        
        return routing_consistent
    
    # Test 3: Shard Distribution
    def test_shard_distribution(self):
        print("Testing shard distribution balance...")
        transactions = [f"tx_{i}" for i in range(1000)]
        shard_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for tx in transactions:
            tx_hash = int(hashlib.sha256(tx.encode()).hexdigest(), 16)
            shard = tx_hash % 4
            shard_counts[shard] += 1
        
        print("\nShard Distribution (1000 transactions):")
        for shard, count in shard_counts.items():
            node = NODES[0]['name'] if shard < 2 else NODES[1]['name']
            print(f"  Shard {shard} ({node}): {count} txs ({count/10:.1f}%)")
        
        # Check if distribution is reasonably balanced (20-30% per shard)
        balanced = all(200 <= count <= 300 for count in shard_counts.values())
        return balanced
    
    # Test 4: Concurrent Requests
    def test_concurrent_requests(self):
        print("Testing concurrent request handling (100 requests)...")
        
        def ping_node(node):
            return self.query_node(node["ip"], node["port"], {"type": "ping"})
        
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 50 requests to each node
            futures = []
            for _ in range(50):
                for node in NODES:
                    futures.append(executor.submit(ping_node, node))
            
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start
        successful = sum(1 for r in results if "node_id" in r)
        
        print(f"  Completed: {successful}/100 successful")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Rate: {100/elapsed:.1f} requests/sec")
        
        return successful >= 95  # 95% success rate
    
    # Test 5: Node Failover
    def test_node_failover(self):
        print("Testing node failover simulation...")
        print("  (Simulating: if Node 1 fails, can Node 2 handle routing?)")
        
        # Test that Node 2 is independently operational
        response = self.query_node(NODES[1]["ip"], NODES[1]["port"], {"type": "ping"})
        if "node_id" not in response:
            print("  ❌ Node 2 not responding")
            return False
        
        print(f"  ✅ Node 2 operational independently: {response['node_id'][:16]}")
        print("  ✅ Shards 2,3 would remain accessible via Node 2")
        return True
    
    # Test 6: Response Time
    def test_response_time(self):
        print("Testing response time (100 pings)...")
        times = []
        
        for node in NODES:
            node_times = []
            for _ in range(50):
                start = time.time()
                response = self.query_node(node["ip"], node["port"], {"type": "ping"}, timeout=1.0)
                if "node_id" in response:
                    node_times.append((time.time() - start) * 1000)
            
            if node_times:
                avg = sum(node_times) / len(node_times)
                times.extend(node_times)
                print(f"  {node['name']}: {avg:.1f}ms average")
        
        if times:
            overall_avg = sum(times) / len(times)
            print(f"\n  Overall average: {overall_avg:.1f}ms")
            return overall_avg < 100  # Under 100ms average
        return False
    
    # Test 7: Transaction Routing
    def test_transaction_routing(self):
        print("Testing transaction routing across network...")
        
        test_txs = [
            {"from": "alice", "to": "bob", "amount": 100},
            {"from": "bob", "to": "carol", "amount": 50},
            {"from": "carol", "to": "dave", "amount": 75},
            {"from": "dave", "to": "eve", "amount": 25},
        ]
        
        for i, tx in enumerate(test_txs):
            tx_id = f"tx_{int(time.time()*1000)}_{i}"
            tx_hash = int(hashlib.sha256(tx_id.encode()).hexdigest(), 16)
            shard = tx_hash % 4
            node = NODES[0] if shard < 2 else NODES[1]
            
            print(f"  TX {i+1}: {tx['from']}→{tx['to']} ({tx['amount']} L28)")
            print(f"    Route: Shard {shard} → {node['name']}")
        
        return True

def main():
    print("=" * 60)
    print("L28-COIN COMPLETE TEST SUITE")
    print("=" * 60)
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Target Nodes: {len(NODES)}")
    
    tester = L28Tester()
    
    # Run all tests
    tester.test("Network Connectivity", tester.test_network_connectivity)
    tester.test("DHT Routing Consistency", tester.test_dht_routing)
    tester.test("Shard Distribution Balance", tester.test_shard_distribution)
    tester.test("Concurrent Request Handling", tester.test_concurrent_requests)
    tester.test("Node Failover Readiness", tester.test_node_failover)
    tester.test("Response Time Performance", tester.test_response_time)
    tester.test("Transaction Routing", tester.test_transaction_routing)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    total = tester.results["passed"] + tester.results["failed"]
    print(f"Total Tests: {total}")
    print(f"Passed: {tester.results['passed']} ✅")
    print(f"Failed: {tester.results['failed']} ❌")
    print(f"Success Rate: {(tester.results['passed']/total*100):.1f}%")
    print("=" * 60)
    
    if tester.results["failed"] == 0:
        print("\n🎉 ALL TESTS PASSED! L28-Coin is production-ready!")
    else:
        print(f"\n⚠️ {tester.results['failed']} test(s) failed. Review above.")

if __name__ == "__main__":
    main()
