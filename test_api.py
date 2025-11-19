#!/usr/bin/env python3
"""
Test script for ECG Processing Service API.
"""
import requests
import json
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_analyze(file_path, duration=20, channels="CH2,CH3,CH4", include_signals=False):
    """Test analyze endpoint with a file."""
    print(f"Testing /analyze endpoint with {file_path}...")
    
    if not Path(file_path).exists():
        print(f"Error: File {file_path} not found")
        return
    
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f, 'text/plain')}
        data = {
            'duration': duration,
            'channels': channels,
            'include_signals': str(include_signals).lower(),
            'sampling_rate': 500
        }
        
        response = requests.post(f"{API_URL}/analyze", files=files, data=data)
        
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n=== METADATA ===")
        print(json.dumps(result['metadata'], indent=2))
        print("\n=== STATISTICS ===")
        print(json.dumps(result['statistics'], indent=2))
        
        if include_signals:
            print("\n=== SIGNAL DATA ===")
            print(f"Raw signal points: {len(result['raw_signal']['time']) if result.get('raw_signal') else 0}")
            print(f"Cleaned signal points: {len(result['cleaned_signal']['time']) if result.get('cleaned_signal') else 0}")
            print(f"R-peaks: {len(result['r_peak_times']) if result.get('r_peak_times') else 0}")
    else:
        print(f"Error: {response.text}")
    print()

if __name__ == "__main__":
    # Test health endpoint
    test_health()
    
    # Test analyze endpoint
    # Update this path to point to an actual ECG data file
    test_file = "../ecg-webapp/public/Readings 2025-11-12 Zorye post run/Device_0_Volts.txt"
    
    if Path(test_file).exists():
        print("=" * 80)
        print("Testing with ECG file (without signals)")
        print("=" * 80)
        test_analyze(test_file, duration=20, include_signals=False)
        
        print("=" * 80)
        print("Testing with ECG file (with signals)")
        print("=" * 80)
        test_analyze(test_file, duration=5, include_signals=True)
    else:
        print(f"Sample file not found: {test_file}")
        print("Please update the test_file path in the script.")
