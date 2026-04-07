import { useEffect } from 'react';
import { Package, FolderOpen, RefreshCw } from 'lucide-react';
import { useAppStore } from '../stores/useAppStore';
import { Card } from '../components/Card';

export function Dashboard() {
  const { dashboardStats, fetchDashboardStats } = useAppStore();

  useEffect(() => {
    fetchDashboardStats();
  }, [fetchDashboardStats]);

  const stats = [
    {
      label: 'Skills',
      value: dashboardStats?.total_skills || 0,
      icon: Package,
      color: 'text-blue-500',
    },
    {
      label: 'Projects',
      value: dashboardStats?.total_projects || 0,
      icon: FolderOpen,
      color: 'text-green-500',
    },
    {
      label: 'Synced Today',
      value: dashboardStats?.synced_today || 0,
      icon: RefreshCw,
      color: 'text-purple-500',
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Welcome to SkillStack
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-700 ${stat.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {stat.label}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stat.value}
                  </p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">
              Create New Skill
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Add a new skill to your global repository
            </p>
          </Card>
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <h3 className="font-medium text-gray-900 dark:text-white mb-2">
              Register Project
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Add a new project to manage its skills
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
