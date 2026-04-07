import { useEffect } from 'react';
import { useAppStore } from './stores/useAppStore';
import { Sidebar } from './components/Sidebar';
import { ToastContainer } from './components/Toast';
import { Dashboard } from './pages/Dashboard';
import { Skills } from './pages/Skills';

function App() {
  const {
    currentView,
    setCurrentView,
    toasts,
    removeToast,
    isInitialized,
    checkInitialized,
  } = useAppStore();

  useEffect(() => {
    checkInitialized();
  }, [checkInitialized]);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            SkillStack
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            Initializing...
          </p>
        </div>
      </div>
    );
  }

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'skills':
        return <Skills />;
      case 'projects':
        return <div className="p-6"><h1 className="text-3xl font-bold">Projects (Coming Soon)</h1></div>;
      case 'settings':
        return <div className="p-6"><h1 className="text-3xl font-bold">Settings (Coming Soon)</h1></div>;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <main className="flex-1 overflow-hidden bg-white dark:bg-gray-800">
        {renderView()}
      </main>
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
}

export default App;
