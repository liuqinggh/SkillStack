import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { RefreshCw, Info } from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { useAppStore } from '../stores/useAppStore';
import type { ProjectSkillMatrix } from '../types';

export function Matrix() {
  const [matrix, setMatrix] = useState<ProjectSkillMatrix | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<string>('all');
  const { addToast } = useAppStore();

  const fetchMatrix = async () => {
    setIsLoading(true);
    try {
      const data = await invoke<ProjectSkillMatrix>('get_project_skill_matrix');
      setMatrix(data);
    } catch (error) {
      console.error('Failed to fetch matrix:', error);
      addToast({
        type: 'error',
        message: `Failed to fetch matrix: ${error}`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMatrix();
  }, []);

  const handleToggle = async (projectName: string, skillName: string, currentlyInstalled: boolean) => {
    try {
      await invoke('toggle_project_skill', {
        projectName,
        skillName,
        install: !currentlyInstalled,
      });

      // Optimistic update
      if (matrix) {
        const newMatrix = { ...matrix };
        const projectIndex = newMatrix.projects.findIndex(p => p.name === projectName);
        const skillIndex = newMatrix.skills.findIndex(s => s.name === skillName);

        if (projectIndex !== -1 && skillIndex !== -1) {
          newMatrix.matrix[projectIndex][skillIndex].installed = !currentlyInstalled;

          // Update installed_skills list
          if (!currentlyInstalled) {
            newMatrix.projects[projectIndex].installed_skills.push(skillName);
          } else {
            newMatrix.projects[projectIndex].installed_skills =
              newMatrix.projects[projectIndex].installed_skills.filter(s => s !== skillName);
          }
          newMatrix.projects[projectIndex].skill_count = newMatrix.projects[projectIndex].installed_skills.length;

          setMatrix(newMatrix);
        }
      }

      addToast({
        type: 'success',
        message: `${!currentlyInstalled ? 'Installed' : 'Uninstalled'} ${skillName} ${!currentlyInstalled ? 'to' : 'from'} ${projectName}`,
      });
    } catch (error) {
      console.error('Failed to toggle skill:', error);
      addToast({
        type: 'error',
        message: `Failed to toggle skill: ${error}`,
      });
    }
  };

  const filteredProjects = matrix?.projects.filter(p =>
    selectedTool === 'all' || p.tool === selectedTool
  ) || [];

  const filteredMatrix = matrix ? matrix.matrix.filter((_, index) => {
    const project = matrix.projects[index];
    return selectedTool === 'all' || project.tool === selectedTool;
  }) : [];

  const tools = Array.from(new Set(matrix?.projects.map(p => p.tool) || []));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500 dark:text-gray-400">Loading matrix...</p>
      </div>
    );
  }

  if (!matrix || matrix.projects.length === 0 || matrix.skills.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Info className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 dark:text-gray-400 mb-2">
            {matrix?.projects.length === 0 ? 'No projects registered' : 'No skills available'}
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            {matrix?.projects.length === 0
              ? 'Register projects from the Projects page'
              : 'Create skills from the Skills page'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Project-Skill Matrix
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Manage which skills are installed in each project
            </p>
          </div>
          <Button size="sm" onClick={fetchMatrix}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </div>

        {/* Tool Filter */}
        {tools.length > 1 && (
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedTool('all')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                selectedTool === 'all'
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              All ({matrix.projects.length})
            </button>
            {tools.map(tool => (
              <button
                key={tool}
                onClick={() => setSelectedTool(tool)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
                  selectedTool === tool
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
              >
                {tool} ({matrix.projects.filter(p => p.tool === tool).length})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Matrix Table */}
      <div className="flex-1 overflow-auto p-6">
        <div className="inline-block min-w-full align-middle">
          <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider sticky left-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
                    Project
                  </th>
                  {matrix.skills.map(skill => (
                    <th
                      key={skill.name}
                      className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider min-w-[100px]"
                    >
                      <div className="flex flex-col items-center">
                        <span className="truncate max-w-[100px]" title={skill.name}>
                          {skill.name}
                        </span>
                      </div>
                    </th>
                  ))}
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider sticky right-0 bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredProjects.map((project) => {
                  const projectMatrixIndex = matrix.projects.findIndex(p => p.name === project.name);
                  const row = matrix.matrix[projectMatrixIndex];

                  return (
                    <tr key={project.name} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white sticky left-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
                        <div className="flex flex-col">
                          <span className="truncate max-w-[200px]" title={project.name}>
                            {project.name}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                            {project.tool}
                          </span>
                        </div>
                      </td>
                      {row.map((cell, skillIndex) => {
                        const skill = matrix.skills[skillIndex];
                        return (
                          <td
                            key={`${project.name}-${skill.name}`}
                            className="px-4 py-3 text-center"
                          >
                            <div className="flex items-center justify-center">
                              <input
                                type="checkbox"
                                checked={cell.installed}
                                onChange={() => handleToggle(project.name, skill.name, cell.installed)}
                                className="w-5 h-5 text-primary-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500 focus:ring-2 cursor-pointer"
                                title={cell.is_override ? 'Modified in project (override)' : ''}
                              />
                              {cell.is_override && (
                                <span className="ml-1 text-xs text-yellow-500" title="Project override">
                                  ⚠️
                                </span>
                              )}
                            </div>
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 text-sm text-center text-gray-900 dark:text-white font-medium sticky right-0 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
                        {project.skill_count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="bg-gray-50 dark:bg-gray-900 sticky bottom-0">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white sticky left-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
                    Total Projects
                  </td>
                  {matrix.skills.map(skill => {
                    const installedCount = filteredMatrix.reduce((count, row) => {
                      const skillIndex = matrix.skills.findIndex(s => s.name === skill.name);
                      return count + (row[skillIndex].installed ? 1 : 0);
                    }, 0);

                    return (
                      <td
                        key={skill.name}
                        className="px-4 py-3 text-sm text-center text-gray-900 dark:text-white font-medium"
                      >
                        {installedCount}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 text-sm text-center text-gray-500 dark:text-gray-400 sticky right-0 bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700">
                    {filteredProjects.length}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Legend */}
        <Card className="mt-6">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Legend</h3>
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <input type="checkbox" checked readOnly className="w-4 h-4" />
              <span>Skill installed</span>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" readOnly className="w-4 h-4" />
              <span>Skill not installed</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-yellow-500">⚠️</span>
              <span>Project override (modified version)</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
