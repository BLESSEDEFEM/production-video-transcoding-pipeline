"""
Test quality metrics with sample videos
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quality_metrics import QualityMetrics


def test_metrics(reference_video: str, distorted_video: str):
    """
    Test all quality metrics
    """
    print("="*70)
    print("VIDEO QUALITY METRICS TEST")
    print("="*70)
    
    metrics_service = QualityMetrics()
    
    # Test all metrics
    results = metrics_service.compare_videos(
        reference_video,
        distorted_video,
        metrics=['psnr', 'ssim', 'vmaf']
    )
    
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    for metric_name, metric_data in results['metrics'].items():
        if 'error' not in metric_data:
            print(f"\n{metric_data['metric']}:")
            print(f"score: {metric_data['score']} {metric_data['unit']}")
            print(f"quality: {metric_data['quality']}")
            print(f"interpretation: {metric_data['interpretation']}")
        else:
            print(f"\n{metric_name.upper()}: ❌ {metric_data['error']}")
            
    print("\n" + "="*70)
    

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_quality_metrics.py <reference_video> <distorted_video>")
        print("\nExample:")
        print("  python test_quality_metrics.py original.mp4 compressed.mp4")
        sys.exit(1)
        
    test_metrics(sys.argv[1], sys.argv[2])