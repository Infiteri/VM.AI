export interface Task {
  name: string;
  start: string | null;
  deadline: string | null;
  duration: string;
  difficulty: string;
  location: string | null;
  importance: string;
  fixed_time: boolean;
  fixed_start: string | null;
  recurrent: boolean;
  recurrence_days: string[] | null;
  category: string[];
  created_at: string;
  updated_at: string;
}

export function createDefaultTask(): Task {
  return {
    name: "",
    start: null,
    deadline: null,
    duration: "30",
    difficulty: "0.5",
    location: null,
    importance: "0.5",
    fixed_time: false,
    fixed_start: null,
    recurrent: false,
    recurrence_days: null,
    category: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}