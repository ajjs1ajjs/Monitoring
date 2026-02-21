#!/usr/bin/env python
import sys
sys.path.insert(0, '.')

print("Step 1: Importing models...")
from pymon.metrics import models
print("Models imported successfully")

print("\nStep 2: Importing collector...")
from pymon.metrics import collector
print("Collector imported successfully")

print("\nStep 3: Creating Counter...")
c = collector.Counter('test', 'Test')
print("Counter created successfully")

print("\nStep 4: Incrementing counter...")
c.inc()
print("Counter incremented successfully")

print("\nStep 5: Getting metric...")
metric = collector.registry.get_metric('test')
print(f"Metric: {metric}")

print("\nAll steps completed!")