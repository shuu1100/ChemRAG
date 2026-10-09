import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ChatPage } from './pages/ChatPage';
import { ChemicalExplorerPage } from './pages/ChemicalExplorerPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { DocumentViewerPage } from './pages/DocumentViewerPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { JobsPage } from './pages/JobsPage';
import { PagePlaceholder } from './pages/PagePlaceholder';
import { SearchPage } from './pages/SearchPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="viewer" element={<DocumentViewerPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="chemical" element={<ChemicalExplorerPage />} />
          <Route path="experiments" element={<ExperimentsPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="settings" element={<SettingsPage />} />
          {/* Catch-all fallback route */}
          <Route path="*" element={<PagePlaceholder />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
