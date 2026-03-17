'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { CheckCircle2, XCircle, AlertTriangle, Upload, FileVideo, Loader2 } from 'lucide-react';
import Navbar from '@/components/Navbar'; // ← NEW: Import Navbar

interface Check {
  name: string;
  passed: boolean;
  level: 'reject' | 'warn' | 'info';
  message: string;
}

interface ValidationResult {
  is_valid: boolean | null;
  filename: string;
  size: number;
  checks: Check[];
  error?: string;
  message?: string;
  video_id?: number;
  status?: string;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  
  const router = useRouter();

  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 1: Protect route - redirect to login if not authenticated
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  function handleFileSelect(event: any) {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setResult(null);
      setProgress(0);
    }
  }
  
  function handleDragOver(event: any) {
    event.preventDefault();
    setIsDragging(true);
  }
  
  function handleDragLeave(event: any) {
    event.preventDefault();
    setIsDragging(false);
  }
  
  function handleDrop(event: any) {
    event.preventDefault();
    setIsDragging(false);
    
    const droppedFile = event.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('video/')) {
      setFile(droppedFile);
      setFileName(droppedFile.name);
      setResult(null);
      setProgress(0);
    }
  }
  
  async function handleUpload() {
    if (!file) return;
    
    setUploading(true);
    setResult(null);
    setProgress(0);
    
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        setResult({
          is_valid: false,
          filename: fileName,
          size: 0,
          checks: [],
          error: 'Please login first!'
        });
        setUploading(false);
        return;
      }
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(
        'http://localhost:8000/api/upload',
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 1)
            );
            setProgress(percentCompleted);
          }
        }
      );
      
      const uploadData = response.data;
      
      setResult({
        is_valid: null,
        filename: uploadData.filename,
        size: uploadData.file_size,
        checks: [],
        message: `📤 Upload Successful!\n\n⏳ Validation in Progress...\n\nClick "Check Status" to see results.`,
        video_id: uploadData.id,
        status: 'processing'
      });
      
      if (uploadData.id) {
        router.push(`/progress?video_id=${uploadData.id}`);
      }
      
    } catch (error: any) {
      let errorMessage = 'Upload failed! Make sure backend is running.';
      
      if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please login again.';
        router.push('/login');
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setResult({
        is_valid: false,
        filename: fileName,
        size: 0,
        checks: [],
        error: errorMessage
      });
    }
    
    setUploading(false);
  }
  
  function resetUpload() {
    setFile(null);
    setFileName('');
    setResult(null);
    setProgress(0);
  }
  
  function getCheckIcon(check: Check) {
    if (check.passed) {
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    }
    if (check.level === 'reject') {
      return <XCircle className="w-5 h-5 text-red-500" />;
    }
    return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* ═══════════════════════════════════════════════════════════
          NEW FEATURE 4 & 9: Navbar with Logout and Home buttons
          ═══════════════════════════════════════════════════════════ */}
      <Navbar />
      
      <div className="py-12 px-4">
        <div className="max-w-4xl mx-auto">
          
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Video Upload & Validation
            </h1>
            <p className="text-gray-600">
              Upload your video to check quality and compatibility
            </p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* LEFT SIDE: Upload Section */}
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload Video
              </h2>
              
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  border-3 border-dashed rounded-xl p-8 text-center
                  transition-all duration-300 cursor-pointer
                  ${isDragging 
                    ? 'border-blue-500 bg-blue-50 scale-105' 
                    : 'border-gray-300 bg-gray-50 hover:border-blue-400'
                  }
                `}
              >
                <FileVideo className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                
                <p className="text-lg font-semibold text-gray-700 mb-2">
                  {isDragging ? 'Drop it here!' : 'Drag & drop video'}
                </p>
                
                <p className="text-sm text-gray-500 mb-4">
                  or
                </p>
                
                <label className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors cursor-pointer">
                  Browse Files
                  <input 
                    type="file" 
                    accept="video/*" 
                    onChange={handleFileSelect}
                    disabled={uploading}
                    className="hidden"
                  />
                </label>
              </div>
              
              {fileName && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">{fileName}</p>
                      <p className="text-sm text-gray-600">
                        {(file!.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>
                    {!uploading && !result && (
                      <button
                        onClick={resetUpload}
                        className="text-red-500 hover:text-red-700 text-sm font-semibold"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              {uploading && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span>Uploading & Validating...</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-blue-600 h-full rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
              
              <button 
                onClick={handleUpload}
                disabled={!file || uploading}
                className={`
                  w-full mt-4 py-3 rounded-lg font-bold
                  transition-all duration-300
                  ${file && !uploading
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {uploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processing...
                  </span>
                ) : (
                  'Validate Video'
                )}
              </button>
              
              {result && (
                <button 
                  onClick={resetUpload}
                  className="w-full mt-3 py-3 rounded-lg font-bold bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors"
                >
                  Try Another Video
                </button>
              )}
            </div>
            
            {/* RIGHT SIDE: Validation Results */}
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Validation Results
              </h2>
              
              {!result && !uploading && (
                <div className="flex items-center justify-center h-64 text-gray-400">
                  <div className="text-center">
                    <FileVideo className="w-16 h-16 mx-auto mb-4" />
                    <p>Upload a video to see validation results</p>
                  </div>
                </div>
              )}
              
              {uploading && (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <Loader2 className="w-16 h-16 mx-auto mb-4 text-blue-600 animate-spin" />
                    <p className="text-gray-600">Analyzing video...</p>
                  </div>
                </div>
              )}
              
              {result && result.error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2 text-red-800">
                    <XCircle className="w-5 h-5" />
                    <p className="font-semibold">{result.error}</p>
                  </div>
                </div>
              )}
              
              {result && !result.error && (
                <div>
                  <div className={`
                    p-4 rounded-lg mb-4
                    ${result.status === 'approved' || result.is_valid === true
                      ? 'bg-green-50 border border-green-200' 
                      : result.status === 'rejected' || result.is_valid === false
                      ? 'bg-red-50 border border-red-200'
                      : 'bg-yellow-50 border border-yellow-200'
                    }
                  `}>
                    <div className="flex items-center gap-3">
                      {result.status === 'approved' || result.is_valid === true ? (
                        <CheckCircle2 className="w-8 h-8 text-green-600" />
                      ) : result.status === 'rejected' || result.is_valid === false ? (
                        <XCircle className="w-8 h-8 text-red-600" />
                      ) : (
                        <Loader2 className="w-8 h-8 text-yellow-600 animate-spin" />
                      )}
                      <div>
                        <p className={`font-bold text-lg ${
                          result.status === 'approved' || result.is_valid === true
                            ? 'text-green-800'
                            : result.status === 'rejected' || result.is_valid === false
                            ? 'text-red-800'
                            : 'text-yellow-800'
                        }`}>
                          {result.status === 'approved' || result.is_valid === true
                            ? 'Video Approved!'
                            : result.status === 'rejected' || result.is_valid === false
                            ? 'Video Rejected!'
                            : 'Validation In Progress...'
                          }
                        </p>
                        <p className={`text-sm ${
                          result.status === 'approved' || result.is_valid === true
                            ? 'text-green-700'
                            : result.status === 'rejected' || result.is_valid === false
                            ? 'text-red-700'
                            : 'text-yellow-700'
                        }`}>
                          {result.message || 'Processing...'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}