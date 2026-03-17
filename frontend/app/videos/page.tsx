'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import { Video, Download, Trash2, Eye, Loader2, CheckCircle, XCircle } from 'lucide-react';

interface TranscodedVideo {
  quality: string;
  file_size_mb: number;
  similarity_score: number;
  verification_passed: boolean;
  processing_time: number;
}

interface VideoItem {
  id: number;
  filename: string;
  resolution: string;
  file_size_mb: number;
  status: string;
  created_at: string;
  transcoded: TranscodedVideo[];
}

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedVideos, setSelectedVideos] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  
  const router = useRouter();

  // ═══════════════════════════════════════════════════════════
  // Fetch user's videos on page load
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    fetchVideos();
  }, [router]);

  const fetchVideos = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/videos/list', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVideos(response.data);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    }
    setLoading(false);
  };

  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 6: Toggle video selection for batch delete
  // ═══════════════════════════════════════════════════════════
  const toggleSelection = (videoId: number) => {
    const newSelected = new Set(selectedVideos);
    if (newSelected.has(videoId)) {
      newSelected.delete(videoId);
    } else {
      newSelected.add(videoId);
    }
    setSelectedVideos(newSelected);
  };

  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 6: Batch delete selected videos
  // ═══════════════════════════════════════════════════════════
  const handleBatchDelete = async () => {
    if (selectedVideos.size === 0) return;
    
    if (!confirm(`Delete ${selectedVideos.size} video(s)? This cannot be undone.`)) {
      return;
    }

    setDeleting(true);
    try {
      const token = localStorage.getItem('token');
      
      // Delete each selected video
      await Promise.all(
        Array.from(selectedVideos).map(videoId =>
          axios.delete(`http://localhost:8000/api/videos/${videoId}`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        )
      );
      
      // Refresh list
      setSelectedVideos(new Set());
      await fetchVideos();
      alert('Videos deleted successfully!');
    } catch (error) {
      alert('Failed to delete some videos');
      console.error(error);
    }
    setDeleting(false);
  };

  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 7: Download transcoded video
  // ═══════════════════════════════════════════════════════════
  const handleDownload = async (videoId: number, quality: string, filename: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `http://localhost:8000/api/videos/${videoId}/download/${quality}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename.replace('.mp4', '')}_${quality}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert('Download failed');
      console.error(error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 py-12">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">My Videos</h1>
            <p className="text-gray-600">
              Manage your uploaded and transcoded videos
            </p>
          </div>

          {/* Batch Delete Button */}
          {selectedVideos.size > 0 && (
            <button
              onClick={handleBatchDelete}
              disabled={deleting}
              className="flex items-center gap-2 px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-semibold disabled:bg-gray-400"
            >
              <Trash2 className="w-5 h-5" />
              Delete Selected ({selectedVideos.size})
            </button>
          )}
        </div>

        {/* Videos List */}
        {videos.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
            <Video className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <p className="text-xl text-gray-600 mb-4">No videos yet</p>
            <button
              onClick={() => router.push('/upload')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
            >
              Upload Your First Video
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {videos.map(video => (
              <div key={video.id} className="bg-white rounded-2xl shadow-xl p-6">
                <div className="flex items-start gap-4">
                  
                  {/* Checkbox for selection */}
                  <input
                    type="checkbox"
                    checked={selectedVideos.has(video.id)}
                    onChange={() => toggleSelection(video.id)}
                    className="mt-1 w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />

                  {/* Video Info */}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">{video.filename}</h3>
                        <p className="text-sm text-gray-600">
                          {video.resolution} • {video.file_size_mb} MB • 
                          {video.status === 'approved' ? (
                            <span className="text-green-600 ml-2">✓ Approved</span>
                          ) : (
                            <span className="text-yellow-600 ml-2">⏳ {video.status}</span>
                          )}
                        </p>
                      </div>
                      
                      <button
                        onClick={() => router.push(`/progress?video_id=${video.id}`)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </button>
                    </div>

                    {/* Transcoded Versions */}
                    {video.transcoded && video.transcoded.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm font-semibold text-gray-700 mb-2">
                          Transcoded Versions:
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                          {video.transcoded.map(t => (
                            <div
                              key={t.quality}
                              className={`p-3 rounded-lg border-2 ${
                                t.verification_passed
                                  ? 'border-green-300 bg-green-50'
                                  : 'border-yellow-300 bg-yellow-50'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-bold text-gray-900">{t.quality}</span>
                                {t.verification_passed ? (
                                  <CheckCircle className="w-4 h-4 text-green-600" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-yellow-600" />
                                )}
                              </div>
                              <p className="text-xs text-gray-600 mb-2">
                                {t.file_size_mb} MB • {t.similarity_score}% similar
                              </p>
                              
                              {/* Download Button */}
                              <button
                                onClick={() => handleDownload(video.id, t.quality, video.filename)}
                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                              >
                                <Download className="w-4 h-4" />
                                Download
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}