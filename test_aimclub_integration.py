"""
Test script for AimClub ECG integration.
Demonstrates how to use the aimclub ECG library with 8-channel data.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.aimclub_ecg_service import AimClubECGService, is_aimclub_available


def test_aimclub_service():
    """Test aimclub ECG service with Device_1_Volts.txt"""
    
    print("=" * 60)
    print("AimClub ECG Library Integration Test")
    print("=" * 60)
    
    # Check if library is available
    if not is_aimclub_available():
        print("\n❌ AimClub ECG library not installed!")
        print("\nTo install, run:")
        print("  pip install git+https://github.com/aimclub/ECG.git")
        print("  pip install torch opencv-python grad-cam pillow")
        return False
    
    print("\n✓ AimClub ECG library is installed")
    
    # Initialize service
    try:
        service = AimClubECGService(sampling_rate=500)
        print("✓ Service initialized with 500 Hz sampling rate")
    except Exception as e:
        print(f"\n❌ Failed to initialize service: {e}")
        return False
    
    # Test file path
    data_file = Path(__file__).parent / "Device_1_Volts.txt"
    
    if not data_file.exists():
        print(f"\n❌ Test data file not found: {data_file}")
        return False
    
    print(f"✓ Found test data file: {data_file.name}")
    
    # Load and convert data
    print("\n" + "-" * 60)
    print("Loading 8-channel data...")
    try:
        ecg_8ch, metadata = service.load_8channel_file(str(data_file), duration=10.0)
        print(f"✓ Loaded {ecg_8ch.shape[1]} samples from {ecg_8ch.shape[0]} channels")
        print(f"  Duration: {ecg_8ch.shape[1] / 500:.2f} seconds")
        if metadata:
            print(f"  Metadata: {metadata}")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return False
    
    # Convert to 12-lead
    print("\n" + "-" * 60)
    print("Converting to 12-lead format...")
    try:
        ecg_12_lead = service.convert_8ch_to_12lead(ecg_8ch)
        print(f"✓ Converted to 12-lead format: {ecg_12_lead.shape}")
        print("  Mapping: Leads 0-7 = CH1-8, Leads 8-11 = duplicated CH5-8")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False
    
    # Run complete analysis
    print("\n" + "-" * 60)
    print("Running complete ECG analysis...")
    print("(This may take a minute...)")
    
    try:
        results = service.analyze_ecg_complete(
            str(data_file),
            duration=10.0,
            include_nn_analysis=True
        )
        
        if not results['success']:
            print(f"❌ Analysis failed: {results.get('error')}")
            return False
        
        print("\n✓ Analysis complete!")
        
        # Display results
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        
        # Signal info
        print("\n📊 Signal Information:")
        info = results['signal_info']
        print(f"  Original channels: {info['original_channels']}")
        print(f"  Converted leads: {info['converted_leads']}")
        print(f"  Samples: {info['samples']}")
        print(f"  Duration: {info['duration_seconds']:.2f} seconds")
        print(f"  Sampling rate: {info['sampling_rate']} Hz")
        
        # ST-Elevation (Classic)
        print("\n🔍 ST-Elevation Detection (Classic CV):")
        st_classic = results['st_elevation_classic']
        if st_classic['success']:
            print(f"  Status: {st_classic['st_elevation_detected']}")
            print(f"  Explanation: {st_classic['explanation']}")
        else:
            print(f"  ❌ Failed: {st_classic.get('error')}")
        
        # ST-Elevation (Neural Network)
        if 'st_elevation_nn' in results:
            print("\n🤖 ST-Elevation Detection (Neural Network):")
            st_nn = results['st_elevation_nn']
            if st_nn['success']:
                print(f"  Status: {st_nn['st_elevation_detected']}")
                print(f"  Explanation: {st_nn['explanation']}")
                if st_nn.get('has_gradcam'):
                    print("  ✓ GradCAM visualization available")
            else:
                print(f"  ❌ Failed: {st_nn.get('error')}")
        
        # Risk Markers
        print("\n⚠️  Risk Markers:")
        risk = results['risk_markers']
        if risk['success']:
            print(f"  QTc: {risk['QTc_ms']:.2f} ms")
            print(f"  RA_V4: {risk['RA_V4_mv']:.4f} mV")
            print(f"  STE60_V3: {risk['STE60_V3_mv']:.4f} mV")
        else:
            print(f"  ❌ Failed: {risk.get('error')}")
        
        # Diagnosis (Risk Markers)
        print("\n💊 Differential Diagnosis (Risk Markers):")
        diag = results['diagnosis_risk_markers']
        if diag['success']:
            print(f"  Diagnosis: {diag['diagnosis']}")
            print(f"  Explanation: {diag['explanation']}")
        else:
            print(f"  ❌ Failed: {diag.get('error')}")
        
        # Diagnosis (Neural Network)
        if 'diagnosis_nn' in results:
            print("\n🤖 Differential Diagnosis (Neural Network):")
            diag_nn = results['diagnosis_nn']
            if diag_nn['success']:
                if 'ber_detected' in diag_nn:
                    print(f"  BER Detected: {diag_nn['ber_detected']}")
                    print(f"  BER Explanation: {diag_nn['ber_explanation']}")
                if 'mi_detected' in diag_nn:
                    print(f"  MI Detected: {diag_nn['mi_detected']}")
                    print(f"  MI Explanation: {diag_nn['mi_explanation']}")
            else:
                print(f"  ❌ Failed: {diag_nn.get('error')}")
        
        # QRS Complex
        print("\n💓 QRS Complex Detection:")
        qrs = results['qrs_complex']
        if qrs['success']:
            print(f"  Channels analyzed: {qrs['qrs_peaks_detected']}")
            if qrs['peaks_summary']:
                first_channel = qrs['peaks_summary'][0]
                print(f"  Sample (Channel {first_channel['channel']}):")
                for wave, data in first_channel['waves'].items():
                    print(f"    {wave}-wave: {data['count']} peaks detected")
        else:
            print(f"  ❌ Failed: {qrs.get('error')}")
        
        print("\n" + "=" * 60)
        print("✓ Test completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_aimclub_service()
    sys.exit(0 if success else 1)
