"""
Inpection Report Generator
Converts validation results into structured reports
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from pathlib import Path


class ReportGenerator:
    """
    Generates human_readable and machine-readable inspection reports
    """
    
    # Severity level descriptions
    SEVERITY_DESCRIPTIONS = {
        'reject': {
            'icon': '❌',
            'label': 'CRITICAL',
            'color': 'red',
            'description': 'This issue prevents video processing'
        },
        'warn': {
            'icon': '⚠️',
            'label': 'WARNING',
            'color': 'yellow',
            'description': 'Video can be processed but quality may be affected'
        },
        'info': {
            'icon': 'ℹ️',
            'label': 'INFO',
            'color': 'blue',
            'description': 'Informational note'
        }
    }
    
    # Category explanations for users
    CATEGORY_EXPLANATIONS = {
        'corruption': 'File appears damaged or incomplete',
        'container': 'Video file format is not supported',
        'codec': 'Video compression format is not compatible',
        'resolution': 'Video dimensions are outside acceptable range',
        'bitrate': 'Video quality/compression rate is problematic',
        'framerate': 'Video frame rate is outside acceptable range',
        'audio': 'Audio track has quality issues',
        'content': 'Video content has black or frozen frames'
    }
    
    # Fix suggestions
    FIX_SUGGESTIONS = {
        'resolution_low': [
            'Re-record video at higher resolution',
            'Use HD or high Quality export setting',
            'Check camera/recording settings',
            'Upload original uncompressed file'
        ],
        'resolution_high': [
            'Video resolution exceeds 4K limit',
            'Consider downscaling to 4K or 1080p',
            'Use video editing software to resize'
        ],
        'bitrate_low': [
            'Increase export quality settings',
            'Use higher bitrate in encoder',
            'Avoid excessive compression',
            'Upload original high-quality source'
        ],
        'framerate_low': [
            'Record at 24 FPS or higher',
            'Check camera frame rate settings',
            'Use standard frame rates (24, 30, 60 FPS)'
        ],
        'corruption': [
            'Try uploading again',
            'Check file plays correctly locally',
            'Re-export from video editor',
            'Use different browser if problem persists'
        ],
        'codec_unsupported': [
            'Convert to H.264 (MP4) format',
            'Use HandBrake or FFmpeg to re-encode',
            'Export in compatible format (MP4, MOV)'
        ],
        'black_frames': [
            'Check source video for black sections',
            'Remove black frames in video editor',
            'Verify recording didn\'t fail mid-capture'
        ],
        'frozen_frames': [
            'Check for recording issues',
            'Verify source plays smoothly',
            'Re-encode video to fix frame duplication'
        ]
    }
    
    def __init__(self):
        pass
    
    def generate_report(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        video_info: Dict,
        audio_info: Optional[Dict],
        issues: List[Dict],
        frame_analysis: Optional[Dict] = None
    ) -> Dict:
        """
        Generate complete inspection report
        
        Args:
            filename: Original filename
            file_path: Path to uploaded file
            file_size: File size in bytes
            video_info: Video stream information
            audio_info: Audio stream information (or None)
            issues: List of validation issues
            frame_analysis: Frame-level analysis results
        
        Returns:
            Complete structured report
        """
        inspection_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Categorize issues by severity
        rejections = [i for i in issues if i['severity'] == 'reject']
        warnings = [i for i in issues if i['severity'] == 'warn']
        
        # Determine final status
        if rejections:
            status = 'FAILED'
            can_process = False
            verdict_message = f"Video rejected due to {len(rejections)} crtical issue(s)"
        elif warnings:
            status = 'WARNING'
            can_process = True
            verdict_message = f"Video accepted with {len(warnings)} warning(s)"
        else:
            status = 'PASSED'
            can_process = True
            verdict_message = "Video passed all validations"
        
        # Generate check results
        checks = self._generate_checks(issues, frame_analysis)
        
        # Extract rejection reasons
        rejection_reasons = [self._format_issue_message(i) for i in rejections]
        warning_messages = [self._format_issue_message(i) for i in warnings]
        
        # Build report
        report = {
            'inspection_id': inspection_id,
            'filename': filename,
            'file_info': {
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'path': file_path,
                'uploaded_at': now.isoformat(),
                'inspected_at': now.isoformat()
            },
            'video': {
                'codec': video_info.get('codec_name'),
                'width': video_info.get('width'),
                'height': video_info.get('height'),
                'fps': self._parse_fps(video_info.get('r_frame_rate')),
                'bitrate': video_info.get('bit_rate'),
                'bitrate_mbps': round(int(video_info.get('bit_rate', 0)) / 1_000_000, 2) if video_info.get('bit_rate') else None,
                'duration': video_info.get('duration')
            },
            'audio': {
                'codec': audio_info.get('codec_name'),
                'bitrate': audio_info.get('bit_rate'),
                'bitrate_kbps': round(int(audio_info.get('bit_rate', 0)) / 1000, 0) if audio_info.get('bit_rate') else None,
                'sample_rate': audio_info.get('sample_rate'),
                'sample_rate_khz': round(int(audio_info.get('sample_rate', 0)) / 1000, 1) if audio_info.get('sample_rate') else None,
                'has_audio': True
            } if audio_info else None,
            'checks': checks,
            'issues': self._enrich_issues(issues),
            'frame_analysis': frame_analysis,
            'verdict': {
                'status': status,
                'can_process': can_process,
                'message': verdict_message,
                'rejection_reasons': rejection_reasons,
                'warnings': warning_messages
            }
        }
        
        return report
    
    def _generate_checks(self, issues: List[Dict], frame_analysis: Optional[Dict]) -> Dict:
        """Generate individual check results"""
        checks = {
            'container_format': 'PASS',
            'codec_support': 'PASS',
            'resolution': 'PASS',
            'bitrate': 'PASS',
            'frame_rate': 'PASS',
            'audio_quality': 'PASS',
            'black_frames': 'PASS',
            'frozen_frames': 'PASS'
        }
        
        # Update based on issues
        for issue in issues:
            category = issue['category']
            severity = issue['severity']
            
            # Map categories to check names
            if category in ['container', 'corruption']:
                checks['container_format'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'codec':
                checks['codec_support'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'resolution':
                checks['resolution'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'bitrate':
                checks['bitrate'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'framerate':
                checks['frame_rate'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'audio':
                checks['audio_quality'] = 'FAIL' if severity == 'reject' else 'WARN'
            elif category == 'content':
                # Determine if black or frozen frames based on message
                if 'black' in issue['message'].lower():
                    checks['black_frames'] = 'FAIL' if severity == 'reject' else 'WARN'
                elif 'frozen' in issue['message'].lower() or 'freeze' in issue['message'].lower():
                    checks['frozen_frames'] = 'FAIL' if severity == 'reject' else 'WARN'
        
        # Update based on frame analysis if available
        if frame_analysis:
            black_frames = frame_analysis.get('black_frames', {})
            frozen_frames = frame_analysis.get('frozen_frames', {})
            
            if not black_frames.get('passed', True):
                checks['black_frames'] = 'FAIL'
            
            if not frozen_frames.get('passed', True):
                checks['frozen_frames'] = 'FAIL'
                
    def _enrich_issues(self, issues: List[Dict]) -> List[Dict]:
        """Add human-readable explanations to issues"""
        enriched = []
        
        for issue in issues:
            enriched_issue = issue.copy()
            
            # Add severity info
            severity_info = self.SEVERITY_DESCRIPTIONS.get(issue['severity'], {})
            enriched_issue['severity_info'] = severity_info
            
            # Add categority explanation
            # Add category explanation
            category_explanation = self.CATEGORY_EXPLANATIONS.get(issue['category'], '')
            enriched_issue['category_explanation'] = category_explanation
            
            # Add fix suggestions
            fix_key = self._get_fix_key(issue)
            enriched_issue['fix_suggestions'] = self.FIX_SUGGESTIONS.get(fix_key, [])
            
            enriched.append(enriched_issue)
            
        return enriched
    
    def _get_fix_key(self, issue: Dict) -> str:
        """Determine which fix suggestions to show"""
        category = issue['category']
        message = issue['message'].lower()
        
        if category == 'resolution':
            if 'too low' in message or 'minimum' in message:
                return 'resolution_low'
            elif 'too high' in message or 'maximum' in message:
                return 'resolution_high'
        elif category == 'bitrate':
            if 'too low' in message:
                return 'bitrate_low'
        elif category == 'framerate':
            if 'too low' in message:
                return 'framerate_low'
        elif category == 'corruption':
            return 'corruption'
        elif category == 'codec':
            return 'codec_unsupported'
        elif category == 'content':
            if 'black' in message:
                return 'black_frames'
            elif 'frozen' in message or 'freeze' in message:
                return 'frozen_frames'
        
        return category
    
    def _format_issue_message(self, issue: Dict) -> str:
        """Format issue for verdict summary"""
        icon = self.SEVERITY_DESCRIPTIONS.get(issue['severity'], {}).get('icon', '•')
        return f"{icon} {issue['message']}"
    
    def _parse_fps(self, r_frame_rate: Optional[str]) -> Optional[float]:
        """Parse frame rate string"""
        if not r_frame_rate:
            return None
        try:
            num, den = map(int, r_frame_rate.split('/'))
            return round(num / den, 2) if den != 0 else None
        except:
            return None
        
    def generate_human_readable_report(self, report: Dict) -> str:
        """
        Generate human-readable text report for display
        
        Args:
            report: Structured report dictionary
        
        Returns:
            Formatted text report
        """
        lines = []
        
        # Header
        lines.append("━" * 70)
        verdict = report['verdict']
        
        if verdict['status'] == 'FAILED':
            lines.append("❌ VIDEO REJECTED")
        elif verdict['status'] == 'WARNING':
            lines.append("⚠️  VIDEO ACCEPTED WITH WARNINGS")
        else:
            lines.append("✅ VIDEO PASSED")
        
        lines.append("━" * 70)
        lines.append("")
        
        # File info
        file_info = report['file_info']
        lines.append(f"File: {report['filename']}")
        lines.append(f"Size: {file_info['size_mb']} MB")
        lines.append(f"Inspected: {file_info['inspected_at']}")
        lines.append("")
        
        # Video info
        video = report['video']
        lines.append("Video Properties:")
        lines.append(f"  Resolution: {video['width']}×{video['height']}")
        lines.append(f"  Codec: {video['codec']}")
        lines.append(f"  Frame Rate: {video['fps']} FPS")
        lines.append(f"  Bitrate: {video.get('bitrate_mbps', 'N/A')} Mbps")
        duration = float(video['duration']) if video.get('duration') else 0
        lines.append(f"  Duration: {duration:.2f}s")
        lines.append("")
        
        # Audio info
        if report['audio']:
            audio = report['audio']
            lines.append("Audio Properties:")
            lines.append(f"  Codec: {audio.get('codec', 'N/A')}")
            lines.append(f"  Bitrate: {audio.get('bitrate_kbps', 'N/A')} kbps")
            lines.append(f"  Sample Rate: {audio.get('sample_rate_khz', 'N/A')} kHz")
        else:
            lines.append("Audio: No audio track")
        lines.append("")
        
        # Issues
        if report['issues']:
            lines.append("Issues Found:")
            lines.append("─" * 70)
            
            for i, issue in enumerate(report['issues'], 1):
                severity_info = issue['severity_info']
                lines.append(f"\n{i}. {severity_info['icon']} {issue['message']}")
                lines.append(f"   Category: {issue['category_explanation']}")
                
                if issue.get('fix_suggestions'):
                    lines.append("   How to fix:")
                    for suggestion in issue['fix_suggestions'][:3]:  # Show top 3
                        lines.append(f"   • {suggestion}")
            
            lines.append("")
            
        # Frame analysis
        if report.get('frame_analysis'):
            frame_analysis = report['frame_analysis']
            lines.append("Frame Analysis:")
            
            black = frame_analysis.get('black_frames', {})
            lines.append(f"  Black Frames: {black.get('percent', 0):.2f}% {'✅' if black.get('passed', True) else '❌'}")
            
            frozen = frame_analysis.get('frozen_frames', {})
            lines.append(f"  Frozen Frames: {frozen.get('percent', 0):.2f}% {'✅' if frozen.get('passed', True) else '❌'}")
            lines.append("")
            
        # Verdict
        lines.append("━" * 70)
        lines.append(f"Status: {verdict['status']}")
        lines.append(f"Message: {verdict['message']}")
        
        if verdict['rejection_reasons']:
            lines.append("\nRejection Reasons:")
            for reason in verdict['rejection_reasons']:
                lines.append(f"  {reason}")
        
        if verdict['warnings']:
            lines.append("\nWarnings:")
            for warning in verdict['warnings']:
                lines.append(f"  {warning}")
                
        lines.append("━" * 70)
        
        return "\n".join(lines)