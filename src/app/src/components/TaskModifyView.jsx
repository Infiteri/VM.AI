import React, { useState } from "react";

const Toggle = ({ name, checked, onChange }) => (
    <div className="flex items-center gap-3">
        <span className="text-main-font text-sm font-medium">{name}</span>
        <label className="relative inline-flex items-center cursor-pointer">
            <input
                type="checkbox"
                className="sr-only peer"
                checked={checked}
                onChange={onChange}
            />
            <div className="w-11 h-5 bg-second rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-second peer-checked:after:bg-main-font after:rounded-full after:h-4 after:w-5 after:transition-all border border-main-font/20" />
        </label>
    </div>
);

const RangeSlider = ({ label, name, value, onChange }) => (
    <div className="flex flex-col gap-1 px-4 py-2 border border-main-font/20 rounded-xl">
        <span className="text-main-font/80 text-xs uppercase tracking-wider">{label}</span>
        <div className="relative flex items-center h-4">
            <div className="absolute w-full h-[1px] bg-main-font/20" />
            <div className="absolute left-1/2 w-[1px] h-3 bg-main-font/40 -translate-x-1/2" />
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

export default function TaskModifyView({ taskData }) {
    const {
        name: initName = "",
        duration: initDuration = 0,
        fixed: initFixed = false,
        recurrent: initRecurrent = false,
        recurrency: initRecurrency = [],
        start: initStart = "2026-01-01",
        startTime: initStartTime = "08:00",
        deadline: initDeadline = "2026-01-01",
        deadlineTime: initDeadlineTime = "08:00",
        difficulty: initDifficulty = 0.5,
        importance: initImportance = 0.5,
        location: initLocation = "",
        category: initCategory = "",
    } = taskData || {};

    const toISODate = (dateStr) => {
        if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) return dateStr;
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return "2026-01-01";
        return date.toISOString().split("T")[0];
    };

    const [task, setTask] = useState({
        name: initName,
        duration: initDuration,
        fixed: initFixed,
        recurrent: initRecurrent,
        recurrency: initRecurrency,
        start: toISODate(initStart),
        startTime: initStartTime,
        deadline: toISODate(initDeadline),
        deadlineTime: initDeadlineTime,
        difficulty: initDifficulty,
        importance: initImportance,
        location: initLocation,
        category: initCategory,
        realization: null,
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setTask((prev) => ({
            ...prev,
            [name]: type === "checkbox" ? checked : value,
        }));
    };

    const days = ["S", "M", "T", "W", "T", "F", "S"];
    const handleDayToggle = (index) => {
        setTask((prev) => {
            const newRecurrency = prev.recurrency.includes(index)
                ? prev.recurrency.filter((i) => i !== index)
                : [...prev.recurrency, index];
            return { ...prev, recurrency: newRecurrency };
        });
    };

    return (
        <div className="w-200 bg-main p-8 rounded-[40px] shadow-glow border border-white/5 flex flex-col gap-5">
            <h2 className="text-main-font text-2xl font-light text-center mb-2">
                Set up your new task
            </h2>

            <div className="flex gap-3">
                <input
                    name="name"
                    value={task.name}
                    onChange={handleChange}
                    placeholder="Name"
                    className="flex-1 bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
                />
                <div className="w-32 relative">
                    <input
                        name="duration"
                        type="number"
                        value={task.duration}
                        onChange={handleChange}
                        className="w-full bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all no-spinner pr-12 text-right"
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-main-font/40 text-sm italic">
                        min
                    </span>
                </div>
            </div>

            <div className="grid gap-3">
                <div className="flex flex-col gap-3 p-4 border border-main-font/20 rounded-xl min-h-[20px]">
                    <Toggle
                        name="Fixed"
                        checked={task.fixed}
                        onChange={(e) => setTask({ ...task, fixed: e.target.checked })}
                    />
                    {task.fixed && (
                        <span className="bg-sec/40 text-main-font/80 text-[11px] px-3 py-1.5 rounded-lg border border-main-font/10 w-fit">
                            {task.startTime}
                        </span>
                    )}
                </div>

            </div>

            {!task.fixed && (
                <div className="grid grid-cols-2 gap-3 animate-slide-in">
                    <div className="flex flex-col gap-2 p-3 border border-main-font/20 rounded-xl">
                        <span className="text-main-font/80 text-[10px] uppercase tracking-widest">
                            Start
                        </span>
                        <div className="flex gap-2">
                            <input
                                type="date"
                                value={task.start}
                                onChange={(e) => setTask({ ...task, start: e.target.value })}
                                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1 text-main-font text-xs flex-1 focus:border-main-font/40 outline-none"
                            />
                            <input
                                type="time"
                                value={task.startTime}
                                onChange={(e) => setTask({ ...task, startTime: e.target.value })}
                                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1 text-main-font text-xs focus:border-main-font/40 outline-none"
                            />
                        </div>
                    </div>
                    <div className="flex flex-col gap-2 p-3 border border-main-font/20 rounded-xl">
                        <span className="text-main-font/80 text-[10px] uppercase tracking-widest">
                            Deadline
                        </span>
                        <div className="flex gap-2">
                            <input
                                type="date"
                                value={task.deadline}
                                onChange={(e) => setTask({ ...task, deadline: e.target.value })}
                                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1 text-main-font text-xs flex-1 focus:border-main-font/40 outline-none"
                            />
                            <input
                                type="time"
                                value={task.deadlineTime}
                                onChange={(e) => setTask({ ...task, deadlineTime: e.target.value })}
                                className="bg-sec/40 border border-main-font/20 rounded-lg px-2 py-1 text-main-font text-xs focus:border-main-font/40 outline-none"
                            />
                        </div>
                    </div>
                </div>
            )}

            <RangeSlider
                label="Difficulty"
                name="difficulty"
                value={task.difficulty}
                onChange={handleChange}
            />
            <RangeSlider
                label="Importance"
                name="importance"
                value={task.importance}
                onChange={handleChange}
            />

            <input
                name="location"
                value={task.location}
                onChange={handleChange}
                placeholder="Location"
                className="w-full bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
            />

            <div className="relative">
                <input
                    name="category"
                    value={task.category}
                    onChange={handleChange}
                    placeholder="Category"
                    className="w-full bg-sec/40 border border-main-font/20 rounded-xl px-4 py-3 text-main-font placeholder:text-main-font/20 outline-none focus:border-main-font/40 transition-all"
                />
                <button className="absolute right-4 top-1/2 -translate-y-1/2 text-main-font text-xl font-light hover:scale-110 transition-transform">
                    +
                </button>
            </div>

            <button
                onClick={() => console.log(task)}
                className="w-full bg-main-font text-background font-bold py-4 rounded-2xl text-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-xl uppercase tracking-[0.2em] mt-2"
            >
                Submit task
            </button>
        </div>
    );
}