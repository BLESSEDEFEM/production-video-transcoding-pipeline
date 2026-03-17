'use client';

import { useRouter } from 'next/navigation';
import { Home, Video, LogOut } from 'lucide-react';

export default function Navbar() {
  const router = useRouter();

  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 4: Logout function
  // ═══════════════════════════════════════════════════════════
  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          
          {/* Left side - Logo/Brand */}
          <div className="flex items-center gap-2">
            <Video className="w-6 h-6 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">
              Video Transcoder
            </span>
          </div>

          {/* Right side - Navigation buttons */}
          <div className="flex items-center gap-4">
            
            {/* ═══════════════════════════════════════════════════════════
                NEW FEATURE 9: Home button (returns to upload page)
                ═══════════════════════════════════════════════════════════ */}
            <button
              onClick={() => router.push('/upload')}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <Home className="w-5 h-5" />
              <span className="font-semibold">Home</span>
            </button>

            {/* ═══════════════════════════════════════════════════════════
                NEW FEATURE 5: My Videos button
                ═══════════════════════════════════════════════════════════ */}
            <button
              onClick={() => router.push('/videos')}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <Video className="w-5 h-5" />
              <span className="font-semibold">My Videos</span>
            </button>

            {/* ═══════════════════════════════════════════════════════════
                NEW FEATURE 4: Logout button
                ═══════════════════════════════════════════════════════════ */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white hover:bg-red-600 rounded-lg transition-colors font-semibold"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}