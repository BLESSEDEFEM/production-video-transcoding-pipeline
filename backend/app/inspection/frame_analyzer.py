"""
Frame-Level Analysis
Detects black frames, frozen frames, and other frame issues
"""
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FrameAnalyzer:
    """
    Analyzes video frames for issues
    """
    
    # Thresholds
    MAX_BLACK_PERCENT = 5.0
    WARN_BLACK_PERCENT = 1.0
    MAX_FROZEN_PERCENT = 2.0
    WARN_FROZEN_PERCENT = 0.5
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        self.ffmpeg = ffmpeg_path
        
    def analyze_frames(
        self,
        video_path: str,
        duration: float,
        fps: float = 30.0
    ) -> Dict:
        """
        Complete frame analysis
        
        Args:
            video_path: Path to video
            duration: Video duration in seconds
            fps: Frame rate
            
        Returns:
            Dictionary with all frame analysis results
        """
        print(f"\n🎬 Analyzing frames...")
        
        # Detect black frames
        black_result = self.detect_black_frames(video_path, duration)
        
        # Detect frozen frames
        frozen_result = self.detect_frozen_frames(video_path, duration)
        
        # Combine results
        total_frames = int(duration * fps)
        
        analysis = {
            'total_frames': total_frames,
            'duration': duration,
            'fps': fps,
            'black_frames': black_result,
            'frozen_frames': frozen_result,
            'passed': self._evaluate_results(black_result, frozen_result)
        }
        
        self._print_summary(analysis)
        
        return analysis
    
    def detect_black_frames(
        self,
        video_path: str,
        duration: float,
        black_threshold: float = 0.00,
        min_duration: float = 0.1
    ) -> Dict:
        """
        Detect black frames using FFmpeg blackdetect filter
        
        Args:
            video_path: Path to video
            duration: Video duration
            black_threshold: Pixel threshold (0.00 = pure black)
            min_duration: Minimum black duration to detect (seconds)
        
        Returns:
            Dictionary with black frame detection results
        """
        print(f"  ⬛ Detecting black frames...")
        
        try:
            cmd = [
                self.ffmpeg,
                '-i', video_path,
                '-vf', f'blackdetect=d={min_duration}:pix_th={black_threshold}',
                '-an', # No audio
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse output
            detections = self._parse_black_detections(result.stderr)
            
            # Calculate statistics
            total_black_duration = sum(d['duration'] for d in detections)
            black_percent = (total_black_duration / duration * 100) if duration > 0 else 0
            
            # Determine status
            if black_percent > self.MAX_BLACK_PERCENT:
                status = 'FAIL'
            elif black_percent > self.WARN_BLACK_PERCENT:
                status = 'WARN'
            else:
                status = 'PASS'
                
            print(f"      Found {len(detections)} black section(s)")
            print(f"      Total black duration: {total_black_duration:.2f}s ({black_percent:.2f}%)")
            print(f"      Status: {status}")
            
            return {
                'detections': detections,
                'count': len(detections),
                'total_duration': round(total_black_duration, 2),
                'percentage': round(black_percent, 2),
                'status': status,
                'passed': status != 'FAIL'
            }
            
        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Timeout - skipped")
            return self._empty_black_result()
        except Exception as e:
            print(f"     ⚠️  Error: {e}")
            return self._empty_black_result()
        
    def detect_frozen_frames(
        self,
        video_path: str,
        duration: float,
        noise_threshold: str = '-60dB',
        min_duration: float = 2.0
    ) -> Dict:
        """
        Detect frozen frames using FFmpeg freezedetect filter
        
        Args:
            video_path: Path to video
            duration: Video duration
            noise_threshold: Noise threshold (e.g., '-60dB')
            min_duration: Minimum freeze duration to detect (seconds)
        
        Returns:
            Dictionary with frozen frame detection results
        """
        print(f"   ❄️  Detecting frozen frames...")
        
        try:
            cmd = [
                self.ffmpeg,
                '-i', video_path,
                '-vf', f'freezedetect=n={noise_threshold}:d={min_duration}',
                '-an',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse output
            detections = self._parse_freeze_detections(result.stderr)  
            
            # Calculate statistics
            total_frozen_duration = sum(d['duration'] for d in detections)
            frozen_percent = (total_frozen_duration / duration * 100) if duration > 0 else 0
            
            # Determine status
            if frozen_percent > self.MAX_FROZEN_PERCENT:
                status = 'FAIL'
            elif frozen_percent > self.WARN_FROZEN_PERCENT:
                status = 'WARN'
            else:
                status = 'PASS'
                
            print(f"    Found {len(detections)} freeze(s)")
            print(f"    Total frozen duration: {total_frozen_duration:.2f}s ({frozen_percent:.2f}%)")
            print(f"      Status: {status}")
            
            return {
                'detections': detections,
                'count': len(detections),
                'total_duration': round(total_frozen_duration, 2),
                'percentage': round(frozen_percent, 2),
                'status': status,
                'passed': status != 'FAIL'
            }
            
        except subprocess.TimeoutExpired:
            print(f"      ⚠️  Timeout - skipped")
            return self._empty_frozen_result()
        except Exception as e:
            print(f"      ⚠️  Error: {e}")
            return self._empty_frozen_result()
        
    def _parse_black_detections(self, output: str) -> List[Dict]:
        """Parse blackdetect filter output"""
        detections = []
        
        # Pattern: black_start:4.5 black_end:4.7 black_duration:0.2
        pattern = r'black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)'
        
        for match in re.finditer(pattern, output):
            start = float(match.group(1))
            end = float(match.group(2))
            duration = float(match.group(3))
            
            detections.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'duration': round(duration, 2)
            })
            
        return detections
    
    def _parse_freeze_detections(self, output: str) -> List[Dict]:
        """Parse freezedetect filter output"""
        detections = []
        
        # Pattern: freeze_start: 5.2 freeze_end: 7.5 freeze_duration: 2.3
        # Note: Different spacing than blackdetect!
        start_pattern = r'freeze_start:\s*([\d.]+)'
        end_pattern = r'freeze_end:\s*([\d.]+)'
        duration_pattern = r'freeze_duration:\s([\d.]+)'
        
        # Find all starts
        starts = [float(m) for m in re.findall(start_pattern, output)]
        ends = [float(m) for m in re.findall(end_pattern, output)]
        durations = [float(m) for m in re.findall(duration_pattern, output)]
        
        # Combine into detections
        for i in range(min(len(starts), len(ends), len(durations))):
            detections.append({
                'start': round(starts[i], 2),
                'end': round(ends[i], 2),
                'duration': round(durations[i], 2)
            })
            
        return detections
    
    def _evaluate_results(self, black_result: Dict, frozen_result: Dict) -> bool:
        """Evaluate if frame analysis passed"""
        return black_result['passed'] and frozen_result['passed']
    
    def _empty_black_result(self) -> Dict:
        """Return empty black frame result"""
        return {
            'detections': [],
            'count': 0,
            'total_duration': 0,
            'percentage': 0,
            'status': 'SKIP',
            'passed': True
        }
    
    def _empty_frozen_result(self) -> Dict:
        """Return empty frozen frame result"""
        return {
            'detections': [],
            'count': 0,
            'total_duration': 0,
            'percentage': 0,
            'status': 'SKIP',
            'passed': True
        }
        
    def _print_summary(self, analysis: Dict):
        """Print frame analysis summary"""
        print(f"\n{'='*70}")
        print(f"FRAME ANALYSIS SUMMARY")
        print(f"{'='*70}")
        
        print(f"\nVideo Info:")
        print(f"  Total Frames: {analysis['total_frames']:,}")
        print(f"  Duration: {analysis['duration']:.2f}s")
        print(f"  FPS: {analysis['fps']:.2f}")
        
        black = analysis['black_frames']
        print(f"\n⬛ Black Frames:")
        print(f"  Detections: {black['count']}")
        print(f"  Duration: {black['total_duration']:.2f}s")
        print(f"  Percentage: {black['percentage']:.2f}%")
        print(f"  Status: {black['status']}")
        
        if black['detections']:
            print(f"  Locations:")
            for i, det in enumerate(black['detections'][:3], 1):
                print(f"   {i}. {det['start']:.2f}s - {det['end']}s ({det['duration']:.2f}s)")
            if black['count'] > 3:
                print(f"   ... and {black['count'] - 3} more")
                
                
        frozen = analysis['frozen_frames']
        print(f"\n❄️  Frozen Frames:")
        print(f"  Detections: {frozen['count']}")
        print(f"  Duration: {frozen['total_duration']:.2f}s")
        print(f"  Percentage: {frozen['percentage']:.2f}%")
        print(f"  Status: {frozen['status']}")
        
        if frozen['detections']:
            print(f"  Location:")
            for i, det in enumerate(frozen['detection'][:3], 1):
                print(f"   {i}. {det['start']:.2f}s - {det['end']:.2f}s ({det['duration']:.2f}s) ")
            if frozen['count'] > 3:
                print(f"   ... and {frozen['count'] - 3} more")
                
        print(f"\n{'='*70}")
        print(f"Overall: {'✅ PASS' if analysis['passed'] else '❌ FAIL'}")
        print(f"{'='*70}\n")
        
        
class FastFrameAnalyzer(FrameAnalyzer):
    """
    Faster frame analyzer using sampling
    Trade-off: Speed vs Accuracy
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg', sample_rate: int = 10):
        """
        Args:
            sample_rate: Analyze every Nth second (default: every 10 seconds)
        """
        super().__init__(ffmpeg_path)
        self.sample_rate = sample_rate
        
    def analyze_frames(
        self,
        video_path: str, 
        duration: float, 
        fps: float = 30.0
    ) -> Dict:
        """
        Fast frame analysis using sampling
        
        Only analyzes key sections of video for speed
        """
        print(f"\n🎬 Fast frame analysis (sampling every {self.sample_rate}s)...")
        
        # For fast analysis, we use higher thresholds
        # to catch only major issues
        black_result = self.detect_black_frames(
            video_path,
            duration,
            min_duration=0.5  # Longer minimum duration
        )
        
        frozen_result = self.detect_frozen_frames(
            video_path,
            duration,
            min_duration=3.0 # Longer minimum duration
        )
        
        total_frames = int(duration * fps)
        
        analysis = {
            'total_frames': total_frames,
            'duration': duration,
            'fps': fps,
            'black_frames': black_result,
            'frozen_frames': frozen_result,
            'passed': self._evaluate_results(black_result, frozen_result),
            'analysis_type': 'fast',
            'sample_rate': self.sample_rate
        }
        
        self._print_summary(analysis)
        
        return analysis