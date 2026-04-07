import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';
import type { Skill, Project, DashboardStats, ViewMode, ToastMessage } from '../types';

interface AppState {
  // View state
  currentView: ViewMode;
  setCurrentView: (view: ViewMode) => void;

  // Skills state
  skills: Skill[];
  selectedSkill: Skill | null;
  isLoadingSkills: boolean;
  fetchSkills: () => Promise<void>;
  selectSkill: (skill: Skill | null) => void;
  createSkill: (name: string, description?: string) => Promise<void>;
  deleteSkill: (name: string) => Promise<void>;

  // Projects state
  projects: Project[];
  selectedProject: Project | null;
  isLoadingProjects: boolean;
  fetchProjects: () => Promise<void>;
  selectProject: (project: Project | null) => void;
  registerProject: (path: string, name?: string, tool?: string) => Promise<void>;
  unregisterProject: (name: string) => Promise<void>;

  // Dashboard state
  dashboardStats: DashboardStats | null;
  fetchDashboardStats: () => Promise<void>;

  // UI state
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;

  // Initialization
  isInitialized: boolean;
  checkInitialized: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // View state
  currentView: 'dashboard',
  setCurrentView: (view) => set({ currentView: view }),

  // Skills state
  skills: [],
  selectedSkill: null,
  isLoadingSkills: false,

  fetchSkills: async () => {
    set({ isLoadingSkills: true });
    try {
      const skills = await invoke<Skill[]>('get_skills');
      set({ skills, isLoadingSkills: false });
    } catch (error) {
      console.error('Failed to fetch skills:', error);
      get().addToast({
        type: 'error',
        message: `Failed to fetch skills: ${error}`,
      });
      set({ isLoadingSkills: false });
    }
  },

  selectSkill: (skill) => set({ selectedSkill: skill }),

  createSkill: async (name, description) => {
    try {
      await invoke('create_skill', { name, description });
      await get().fetchSkills();
      get().addToast({
        type: 'success',
        message: `Skill '${name}' created successfully`,
      });
    } catch (error) {
      console.error('Failed to create skill:', error);
      get().addToast({
        type: 'error',
        message: `Failed to create skill: ${error}`,
      });
      throw error;
    }
  },

  deleteSkill: async (name) => {
    try {
      await invoke('delete_skill', { name });
      await get().fetchSkills();
      set({ selectedSkill: null });
      get().addToast({
        type: 'success',
        message: `Skill '${name}' deleted successfully`,
      });
    } catch (error) {
      console.error('Failed to delete skill:', error);
      get().addToast({
        type: 'error',
        message: `Failed to delete skill: ${error}`,
      });
      throw error;
    }
  },

  // Projects state
  projects: [],
  selectedProject: null,
  isLoadingProjects: false,

  fetchProjects: async () => {
    set({ isLoadingProjects: true });
    try {
      const projects = await invoke<Project[]>('get_projects');
      set({ projects, isLoadingProjects: false });
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      get().addToast({
        type: 'error',
        message: `Failed to fetch projects: ${error}`,
      });
      set({ isLoadingProjects: false });
    }
  },

  selectProject: (project) => set({ selectedProject: project }),

  registerProject: async (path, name, tool = 'claude') => {
    try {
      await invoke('register_project', { path, name, tool });
      await get().fetchProjects();
      get().addToast({
        type: 'success',
        message: `Project registered successfully`,
      });
    } catch (error) {
      console.error('Failed to register project:', error);
      get().addToast({
        type: 'error',
        message: `Failed to register project: ${error}`,
      });
      throw error;
    }
  },

  unregisterProject: async (name) => {
    try {
      await invoke('unregister_project', { name });
      await get().fetchProjects();
      set({ selectedProject: null });
      get().addToast({
        type: 'success',
        message: `Project '${name}' unregistered successfully`,
      });
    } catch (error) {
      console.error('Failed to unregister project:', error);
      get().addToast({
        type: 'error',
        message: `Failed to unregister project: ${error}`,
      });
      throw error;
    }
  },

  // Dashboard state
  dashboardStats: null,

  fetchDashboardStats: async () => {
    try {
      const stats = await invoke<DashboardStats>('get_dashboard_stats');
      set({ dashboardStats: stats });
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
    }
  },

  // UI state
  toasts: [],

  addToast: (toast) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast = { ...toast, id };
    set((state) => ({ toasts: [...state.toasts, newToast] }));

    // Auto-remove after duration
    setTimeout(() => {
      get().removeToast(id);
    }, toast.duration || 3000);
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  // Initialization
  isInitialized: false,

  checkInitialized: async () => {
    try {
      const initialized = await invoke<boolean>('check_initialized');
      set({ isInitialized: initialized });
    } catch (error) {
      console.error('Failed to check initialization:', error);
      set({ isInitialized: false });
    }
  },

  initialize: async () => {
    try {
      await invoke('initialize_skillstack');
      set({ isInitialized: true });
      get().addToast({
        type: 'success',
        message: 'SkillStack initialized successfully',
      });
    } catch (error) {
      console.error('Failed to initialize:', error);
      get().addToast({
        type: 'error',
        message: `Failed to initialize: ${error}`,
      });
      throw error;
    }
  },
}));
