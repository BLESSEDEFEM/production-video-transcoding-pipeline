'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import {
  Activity, Users, Video, Cpu, HardDrive,
  CheckCircle, XCircle, Clock, AlertTriangle,
  RefreshCw, Loader2, ChevronDown, ChevronUp
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────
// TYPE DEFINITIONS
// ─────────────────────────────────────────────────────────────────

interface SystemStats {
  users: { total: number };
  videos: {
    total: number;
    approved: number;
    rejected: number;
    completed: number;
  };
  jobs: {
    total: number;
    completed: number;
    failed: number;
    pending: number;
    processing: number;
    success_rate: number;
    avg_processing_time: number;
  };
  storage: {
    originals_mb: number;
    transcoded_mb: number;
    total_mb: number;
  };
}

interface AdminVideo {
  id: number;
  filename: string;
  owner: string;
  owner_email: string;
  status: string;
  file_size_mb: number;
  resolution: string;
  duration: number;
  transcoded_versions: number;
  jobs_completed: number;
  jobs_failed: number;
  jobs_total: number;
  created_at: string;
}

interface AdminJob {
  id: number;
  video_id: number;
  filename: string;
  owner: string;
  quality: string;
  status: string;
  verification_passed: boolean;
  processing_time: number | null;
  error_message: string | null;
  created_at: string;
}

interface ServiceHealth {
  status: string;
  error?: string;
  queue_length?: number;
  active_workers?: number;
  bucket?: string;
}

interface HealthStatus {
  overall: string;
  services: {
    [key: string]: ServiceHealth;
  };
}

// ─────────────────────────────────────────────────────────────────
// STAT CARD COMPONENT
// ─────────────────────────────────────────────────────────────────

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: any;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    gray: 'bg-gray-50 text-gray-700 border-gray-200',
  };

  const iconClasses: Record<string, string> = {
    blue: 'text-blue-500',
    green: 'text-green-500',
    red: 'text-red-500',
    purple: 'text-purple-500',
    orange: 'text-orange-500',
    gray: 'text-gray-500',
  };

  return (
    <div className={`rounded-xl border-2 p-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold opacity-80">{title}</span>
        <Icon className={`w-5 h-5 ${iconClasses[color]}`} />
      </div>
      <div className="text-3xl font-bold">{value}</div>
      {subtitle && (
        <div className="text-xs mt-1 opacity-70">{subtitle}</div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// STATUS BADGE COMPONENT
// ─────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-100 text-green-800',
    approved: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    rejected: 'bg-red-100 text-red-800',
    processing: 'bg-blue-100 text-blue-800',
    pending: 'bg-yellow-100 text-yellow-800',
    uploaded: 'bg-gray-100 text-gray-800',
    inspecting: 'bg-purple-100 text-purple-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────
// MAIN ADMIN PAGE
// ─────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [videos, setVideos] = useState<AdminVideo[]>([]);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'videos' | 'jobs'>('videos');
  const [jobFilter, setJobFilter] = useState<string>('');
  const [videoFilter, setVideoFilter] = useState<string>('');
  const [showHealth, setShowHealth] = useState(false);

  const router = useRouter();

  // ── Auth check ──
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    fetchAll();
  }, [router]);

  // ── Fetch all data ──
  const fetchAll = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [statsRes, videosRes, jobsRes, healthRes] = await Promise.all([
        axios.get('http://localhost:8000/api/admin/stats', { headers }),
        axios.get('http://localhost:8000/api/admin/videos?limit=100', { headers }),
        axios.get('http://localhost:8000/api/admin/jobs?limit=100', { headers }),
        axios.get('http://localhost:8000/api/admin/health', { headers }),
      ]);

      setStats(statsRes.data);
      setVideos(videosRes.data.videos);
      setJobs(jobsRes.data.jobs);
      setHealth(healthRes.data);
    } catch (error: any) {
      if (error.response?.status === 401) {
        router.push('/login');
      }
      console.error('Failed to fetch admin data:', error);
    }
    setLoading(false);
  };

  // ── Refresh handler ──
  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAll();
    setRefreshing(false);
  };

  // ── Auto-refresh every 30 seconds ──
  useEffect(() => {
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  // ── Filter videos ──
  const filteredVideos = videoFilter
    ? videos.filter(v => v.status === videoFilter)
    : videos;

  // ── Filter jobs ──
  const filteredJobs = jobFilter
    ? jobs.filter(j => j.status === jobFilter)
    : jobs;

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

      <div className="max-w-7xl mx-auto px-4 py-8">

        {/* ── HEADER ── */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-1">
              Admin Dashboard
            </h1>
            <p className="text-gray-600">
              System overview and monitoring
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-semibold text-gray-700"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* ── STAT CARDS (top row) ── */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatCard
              title="Total Users"
              value={stats.users.total}
              icon={Users}
              color="purple"
            />
            <StatCard
              title="Total Videos"
              value={stats.videos.total}
              subtitle={`${stats.videos.completed} completed`}
              icon={Video}
              color="blue"
            />
            <StatCard
              title="Total Jobs"
              value={stats.jobs.total}
              subtitle={`${stats.jobs.success_rate}% success rate`}
              icon={Cpu}
              color="green"
            />
            <StatCard
              title="Failed Jobs"
              value={stats.jobs.failed}
              icon={XCircle}
              color="red"
            />
            <StatCard
              title="Avg Time"
              value={`${stats.jobs.avg_processing_time}s`}
              subtitle="per job"
              icon={Clock}
              color="orange"
            />
            <StatCard
              title="Storage"
              value={`${stats.storage.total_mb} MB`}
              subtitle={`${stats.storage.originals_mb} orig + ${stats.storage.transcoded_mb} trans`}
              icon={HardDrive}
              color="gray"
            />
          </div>
        )}

        {/* ── SYSTEM HEALTH (collapsible) ── */}
        <div className="bg-white rounded-xl shadow-lg mb-8 overflow-hidden">
          <button
            onClick={() => setShowHealth(!showHealth)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-gray-600" />
              <span className="font-semibold text-gray-900">System Health</span>
              {health && (
                <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                  health.overall === 'healthy'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {health.overall}
                </span>
              )}
            </div>
            {showHealth
              ? <ChevronUp className="w-5 h-5 text-gray-400" />
              : <ChevronDown className="w-5 h-5 text-gray-400" />
            }
          </button>

          {showHealth && health && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(health.services).map(([name, info]) => (
                  <div
                    key={name}
                    className={`p-4 rounded-lg border-2 ${
                      info.status === 'healthy'
                        ? 'border-green-200 bg-green-50'
                        : 'border-red-200 bg-red-50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {info.status === 'healthy'
                        ? <CheckCircle className="w-5 h-5 text-green-600" />
                        : <XCircle className="w-5 h-5 text-red-600" />
                      }
                      <span className="font-bold text-gray-900 capitalize">{name}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {info.status === 'healthy' ? (
                        <>
                          {name === 'redis' && info.queue_length !== undefined && (
                            <div>Queue: {info.queue_length} jobs | Workers: {info.active_workers}</div>
                          )}
                          {name === 'minio' && info.bucket && (
                            <div>Bucket: {info.bucket}</div>
                          )}
                          {name === 'database' && <div>Connected</div>}
                        </>
                      ) : (
                        <div className="text-red-700">{info.error}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── TAB SWITCHER ── */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('videos')}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              activeTab === 'videos'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            Videos ({videos.length})
          </button>
          <button
            onClick={() => setActiveTab('jobs')}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              activeTab === 'jobs'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            Jobs ({jobs.length})
          </button>
        </div>

        {/* ── VIDEOS TABLE ── */}
        {activeTab === 'videos' && (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            {/* Filter bar */}
            <div className="p-4 border-b border-gray-200 flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-600">Filter:</span>
              {['', 'uploaded', 'approved', 'rejected', 'completed', 'failed'].map(f => (
                <button
                  key={f}
                  onClick={() => setVideoFilter(f)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                    videoFilter === f
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {f || 'All'}
                </button>
              ))}
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Filename</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Owner</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Resolution</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Size</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Jobs</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredVideos.map(video => (
                    <tr key={video.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-gray-900 font-mono">#{video.id}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 font-semibold max-w-48 truncate">
                        {video.filename}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{video.owner}</td>
                      <td className="px-4 py-3"><StatusBadge status={video.status} /></td>
                      <td className="px-4 py-3 text-sm text-gray-600">{video.resolution}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{video.file_size_mb} MB</td>
                      <td className="px-4 py-3 text-sm">
                        <span className="text-green-600 font-semibold">{video.jobs_completed}</span>
                        {video.jobs_failed > 0 && (
                          <span className="text-red-600 font-semibold"> / {video.jobs_failed} failed</span>
                        )}
                        <span className="text-gray-400"> / {video.jobs_total}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {video.created_at
                          ? new Date(video.created_at).toLocaleDateString()
                          : '-'
                        }
                      </td>
                    </tr>
                  ))}
                  {filteredVideos.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                        No videos found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── JOBS TABLE ── */}
        {activeTab === 'jobs' && (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            {/* Filter bar */}
            <div className="p-4 border-b border-gray-200 flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-600">Filter:</span>
              {['', 'pending', 'processing', 'completed', 'failed'].map(f => (
                <button
                  key={f}
                  onClick={() => setJobFilter(f)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                    jobFilter === f
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {f || 'All'}
                </button>
              ))}
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Job ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Video</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Owner</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Quality</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Verified</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredJobs.map(job => (
                    <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-gray-900 font-mono">#{job.id}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-40 truncate">
                        {job.filename}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{job.owner}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-gray-900">{job.quality}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 text-center">
                        {job.status === 'completed' && (
                          job.verification_passed
                            ? <CheckCircle className="w-4 h-4 text-green-600 inline" />
                            : <AlertTriangle className="w-4 h-4 text-yellow-600 inline" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {job.processing_time ? `${job.processing_time}s` : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-red-600 max-w-48 truncate">
                        {job.error_message || '-'}
                      </td>
                    </tr>
                  ))}
                  {filteredJobs.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                        No jobs found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}