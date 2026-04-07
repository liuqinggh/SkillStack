// ============================================================================
// Skill Types
// ============================================================================

export interface Skill {
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  hash: string;
  path: string;
}

// ============================================================================
// Project Types
// ============================================================================

export interface Project {
  name: string;
  path: string;
  tool: string;
  registered_at: string;
  installed_skills: string[];
  skill_count: number;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardStats {
  total_skills: number;
  total_projects: number;
  synced_today: number;
}

// ============================================================================
// Matrix Types
// ============================================================================

export interface ProjectSkillMatrix {
  projects: Project[];
  skills: Skill[];
  matrix: MatrixCell[][];
}

export interface MatrixCell {
  project_name: string;
  skill_name: string;
  installed: boolean;
  is_override: boolean;
}

// ============================================================================
// UI Types
// ============================================================================

export type ViewMode = 'dashboard' | 'skills' | 'projects' | 'matrix' | 'settings';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}
