'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import axios from 'axios';
import Navbar from '@/components/Navbar'; // ← NEW: Import Navbar
import { Download, X, StopCircle } from 'lucide-react'; // ← NEW: Icons

interface ProgressMessage {
    type: string;
    status: string;
    quality?: string;
    verification_passed?: boolean;
}

interface VideoSummary {
    original: {
        filename: string;
        resolution: string;
        codec: string;
        fps: number;
        duration: number;
        file_size_mb: number;
        bitrate_mbps: number;
    };
    transcoded: Array<{
        quality: string;
        file_size_mb: number;
        similarity_score: number;
        verification_passed: boolean;
        processing_time: number;
    }>;
    summary: {
        total_qualities: number;
        total_processing_time: number;
        total_output_size_mb: number;
        all_verified: boolean;
        status: string;
    };
}

function ProgressContent() {
    const searchParams = useSearchParams();
    const videoId = searchParams.get('video_id');
    const router = useRouter();

    const [messages, setMessages] = useState<string[]>([]);
    const [connected, setConnected] = useState(false);
    const [completedQualities, setCompletedQualities] = useState<Set<string>>(new Set());
    const [showSummary, setShowSummary] = useState(false);
    const [summary, setSummary] = useState<VideoSummary | null>(null);
    const [cancelling, setCancelling] = useState(false); // ← NEW: Cancel state
    
    const wsRef = useRef<WebSocket | null>(null);

    // ═══════════════════════════════════════════════════════════
    // NEW FEATURE 1: Protect route - redirect if not authenticated
    // ═══════════════════════════════════════════════════════════
    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            router.push('/login');
        }
    }, [router]);

    useEffect(() => {
        if (!videoId) return;

        const ws = new WebSocket(`ws://localhost:8000/ws/progress/${videoId}`);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            addMessage('🔗 Connected - waiting for progress...');
        };

        ws.onmessage = (event) => {
            const data: ProgressMessage = JSON.parse(event.data);
            handleMessage(data);
        };

        ws.onerror = () => {
            addMessage('❌ Connection error');
        };

        ws.onclose = () => {
            setConnected(false);
            addMessage('🔌 Disconnected');
        };

        return () => {
            ws.close();
        };
    }, [videoId]);

    const handleMessage = (data: ProgressMessage) => {
        addMessage(data.status);

        if (data.type === 'completed' && data.quality) {
            setCompletedQualities(prev => new Set([...prev, data.quality!]));
        }
    };

    const addMessage = (msg: string) => {
        const timestamp = new Date().toLocaleTimeString();
        setMessages(prev => [...prev, `[${timestamp}] ${msg}`]);
    };

    const fetchSummary = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(
                `http://localhost:8000/api/videos/${videoId}/summary`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setSummary(response.data);
            setShowSummary(true);
        } catch (error) {
            console.error('Failed to fetch summary:', error);
        }
    };

    // ═══════════════════════════════════════════════════════════
    // NEW FEATURE 10: Cancel ongoing transcoding
    // ═══════════════════════════════════════════════════════════
    const handleCancel = async () => {
        if (!confirm('Cancel all transcoding jobs for this video?')) return;
        
        setCancelling(true);
        try {
            const token = localStorage.getItem('token');
            await axios.post(
                `http://localhost:8000/api/videos/${videoId}/cancel`,
                {},
                { headers: { Authorization: `Bearer ${token}` } }
            );
            addMessage('🛑 Cancellation requested...');
            alert('Transcoding cancelled. Returning to upload page.');
            router.push('/upload');
        } catch (error) {
            alert('Failed to cancel');
            console.error(error);
        }
        setCancelling(false);
    };

    // ═══════════════════════════════════════════════════════════
    // NEW FEATURE 7: Download transcoded video
    // ═══════════════════════════════════════════════════════════
    const handleDownload = async (quality: string) => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(
                `http://localhost:8000/api/videos/${videoId}/download/${quality}`,
                {
                    headers: { Authorization: `Bearer ${token}` },
                    responseType: 'blob'
                }
            );
            
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = `video_${videoId}_${quality}.mp4`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            alert('Download failed');
            console.error(error);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            {/* ═══════════════════════════════════════════════════════════
                NEW FEATURE 4 & 9: Navbar with logout and home
                ═══════════════════════════════════════════════════════════ */}
            <Navbar />
            
            <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto', fontFamily: 'system-ui' }}>
                
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>
                            🎬 Transcoding Progress
                        </h1>
                        <p style={{ color: '#666' }}>
                            Video ID: {videoId} &nbsp;|&nbsp;
                            Status: {connected
                                ? <span style={{ color: 'green' }}>● Connected</span>
                                : <span style={{ color: 'red' }}>● Disconnected</span>
                            }
                        </p>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════
                        NEW FEATURE 10: Cancel button (only show if not complete)
                        ═══════════════════════════════════════════════════════════ */}
                    {!showSummary && (
                        <button
                            onClick={handleCancel}
                            disabled={cancelling}
                            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-semibold disabled:bg-gray-400"
                        >
                            <StopCircle className="w-5 h-5" />
                            {cancelling ? 'Cancelling...' : 'Cancel Transcoding'}
                        </button>
                    )}
                </div>

                {/* LIVE LOG */}
                <div style={{ marginBottom: '24px' }}>
                    <h2 style={{ fontSize: '18px', marginBottom: '8px' }}>📋 Live Log</h2>
                    <div style={{
                        height: '300px',
                        overflowY: 'auto',
                        backgroundColor: '#1e1e1e',
                        color: '#d4d4d4',
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '13px',
                        lineHeight: '1.6'
                    }}>
                        {messages.map((msg, i) => <div key={i}>{msg}</div>)}
                    </div>
                </div>

                {/* SHOW SUMMARY BUTTON */}
                {completedQualities.size > 0 && !showSummary && (
                    <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                        <button
                            onClick={fetchSummary}
                            style={{
                                padding: '12px 24px',
                                fontSize: '16px',
                                backgroundColor: '#4caf50',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 'bold'
                            }}
                        >
                            📊 View Summary Report
                        </button>
                    </div>
                )}

                {/* SUMMARY REPORT */}
                {showSummary && summary && (
                    <div style={{
                        backgroundColor: '#f5f5f5',
                        padding: '24px',
                        borderRadius: '12px',
                        border: '2px solid #4caf50',
                        position: 'relative'
                    }}>
                        {/* ═══════════════════════════════════════════════════════════
                            NEW FEATURE 8: X button to close summary
                            ═══════════════════════════════════════════════════════════ */}
                        <button
                            onClick={() => setShowSummary(false)}
                            style={{
                                position: 'absolute',
                                top: '16px',
                                right: '16px',
                                background: 'white',
                                border: '2px solid #ccc',
                                borderRadius: '50%',
                                width: '32px',
                                height: '32px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                fontSize: '18px',
                                color: '#666'
                            }}
                        >
                            ×
                        </button>

                        <h2 style={{ fontSize: '24px', marginBottom: '16px', color: '#2e7d32' }}>
                            ✅ Transcoding Complete!
                        </h2>

                        {/* ORIGINAL VIDEO INFO */}
                        <div style={{ marginBottom: '24px', padding: '16px', backgroundColor: 'white', borderRadius: '8px' }}>
                            <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>📹 Original Video</h3>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '14px' }}>
                                <div><strong>Filename:</strong> {summary.original.filename}</div>
                                <div><strong>Resolution:</strong> {summary.original.resolution}</div>
                                <div><strong>Codec:</strong> {summary.original.codec}</div>
                                <div><strong>FPS:</strong> {summary.original.fps}</div>
                                <div><strong>Duration:</strong> {summary.original.duration.toFixed(2)}s</div>
                                <div><strong>File Size:</strong> {summary.original.file_size_mb} MB</div>
                            </div>
                        </div>

                        {/* TRANSCODED VERSIONS */}
                        <div style={{ marginBottom: '24px' }}>
                            <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>🎬 Transcoded Versions</h3>
                            <div style={{ display: 'grid', gap: '12px' }}>
                                {summary.transcoded.map(t => (
                                    <div key={t.quality} style={{
                                        padding: '16px',
                                        backgroundColor: 'white',
                                        borderRadius: '8px',
                                        border: `2px solid ${t.verification_passed ? '#4caf50' : '#ff9800'}`,
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center'
                                    }}>
                                        <div>
                                            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{t.quality}</div>
                                            <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                                                {t.file_size_mb} MB • {t.processing_time}s • Similarity: {t.similarity_score}%
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                            {/* ═══════════════════════════════════════════════════════════
                                                NEW FEATURE 7: Download button for each quality
                                                ═══════════════════════════════════════════════════════════ */}
                                            <button
                                                onClick={() => handleDownload(t.quality)}
                                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-semibold"
                                            >
                                                <Download className="w-4 h-4" />
                                                Download
                                            </button>
                                            <div style={{ fontSize: '24px' }}>
                                                {t.verification_passed ? '✅' : '⚠️'}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* SUMMARY STATS */}
                        <div style={{ padding: '16px', backgroundColor: 'white', borderRadius: '8px' }}>
                            <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>📊 Summary</h3>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '14px' }}>
                                <div><strong>Total Qualities:</strong> {summary.summary.total_qualities}</div>
                                <div><strong>Total Time:</strong> {summary.summary.total_processing_time}s</div>
                                <div><strong>Total Output Size:</strong> {summary.summary.total_output_size_mb} MB</div>
                                <div><strong>All Verified:</strong> {summary.summary.all_verified ? '✅ Yes' : '⚠️ No'}</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function ProgressPage() {
    return (
        <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}>Loading...</div>}>
            <ProgressContent />
        </Suspense>
    );
}