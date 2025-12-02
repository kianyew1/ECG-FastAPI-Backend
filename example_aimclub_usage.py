"""
Simple example: Using AimClub ECG with your 8-channel data.
"""
from app.services.aimclub_ecg_service import AimClubECGService, is_aimclub_available
import json

# Check if library is available
if not is_aimclub_available():
    print("Please install aimclub ECG library first:")
    print("  pip install git+https://github.com/aimclub/ECG.git")
    exit(1)

# Initialize service
service = AimClubECGService(sampling_rate=500)

# Analyze your ECG file
print("Analyzing ECG data...")
results = service.analyze_ecg_complete(
    filepath='Device_1_Volts.txt',
    duration=10.0,  # Analyze first 10 seconds
    include_nn_analysis=True  # Include neural network analysis
)

# Display key findings
print("\n" + "="*60)
print("ECG ANALYSIS RESULTS")
print("="*60)

# Signal info
info = results['signal_info']
print(f"\n📊 Signal: {info['duration_seconds']:.1f}s, {info['samples']} samples")

# ST-Elevation
st = results['st_elevation_classic']
print(f"\n🔍 ST-Elevation: {st['st_elevation_detected']}")
print(f"   {st['explanation']}")

# Risk markers
risk = results['risk_markers']
if risk['success']:
    print(f"\n⚠️  Risk Markers:")
    print(f"   QTc: {risk['QTc_ms']:.1f} ms")
    print(f"   RA_V4: {risk['RA_V4_mv']:.3f} mV")

# Diagnosis
diag = results['diagnosis_risk_markers']
print(f"\n💊 Diagnosis: {diag['diagnosis']}")
print(f"   {diag['explanation']}")

# Save full results
with open('aimclub_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\n✓ Full results saved to aimclub_results.json")
