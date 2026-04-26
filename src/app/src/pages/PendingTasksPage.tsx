import { useState } from "react";
import { MapPin, Dumbbell, BookOpen, MessageSquare, ShoppingCart, Utensils, Code, Moon, Pencil, Trash2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Background from "../components/Background";
import TaskView from "../components/TaskView";
import type { Task } from "../types/Task";

interface TaskWithIcon extends Task {
  icon?: LucideIcon;
}

const tasks: TaskWithIcon[] = [
    { name: "Morning Gym", location: "Gold's Gym", start: "06:00", duration: "90", difficulty: "0.7", importance: "0.8", fixed_time: true, fixed_start: null, recurrent: false, recurrence_days: null, category: ["fitness"], deadline: null, created_at: "", updated_at: "", icon: Dumbbell },
    { name: "Math Class", location: "School", start: "08:00", duration: "90", difficulty: "0.6", importance: "0.7", fixed_time: true, fixed_start: null, recurrent: false, recurrence_days: null, category: ["education"], deadline: null, created_at: "", updated_at: "", icon: BookOpen },
    { name: "Project Sync", location: "Discord", start: "11:00", duration: "60", difficulty: "0.5", importance: "0.6", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["work"], deadline: null, created_at: "", updated_at: "", icon: MessageSquare },
    { name: "Grocery Run", location: "Whole Foods", start: "17:00", duration: "60", difficulty: "0.3", importance: "0.7", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["personal"], deadline: null, created_at: "", updated_at: "", icon: ShoppingCart },
    { name: "Dinner Date", location: "Pasta Place", start: "19:30", duration: "90", difficulty: "0.4", importance: "0.9", fixed_time: true, fixed_start: null, recurrent: false, recurrence_days: null, category: ["social"], deadline: null, created_at: "", updated_at: "", icon: Utensils },
    { name: "Review Code", location: "Office", start: "21:30", duration: "60", difficulty: "0.8", importance: "0.6", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["work"], deadline: null, created_at: "", updated_at: "", icon: Code },
    { name: "Meditation", location: "Headspace", start: "23:00", duration: "30", difficulty: "0.2", importance: "0.5", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["wellness"], deadline: null, created_at: "", updated_at: "", icon: Moon }
];

function ScheduleChangesView() {
    return (
        <div className="w-full grid grid-cols-4 auto-rows-fr gap-4">
            {
                tasks.map((t, i) => <TaskView task={t} key={i} />)
            }
        </div>
    );
}

function UnscheduledTaskView({ task }: { task: TaskWithIcon }) {
    const navigate = useNavigate();
    const tags = task.location ? [{ icon: MapPin, value: task.location }] : [];

    const handleModify = () => {
        const plainTask = {
            name: task.name,
            start: task.start,
            deadline: task.deadline,
            duration: task.duration,
            difficulty: task.difficulty,
            location: task.location,
            importance: task.importance,
            fixed_time: task.fixed_time,
            fixed_start: task.fixed_start,
            recurrent: task.recurrent,
            recurrence_days: task.recurrence_days,
            category: task.category,
        };
        navigate("/task", { state: { task: plainTask, openMode: "modify" } });
    };

    const handleDelete = () => {
        console.log("Delete task:", task.name);
    };

    return (
        <div className="flex flex-col gap-3 p-4 border border-white/20 rounded-lg bg-white/5">
            <div className="flex flex-row items-center justify-between">
                <span className="text-lg text-main-font font-medium">{task.name}</span>
                <span className="text-sm text-second-font">{task.start}</span>
            </div>
            <div className="flex flex-row gap-2">
                {tags.map((tag, i) => {
                    const TagIcon = tag.icon;
                    return (
                        <div key={i} className="flex flex-row items-center gap-1.5 px-2 py-1 rounded-md bg-white/5 border border-white/10">
                            <TagIcon className="w-3.5 h-3.5 text-second-font" />
                            <span className="text-xs text-second-font">{tag.value}</span>
                        </div>
                    );
                })}
            </div>
            <div className="flex justify-between mt-1 px-1 text-[9px] font-medium uppercase tracking-tighter">
                <button onClick={handleModify} className="text-second hover:text-main transition-colors">Modify</button>
                <button onClick={handleDelete} className="text-second hover:text-del transition-colors">Delete</button>
            </div>
        </div>
    );
}

function UnscheduledChangesView() {
    return (
        <div className="w-full grid grid-cols-4 auto-rows-fr gap-4">
            {
                tasks.map((t, i) => <UnscheduledTaskView task={t} key={i} />)
            }
        </div>
    );
}

export default function PendingTasksPage() {
    const [activeView, setActiveView] = useState("schedule");

    return (
        <div className="w-screen h-screen flex overflow-hidden">
            <Background />
            <Sidebar />

            <div className="flex-1 flex items-center justify-center p-12">
                <div className="w-275 h-175 rounded-[40px] border border-white/5 bg-sec/30 shadow-2xl backdrop-blur-xl flex flex-col overflow-hidden">
                    <div className="p-6 border-b border-white/5">
                        <div className="flex flex-row items-center justify-between">
                            <div className="flex flex-row gap-3">
                                <button
                                    onClick={() => setActiveView("schedule")}
                                    className={`
                                        px-6 py-4 rounded-xl text-sm font-medium tracking-wide transition-all duration-200
                                        border backdrop-blur-md
                                        ${activeView === "schedule"
                                            ? "border-main-font/40 bg-main-font/10 text-main-font"
                                            : "border-white/10 bg-sec/20 text-main/60 hover:text-main hover:border-white/20"
                                        }
                                    `}
                                >
                                    Schedule Changes
                                </button>

                                <button
                                    onClick={() => setActiveView("unscheduled")}
                                    className={`
                                        px-6 py-4 rounded-xl text-sm font-medium tracking-wide transition-all duration-200
                                        border backdrop-blur-md
                                        ${activeView === "unscheduled"
                                            ? "border-main-font/40 bg-main-font/10 text-main-font"
                                            : "border-white/10 bg-sec/20 text-main/60 hover:text-main hover:border-white/20"
                                        }
                                    `}
                                >
                                    Unscheduled Changes
                                </button>
                            </div>

                            <div className="flex flex-row gap-3">
                                {activeView === "schedule" ? (
                                    <>
                                        <button className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                            Reset to main schedule
                                        </button>
                                        <button className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                            Submit changes
                                        </button>
                                    </>
                                ) : (
                                    <button className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                        Schedule the tasks
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 p-8">
                        {activeView === "schedule" ? <ScheduleChangesView /> : <UnscheduledChangesView />}
                    </div>
                </div>
            </div>
        </div>
    );
}