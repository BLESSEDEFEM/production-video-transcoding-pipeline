"""
Test complete validation pipeline
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_validator import VideoValidator


def test_validation(video_path: str):
    """Test complete validation"""
    
    validator = VideoValidator()
    is_valid, checks = validator.validate(video_path)
    
    # Display detailed results
    print("\n📊 DETAILED RESULTS:\n")
    
    for check in checks:
        icon = "✅" if check.passed else ("❌" if check.level.value == "reject" else "⚠️")
        print(f"{icon} {check.name}: {check.message}")
        if check.details:
            print(f"   Details: {check.details}")
    
    print(f"\n{'='*70}")
    print(f"FINAL VERDICT: {'✅ PASS' if is_valid else '❌ FAIL'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_validator.py <video_path>")
        sys.exit(1)
    
    test_validation(sys.argv[1])