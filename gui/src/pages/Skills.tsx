import { useEffect, useState } from 'react';
import { Plus, Search, Trash2, Edit, Package } from 'lucide-react';
import { useAppStore } from '../stores/useAppStore';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { CreateSkillDialog } from '../components/CreateSkillDialog';
import { ConfirmDialog } from '../components/ConfirmDialog';
import type { Skill } from '../types';

export function Skills() {
  const {
    skills,
    selectedSkill,
    isLoadingSkills,
    fetchSkills,
    selectSkill,
    deleteSkill,
  } = useAppStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [skillToDelete, setSkillToDelete] = useState<Skill | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const filteredSkills = skills.filter((skill) =>
    skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    skill.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDeleteConfirm = async () => {
    if (!skillToDelete) return;

    setIsDeleting(true);
    try {
      await deleteSkill(skillToDelete.name);
      setSkillToDelete(null);
    } catch (error) {
      console.error('Failed to delete skill:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  return (
    <div className="flex h-full">
      {/* Left Panel - Skills List */}
      <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Skills
            </h1>
            <Button size="sm" onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              New
            </Button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>

        {/* Skills List */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-2">
          {isLoadingSkills ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Loading skills...
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="text-center py-8">
              <Package className="w-12 h-12 mx-auto text-gray-400 mb-2" />
              <p className="text-gray-500 dark:text-gray-400">
                {searchQuery ? 'No skills found' : 'No skills yet'}
              </p>
              {!searchQuery && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="mt-2"
                  onClick={() => setIsCreateDialogOpen(true)}
                >
                  Create your first skill
                </Button>
              )}
            </div>
          ) : (
            filteredSkills.map((skill) => (
              <Card
                key={skill.name}
                className={`cursor-pointer transition-all ${
                  selectedSkill?.name === skill.name
                    ? 'ring-2 ring-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : ''
                }`}
                onClick={() => selectSkill(skill)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 dark:text-white truncate">
                      {skill.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-1">
                      {skill.description || 'No description'}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                      Updated {formatDate(skill.updated_at)}
                    </p>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Right Panel - Skill Details */}
      <div className="flex-1 flex flex-col">
        {selectedSkill ? (
          <>
            {/* Detail Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {selectedSkill.name}
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">
                    {selectedSkill.description || 'No description'}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary">
                    <Edit className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => setSkillToDelete(selectedSkill)}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>

            {/* Detail Content */}
            <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
              <div className="space-y-6">
                {/* Metadata */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Metadata
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Created</p>
                      <p className="text-gray-900 dark:text-white">
                        {new Date(selectedSkill.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Updated</p>
                      <p className="text-gray-900 dark:text-white">
                        {new Date(selectedSkill.updated_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-sm text-gray-500 dark:text-gray-400">Hash</p>
                      <p className="text-xs text-gray-900 dark:text-white font-mono break-all">
                        {selectedSkill.hash}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-sm text-gray-500 dark:text-gray-400">Path</p>
                      <p className="text-xs text-gray-900 dark:text-white font-mono break-all">
                        {selectedSkill.path}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Usage */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Usage
                  </h3>
                  <Card className="bg-gray-50 dark:bg-gray-900/50">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Used in 0 projects
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                      Install this skill to projects from the Projects page
                    </p>
                  </Card>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Package className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                Select a skill to view details
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <CreateSkillDialog
        isOpen={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
      />

      <ConfirmDialog
        isOpen={!!skillToDelete}
        onClose={() => setSkillToDelete(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Skill"
        message={`Are you sure you want to delete "${skillToDelete?.name}"? This will remove it from the global repository.`}
        confirmText="Delete"
        isLoading={isDeleting}
        variant="danger"
      />
    </div>
  );
}
