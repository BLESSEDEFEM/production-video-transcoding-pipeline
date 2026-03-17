"""
Test report generation with VideoValidator
"""
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_validator import VideoValidator
from app.services.report_generator import ReportGenerator


def test_report_generation(video_path: str):
    """Test complete report generation"""
    
    print("="*70)
    print("REPORT GENERATION TEST")
    print("="*70)
    
    # Run validation
    validator = VideoValidator()
    is_valid, checks = validator.validate(video_path)
    
    print("\n" + "="*70)
    print("GENERATING STRUCTURED REPORT")
    print("="*70)
    
    # Get video info for report
    video_path_obj = Path(video_path)
    
    # Create mock video_info (simplified version)
    # In production, this would come from validator
    video_info = {
        'codec_name': 'h264',
        'width': 1920,
        'height': 1080,
        'r_frame_rate': '30/1',
        'bit_rate': '5000000',
        'duration': '120.5'
    }
    
    audio_info = {
        'codec_name': 'aac',
        'bit_rate': '128000',
        'sample_rate': '48000'
    }
    
    # Convert checks to issues format
    issues = []
    for check in checks:
        if not check.passed:
            issues.append({
                'severity': 'reject' if check.level.value == 'reject' else 'warn',
                'category': check.name.split('_')[0] if '_' in check.name else check.name,
                'message': check.message,
                'details': {}
            })
    
    # Generate report
    report_generator = ReportGenerator()
    report = report_generator.generate_report(
        filename=video_path_obj.name,
        file_path=str(video_path_obj),
        file_size=video_path_obj.stat().st_size,
        video_info=video_info,
        audio_info=audio_info,
        issues=issues,
        frame_analysis=None
    )
    
    # Display JSON report
    print("\n📄 JSON REPORT:")
    print(json.dumps(report, indent=2, default=str))
    
    # Generate human-readable version
    text_report = report_generator.generate_human_readable_report(report)
    
    print("\n📝 HUMAN-READABLE REPORT:")
    print(text_report)
    
    # Save both versions
    json_file = "inspection_report.json"
    text_file = "inspection_report.txt"

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_report)

    print(f"\n✅ Reports saved:")
    print(f"  JSON: {json_file}")
    print(f"  Text: {text_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_report_generation.py <video_path>")
        sys.exit(1)
    
    test_report_generation(sys.argv[1])