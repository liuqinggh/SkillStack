import { useState } from 'react';
import { Modal } from './Modal';
import { Input } from './Input';
import { Button } from './Button';
import { useAppStore } from '../stores/useAppStore';

interface CreateSkillDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateSkillDialog({ isOpen, onClose }: CreateSkillDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { createSkill } = useAppStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate name
    if (!name.trim()) {
      setError('Skill name is required');
      return;
    }

    if (!/^[a-z][a-z0-9-]*$/.test(name)) {
      setError('Skill name must start with a letter and contain only lowercase letters, numbers, and hyphens');
      return;
    }

    setIsLoading(true);
    try {
      await createSkill(name.trim(), description.trim() || undefined);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create skill');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create New Skill">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Skill Name *"
          placeholder="e.g., debugging"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={error}
          disabled={isLoading}
          autoFocus
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            rows={3}
            placeholder="Brief description of what this skill does..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="flex gap-3 justify-end pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Creating...' : 'Create Skill'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
