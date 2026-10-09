import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { XIcon } from '../common/Icons';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export const AppShell: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('chemrag_sidebar_collapsed');
      return saved ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });

  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);

  useEffect(() => {
    try {
      localStorage.setItem('chemrag_sidebar_collapsed', JSON.stringify(isCollapsed));
    } catch {
      // Ignore localStorage errors
    }
  }, [isCollapsed]);

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => !prev);
  };

  const handleMobileToggle = () => {
    setIsMobileOpen((prev) => !prev);
  };

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
      {/* Top Header Navbar */}
      <Navbar
        onToggleSidebar={handleToggleCollapse}
        onMobileToggle={handleMobileToggle}
      />

      {/* Main Container: Sidebar + Scientific Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Desktop Collapsible Sidebar */}
        <div className="hidden md:block h-full">
          <Sidebar
            isCollapsed={isCollapsed}
            onToggleCollapse={handleToggleCollapse}
          />
        </div>

        {/* Mobile Slide-over Sidebar Drawer */}
        {isMobileOpen && (
          <div className="md:hidden fixed inset-0 z-50 flex">
            {/* Backdrop overlay */}
            <div
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
              onClick={() => setIsMobileOpen(false)}
            />

            {/* Slide-over Drawer */}
            <div className="relative flex-1 max-w-xs w-full bg-slate-900 h-full shadow-2xl z-10 border-r border-slate-800">
              <div className="absolute top-3 right-3 z-20">
                <button
                  onClick={() => setIsMobileOpen(false)}
                  type="button"
                  aria-label="Close Navigation Drawer"
                  className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <XIcon size={20} />
                </button>
              </div>

              <Sidebar
                isCollapsed={false}
                onToggleCollapse={() => {}}
                onMobileClose={() => setIsMobileOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Main Workspace Content Area */}
        <main className="flex-1 overflow-y-auto bg-slate-950 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AppShell;
