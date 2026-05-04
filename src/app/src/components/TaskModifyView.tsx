import type { Task } from "../types/Task";
import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { useNavigate } from "react-router-dom";

interface ToggleProps {
  name: string;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const Toggle = ({ name, checked, onChange }: ToggleProps) => (
  <div className="flex items-center gap-3">
    <span className="text-main-font text-sm font-medium">{name}</span>
    <label className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        className="sr-only peer"
        checked={checked}
        onChange={onChange}
      />
      <div className="w-11 h-5 bg-second rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-second peer-checked:after:bg-main-font after:rounded-full after:h-4 after:w-5 after:transition-all border border-main-font/20" />
    </label>
  </div>
);

interface RangeSliderProps {
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const RangeSlider = ({ label, name, value, onChange }: RangeSliderProps) => (
  <div className="flex flex-col gap-1 px-4 py-2 border border-main-font/20 rounded-xl">
    <span className="text-main-font/80 text-xs uppercase tracking-wider">{label}</span>
    <div className="relative flex items-center h-4">
      <div className="absolute w-full h-px bg-main-font/20" />
      <div className="absolute left-1/2 w-px h-3 bg-main-font/40 -translate-x-1/2" />
      <input
        type="range"
        name={name}
        min="0"
        max="1"
        step="0.1"
        value={value}
        onChange={onChange}
        className="absolute w-full appearance-none bg-transparent cursor-pointer z-10 accent-main-font"
      />
    </div>
  </div>
);

interface TaskModifyProps {
  task?: Task;
  onUpdate?: (task: Task) => void;
  openMode?: "add" | "modify";
  taskId?: string;
}

function formatDateForInput(isoDate: string | null): string {
  if (!isoDate) return "";
  return isoDate.split("T")[0];
}

function formatTimeForInput(isoDate: string | null): string {
  if (!isoDate) return "";
  return isoDate.split("T")[1]?.substring(0, 5) || "";
}

function toISODateTime(dateStr: string, timeStr: string): string | null {
  if (!dateStr || !timeStr) return null;
  const d = new Date(`${dateStr}T${timeStr}:00`);
  return d.toISOString();
}

function toFullDateTime(dateStr: string, defaultHour: number = 0): string | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  d.setHours(defaultHour, 0, 0, 0);
  const iso = d.toISOString();
  return iso.substring(0, 19) + "+00:00";
}

function toBackendDateTime(isoDate: string | null): string | null {
  if (!isoDate) return null;
  const d = new Date(isoDate);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  const secs = String(d.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${mins}:${secs}`;
}

export default function TaskModifyView({ task, onUpdate, openMode = "add", taskId }: TaskModifyProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const defaultTask: Task = {
    name: "",
    start: null,
    deadline: null,
    duration: 30,
    difficulty: 0.5,
    location: "",
    importance: 0.5,
    fixed_time: false,
    fixed_start: null,
    category: [],
  };

  const [formData, setFormData] = useState<Task>(task ?? defaultTask);

  useEffect(() => {
    if (task) {
      setFormData(task);
      if (task.fixed_start) {
        setFixedDate(task.fixed_start.split("T")[0]);
        setFixedTime(task.fixed_start.split("T")[1]?.slice(0, 5) ?? "");
      } else {
        setFixedDate("");
        setFixedTime("");
      }
    }
  }, [task]);

  const [fixedDate, setFixedDate] = useState(
    formData.fixed_start ? formData.fixed_start.split("T")[0] : ""
  );
  const [fixedTime, setFixedTime] = useState(
    formData.fixed_start ? formData.fixed_start.split("T")[1]?.slice(0, 5) : ""
  );
  const [categoryInput, setCategoryInput] = useState("");

  const handleFixedToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const isFixed = e.target.checked;
    if (isFixed) {
      setFormData((prev) => ({
        ...prev,
        fixed_time: true,
        start: null,
        deadline: null,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        fixed_time: false,
        fixed_start: null,
      }));
      setFixedDate("");
      setFixedTime("");
    }
  };

  const handleFixedDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const dateVal = e.target.value;
    setFixedDate(dateVal);
    if (dateVal && fixedTime) {
      const iso = toISODateTime(dateVal, fixedTime);
      setFormData((prev) => ({ ...prev, fixed_start: iso }));
    } else {
      setFormData((prev) => ({ ...prev, fixed_start: null }));
    }
  };

  const handleFixedTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const timeVal = e.target.value;
    setFixedTime(timeVal);
    if (fixedDate && timeVal) {
      const iso = toISODateTime(fixedDate, timeVal);
      setFormData((prev) => ({ ...prev, fixed_start: iso }));
    } else {
      setFormData((prev) => ({ ...prev, fixed_start: null }));
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (name === "duration" || name === "difficulty" || name === "importance") {
      setFormData((prev) => ({
        ...prev,
        [name]: parseFloat(value) || 0,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  const handleCategoryAdd = () => {
    if (categoryInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        category: [...prev.category, categoryInput.trim()],
      }));
      setCategoryInput("");
    }
  };

  const handleCategoryKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleCategoryAdd();
    }
  };

  return (
    <div className="w-200 bg-main p-8 rounded-[40px] shadow-glow border border-white/5 flex flex-col gap-5">
      <h2 className="text-main-font text-2xl font-light text-center mb-2">
        Set up your new task
      </h2>

      <div className="flex gap-3">
        <input
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="Name"
          className="flex-1 bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
        />
        <div className="w-32 relative">
          <input
            name="duration"
            type="number"
            value={String(formData.duration)}
            onChange={handleChange}
            className="w-full bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all no-spinner pr-12 text-right"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-main-font/40 text-sm italic">
            min
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-3 p-4 border border-main-font/20 rounded-xl">
        <Toggle
          name="Fixed time"
          checked={formData.fixed_time}
          onChange={handleFixedToggle}
        />

        {formData.fixed_time ? (
          <div className="flex gap-2 animate-fade-in">
            <input
              type="date"
              value={fixedDate}
              onChange={handleFixedDateChange}
              className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1.5 text-main-font text-xs flex-1 focus:border-main-font/40 outline-none"
            />
            <input
              type="time"
              value={fixedTime}
              onChange={handleFixedTimeChange}
              className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1.5 text-main-font text-xs focus:border-main-font/40 outline-none"
            />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 animate-fade-in">
            <div className="flex flex-col gap-2">
              <span className="text-main-font/80 text-[10px] uppercase tracking-widest">
                Start
              </span>
              <input
                type="date"
                value={formatDateForInput(formData.start)}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    start: toFullDateTime(e.target.value, 9),
                  }))
                }
                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1.5 text-main-font text-xs flex-1 focus:border-main-font/40 outline-none"
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-main-font/80 text-[10px] uppercase tracking-widest">
                Deadline
              </span>
              <input
                type="date"
                value={formatDateForInput(formData.deadline)}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    deadline: toFullDateTime(e.target.value, 23),
                  }))
                }
                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1.5 text-main-font text-xs flex-1 focus:border-main-font/40 outline-none"
              />
            </div>
          </div>
        )}
      </div>

      <RangeSlider
        label="Difficulty"
        name="difficulty"
        value={String(formData.difficulty)}
        onChange={handleChange}
      />
      <RangeSlider
        label="Importance"
        name="importance"
        value={String(formData.importance)}
        onChange={handleChange}
      />

      <input
        name="location"
        value={formData.location ?? ""}
        onChange={handleChange}
        placeholder="Location"
        className="w-full bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
      />



      <div className="flex gap-2">
        <input
          name="category"
          value={categoryInput}
          onChange={(e) => setCategoryInput(e.target.value)}
          onKeyDown={handleCategoryKeyDown}
          placeholder="Category"
          className="flex-1 bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
        />
        <button
          type="button"
          onClick={handleCategoryAdd}
          className="w-12 bg-sec/40 border border-main-font/20 rounded-xl text-main-font text-xl font-light hover:bg-main-font/10 transition-all"
        >
          +
        </button>
      </div>

      {formData.category.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {formData.category.map((cat, i) => (
            <span
              key={i}
              className="px-3 py-1.5 bg-sec/40 border border-main-font/20 rounded-lg text-main-font text-sm flex items-center gap-2"
            >
              {cat}
              <button
                type="button"
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    category: prev.category.filter((_, idx) => idx !== i),
                  }))
                }
                className="text-main-font/60 hover:text-main-font"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <button
        onClick={async () => {
          if (!formData.name) {
            alert("Please enter a task name");
            return;
          }
          if (formData.category.length === 0) {
            alert("Please add at least one category");
            return;
          }
          if (!formData.location) {
            alert("Please enter a location");
            return;
          }
          
          if (!formData.fixed_time && formData.start && formData.deadline) {
            if (new Date(formData.start) >= new Date(formData.deadline)) {
              alert("Start time must be before deadline");
              return;
            }
          }
          
          setLoading(true);
          try {
            let finalFixedStart = formData.fixed_start;
            if (formData.fixed_time && !finalFixedStart) {
              const now = new Date();
              now.setHours(12, 0, 0, 0);
              finalFixedStart = now.toISOString();
            }
            
            const taskToSend = {
              name: formData.name,
              duration: formData.duration,
              difficulty: formData.difficulty,
              importance: formData.importance,
              category: formData.category,
              location: formData.location,
              fixed_time: formData.fixed_time,
              start: formData.fixed_time ? null : toBackendDateTime(formData.start),
              deadline: formData.fixed_time ? null : toBackendDateTime(formData.deadline),
              fixed_start: formData.fixed_time ? toBackendDateTime(finalFixedStart) : null,
            };

            if (openMode === "modify" && taskId) {
              await api.updateTask(taskId, taskToSend, "main_schedule");
            } else {
              console.log("Sending task:", JSON.stringify(taskToSend));
              console.log("Calling API...");
              await api.createTask(taskToSend);
              console.log("API call done");
            }
            navigate("/pending");
          } catch (err: any) {
            console.error("Failed to create task:", err);
            const errorMsg = err instanceof Error ? err.message : JSON.stringify(err);
            alert("Failed to create task: " + errorMsg);
          } finally {
            setLoading(false);
          }
        }}
        disabled={loading}
        className="w-full bg-main-font text-background font-bold py-4 rounded-2xl text-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-xl uppercase tracking-[0.2em] mt-2"
      >
        {loading ? "Creating..." : "Submit task"}
      </button>
    </div>
  );
}