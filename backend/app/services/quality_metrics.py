"""
Video Quality Metrics Service
Implements PSNR, SSIM, and VMAF quality measurements
"""



import subprocess
import re
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

class QualityMetrics:
    """
    Measures video quality using industry-standard metrics
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        
    def _get_video_resolution(self, video_path: str) -> Tuple[int, int]:
        """Get video width and height using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        for stream in data['streams']:
            if stream.get('codec_type') == 'video':
                return stream['width'], stream['height']
        raise ValueError(f"No video stream found in {video_path}")
        
        
    def calculate_psnr(
        self,
        reference_path: str,
        distorted_path: str,
        stats_file: Optional[str] = None
    ) -> Dict:
        """
        Calculate PSNR (Peak Signal-to-Noise Ratio)
        
        Args:
            reference_path: Original video
            distorted_path: Compressed/processed video
            stats_file: Optional file to save detailed stats
            
        Returns:
            Dictionary with PSNR scores
        """
        try:
            # Convert to absolute paths
            reference_path = str(Path(reference_path).resolve())
            distorted_path = str(Path(distorted_path).resolve())
            
            stats_file = stats_file or "psnr_stats.log"
            
            # Get distorted resolution and scale reference to match
            width, height = self._get_video_resolution(distorted_path)

            cmd = [
                self.ffmpeg,
                '-i', reference_path,
                '-i', distorted_path,
                '-filter_complex', f'[0:v]scale={width}:{height}[ref];[ref][1:v]psnr=stats_file={stats_file}',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(f"\n=== PSNR DEBUG ===")
            print(f"Command: {' '.join(cmd)}")
            print(f"FFmpeg output:\n{result.stderr[-1000:]}\n")
            
            # Parse PSNR from output (look for "PSNR" line in stderr)
            psnr_pattern = r'PSNR.*?average:([\d.]+)'
            match = re.search(psnr_pattern, result.stderr)
            
            if match:
                avg_psnr = float(match.group(1))
                quality = self._interpret_psnr(avg_psnr)
                
                return {
                    'metric': 'PSNR',
                    'score': avg_psnr,
                    'unit': 'dB',
                    'quality': quality,
                    'interpretation': self._get_psnr_interpretation(avg_psnr),
                    'stats_file': stats_file
                }   
            else:
                return {'error': 'Could not parse PSNR output'}
            
        except subprocess.TimeoutExpired:
            return {'error': 'PSNR calculation timed out'}
        except Exception as e:
            return {'error': f'PSNR calculation failed: {str(e)}'}
        
        
    def calculate_ssim(
        self,
        reference_path: str,
        distorted_path: str,
        stats_file: Optional[str] = None
    ) -> Dict:
        """
        Calculates SSIM (Structural Similarity Index)
        
        Args:
            reference_path: Original video
            distorted_path: Compressed/processed video
            stats_file: Optional file to save detailed stats
            
        Returns:
            Dictionary with SSIM scores
        """
        try:
            # Convert to absolute paths
            reference_path = str(Path(reference_path).resolve())
            distorted_path = str(Path(distorted_path).resolve())
            
            stats_file = stats_file or "ssim_stats.log"
            
            # Get distorted resolution and scale reference to match
            width, height = self._get_video_resolution(distorted_path)

            cmd = [
                self.ffmpeg,
                '-i', reference_path,
                '-i', distorted_path,
                '-filter_complex', f'[0:v]scale={width}:{height}[ref];[ref][1:v]ssim=stats_file={stats_file}',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(f"\n=== SSIM DEBUG ===")
            print(f"Command: {' '.join(cmd)}")
            print(f"FFmpeg output:\n{result.stderr[-1000:]}\n")
            
            # Parse SSIM from output
            ssim_pattern = r'All:([\d.]+)'
            matches = re.findall(ssim_pattern, result.stderr)
            
            if matches:
                avg_ssim = sum(float(m) for m in matches) / len(matches)
                quality = self._interpret_ssim(avg_ssim)
                
                return {
                    'metric': 'SSIM',
                    'score': round(avg_ssim, 4),
                    'unit': 'index (0-1)',
                    'quality': quality,
                    'interpretation': self._get_ssim_interpretation(avg_ssim),
                    'frame_count': len(matches),
                    "stats_file": stats_file
                }
            else:
                return {'error': 'Could not parse SSIM output'}
            
        except subprocess.TimeoutExpired:
            return {'error': 'SSIM calculation timed out'}
        except Exception as e:
            return {'error': f'SSIM calculation failed: {str(e)}'}
        
    
    def calculate_vmaf(
        self,
        reference_path: str,
        distorted_path: str,
        model_path: Optional[str] = None,
        log_path: Optional[str] = None
    ) -> Dict:
        """
        calculate VMAF (Video Multi-Method Assessment Fusion)
        
        Args:
            reference_path: Original video
            distorted_path: Compressed/processed video
            model_path: Path to VMAF model (optional, uses default if not provided)
            log_path: Path to save detailed VMAF log
            
        Returns:
            Dictionary with VMAF scores
        """
        try:
            # Convert to absolute paths
            reference_path = str(Path(reference_path).resolve())
            distorted_path = str(Path(distorted_path).resolve())
            
            log_path = log_path or "vmaf_log.json"
            
            # Get distorted resolution and scale reference to match
            width, height = self._get_video_resolution(distorted_path)

            if model_path:
                vmaf_filter = f'[1:v]scale={width}:{height}[ref];[0:v][ref]libvmaf=model_path={model_path}:log_path={log_path}:log_fmt=json'
            else:
                vmaf_filter = f'[1:v]scale={width}:{height}[ref];[0:v][ref]libvmaf=log_path={log_path}:log_fmt=json'
                
            cmd = [
                self.ffmpeg,
                '-i', distorted_path,
                '-i', reference_path,
                '-filter_complex', vmaf_filter,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            print(f"\n=== VMAF DEBUG ===")
            print(f"Command: {' '.join(cmd)}")
            print(f"FFmpeg output:\n{result.stderr[-1000:]}\n")
            
            # Parse VMAF score from output
            vmaf_pattern = r'VMAF score[:\s]+([\d.]+)'
            match = re.search(vmaf_pattern, result.stderr)
            
            if match:
                vmaf_score = float(match.group(1))
                quality = self._interpret_vmaf(vmaf_score)
                
                return {
                    'metric': 'VMAF',
                    'score': round(vmaf_score, 2),
                    'unit': 'score (0-100)',
                    'quality': quality,
                    'interpretation': self._get_vmaf_interpretation(vmaf_score),
                    'log_file': log_path
                }
                
            # Try reading from log file
            if Path(log_path).exists():
                with open(log_path, 'r') as f:
                    vmaf_data = json.load(f)
                    vmaf_score = vmaf_data.get('pooled_metrics', {}).get('vmaf', {}).get('mean')
                    
                    if vmaf_score:
                        quality = self._interpret_vmaf(vmaf_score)
                        
                        return {
                            'metric': 'VMAF',
                            'score': round(vmaf_score, 2),
                            'unit': 'score (0-100)',
                            'quality': quality,
                            'interpretation': self._get_vmaf_interpretation(vmaf_score),
                            'log_file': log_path
                        }
                        
            return {'error': 'Could not parse VMAF output'}

        except subprocess.TimeoutExpired:
            return {'error': 'VMAF calculation timed out (this is slow, be patient!)'}
        except Exception as e:
            return {'error': f'VMAF calculation failed: {str(e)}'}
        
    def compare_videos(
        self,
        reference_path: str,
        distorted_path: str,
        metrics: list = ['ssim'] # Default to SSIM for speed
    ) -> Dict:
        """
        Compare two videos using multiple metrics
        
        Args:
        reference_path: Original video,
        distorted_path: Compressed/processed video,
        metrics: List of metric to calculate ['psnr', 'ssim', 'vmaf']
        
        Returns:
            Dictionary with all requested metric scores 
        """
        print(f"\n🔍  Comparing videos:")
        print(f" Reference: {Path(reference_path).name}")
        print(f" Distorted: {Path(distorted_path).name}")
        print(f" Metrics: {', '.join(metrics).upper()}\n")
        
        results = {
            'reference': reference_path,
            'distorted': distorted_path,
            'metrics': {}
        }
        
        if 'psnr' in metrics:
            print("⏳  Calculating PSNR...")
            psnr_result = self.calculate_psnr(reference_path, distorted_path)
            results['metrics']['psnr'] = psnr_result
            
            if 'error' not in psnr_result:
                print(f"  PSNR: {psnr_result['score']:.2f} dB - {psnr_result['quality']}")
            else:
                print(f"  ❌ {psnr_result['error']}")
                
        if 'ssim' in metrics:
            print(f"⏳  Calculating SSIM...")
            ssim_result = self.calculate_ssim(reference_path, distorted_path)
            results['metrics']['ssim'] = ssim_result
            
            if 'error' not in ssim_result:
                print(f"  SSIM: {ssim_result['score']:.4f} - {ssim_result['quality']}")
            else:
                print(f"  ❌ {ssim_result['error']}")
                
        if 'vmaf' in metrics:
            print(f"⏳  Calculating VMAF (this takes longer)...")
            vmaf_result = self.calculate_vmaf(reference_path, distorted_path)
            results['metrics']['vmaf'] = vmaf_result
            
            if 'error' not in vmaf_result:
                print(f"  VMAF: {vmaf_result['score']:.2f} - {vmaf_result['quality']}")
            else:
                print(f"  ❌  {vmaf_result['error']}")
                
            print("\n✅ Comparison complete!\n")
            
            return results
    
    # Helper methods for interpretation
    def _interpret_psnr(self, psnr: float) -> str:
        """Interpret PSNR score"""
        if psnr >= 40:
            return "Excellent"
        elif psnr >= 35:
            return "Good"
        elif psnr >= 30:
            return "Acceptable"
        else:
            return "Poor"
        
    def _interpret_ssim(self, ssim: float) -> str:
        """Interpret SSIM score"""
        if ssim >= 0.95:
            return "Excellent"
        elif ssim >= 0.90:
            return "Good"
        elif ssim >= 0.85:
            return "Acceptable"
        else:
            return "Poor"
        
    def _interpret_vmaf(self, vmaf: float) -> str:
        """Interpret VMAF score"""
        if vmaf >= 95:
            return "Perfect"
        elif vmaf >= 85:
            return "Excellent"
        elif vmaf >= 75:
            return "Very Good"
        elif vmaf >= 60:
            return "Good"
        elif vmaf >= 40:
            return "Acceptable"
        else:
            return "Poor"
        
    def _get_psnr_interpretation(self, psnr: float) -> str:
        """Get detailed PSNR interpretation"""
        
        interpretations = {
            50: "Near perfect - indistinguishable from original",
            40: "Excellent quality - artifacts barely visible",
            35: "Good quality - minor artifacts visible",
            30: "Accepatbe quality - artifacts noticeable",
            25: "Poor quality - significant compression",
            20: "Very poor quality - severe degradation"
        }
        
        for threshold, description in sorted(interpretations.items(), reverse=True):
            if psnr >= threshold:
                return description
            
        return "Extremely poor quality - unusable"
    
    def _get_ssim_interpretation(self, ssim: float) -> str:
        """Get detailed SSIM interpretation"""
        if ssim >= 0.99:
            return "Near perfect - imperceptible difference"
        elif ssim >= 0.95:
            return "Excellent - very minor quality loss"
        elif ssim >= 0.90:
            return "Good - minor structural differences"
        elif ssim >= 0.85:
            return "Acceptable - noticeable structural changes"
        elif ssim >= 0.70:
            return "Poor - significant structural degradation"
        else:
            return "Very poor - severe structural damage"
        
    def _get_vmaf_interpretation(self, vmaf: float) -> str:
        """Get detailed VMAF interpretation (Netflix standards)"""
        if vmaf >= 95:
            return "Perfect - Netflix 4K quality"
        elif vmaf >= 85:
            return "Excellent - Netflix Full HD quality"
        elif vmaf >= 75:
            return "Very Good - Netflix High quality"
        elif vmaf >= 60:
            return "Good - Netflix Medium quality"
        elif vmaf >= 40:
            return "Acceptable - Netflix Low quality"
        elif vmaf >= 20:
            return "Poor - Below Netflix standards"
        else:
            return "Unusable - Netflix would never stream this"
        
    def run_quality_check(
        self,
        original_path: str,
        transcoded_path: str,
        include_vmaf: bool = False  # Optional, slow
    ) -> Dict:
        """
        Quick quality check returning PSNR, SSIM, and optionally VMAF.
        Returns dict with keys: psnr, ssim, vmaf, psnr_ok, ssim_ok, vmaf_ok, overall_pass
        """
        # Choose metrics based on flag
        metrics = ['psnr', 'ssim']
        if include_vmaf:
            metrics.append('vmaf')
        
        result = self.compare_videos(
            original_path,
            transcoded_path,
            metrics=metrics
        )
        
        psnr_score = result['metrics']['psnr'].get('score', 0)
        ssim_score = result['metrics']['ssim'].get('score', 0)
        vmaf_score = result['metrics'].get('vmaf', {}).get('score', None) if include_vmaf else None
        
        return {
            'psnr': psnr_score,
            'ssim': ssim_score,
            'vmaf': vmaf_score,
            'psnr_ok': psnr_score >= 30,
            'ssim_ok': ssim_score >= 0.85,
            'vmaf_ok': vmaf_score >= 70 if vmaf_score is not None else False,
            'overall_pass': psnr_score >= 30 and ssim_score >= 0.85
        }