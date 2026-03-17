"""
Test inspection module
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.inspection.metadata import MetadataExtractor
from app.inspection.validator import VideoValidator
from app.inspection.rules import ValidationRules


def test_inspection(video_path: str):
    """Test complete inspection pipeline"""
    
    print("="*70)
    print("VIDEO INSPECTION TEST")
    print("="*70)
    
    # Step 1: Extract metadata
    print("\n📊 STEP 1: Extract Metadata")
    print("-"*70)
    
    extractor = MetadataExtractor()
    metadata = extractor.extract(video_path)
    
    if 'error' in metadata:
        print(f"\n❌ Extraction failed: {metadata['error']}")
        return
    
    extractor.print_metadata(metadata)
    
    # Step 2: Validate
    print("\n🔍 STEP 2: Validate")
    print("-"*70)
    
    validator = VideoValidator()
    result = validator.validate(metadata)
    
    # Step 3: Get report
    print("\n📋 STEP 3: Generate Report")
    print("-"*70)
    
    summary = result.get_summary()
    
    print(f"\nFinal Verdict: {'✅ PASS' if summary['valid'] else '❌ FAIL'}")
    print(f"Can process: {summary['valid']}")
    
    if not summary['valid']:
        print(f"\nRejection reasons:")
        for error in summary['errors']:
            print(f"  • {error}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_inspection.py <video_path>")
        print("\nExample:")
        print("  python test_inspection.py storage/uploads/video.mp4")
        sys.exit(1)
    
    test_inspection(sys.argv[1])