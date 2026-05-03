import { useState, useEffect } from "react";
import { MapPin } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Background from "../components/Background";
import TaskView from "../components/TaskView";
import type { Task, UnscheduledTask } from "../types/Task";
import { api } from "../services/api";

function ScheduleChangesView({ loading }: { loading: boolean }) {
    if (loading) {
        return <div className="text-second-font">Loading...</div>;
    }
    return (
        <div className="w-full grid grid-cols-4 auto-rows-fr gap-4">
            <div className="text-second-font p-4">No pending schedule changes</div>
        </div>
    );
}

function UnscheduledTaskView({ task, onDelete }: { task: UnscheduledTask; onDelete: (id: string) => void }) {
    const navigate = useNavigate();
    const t = task.task;
    const startTime = t.start ? t.start.split("T")[1]?.substring(0, 5) : "";

    const handleModify = () => {
        navigate("/task", { state: { task: t, openMode: "modify" } });
    };

    const handleDelete = () => {
        onDelete(task.task_id);
    };

    return (
        <div className="flex flex-col gap-3 p-4 border border-white/20 rounded-lg bg-white/5">
            <div className="flex flex-row items-center justify-between">
                <span className="text-lg text-main-font font-medium">{t.name}</span>
                <span className="text-sm text-second-font">{startTime}</span>
            </div>
            <div className="flex flex-row gap-2">
                {t.location && (
                    <div className="flex flex-row items-center gap-1.5 px-2 py-1 rounded-md bg-white/5 border border-white/10">
                        <MapPin className="w-3.5 h-3.5 text-second-font" />
                        <span className="text-xs text-second-font">{t.location}</span>
                    </div>
                )}
            </div>
            <div className="flex justify-between mt-1 px-1 text-[9px] font-medium uppercase tracking-tighter">
                <button onClick={handleModify} className="text-second hover:text-main transition-colors">Modify</button>
                <button onClick={handleDelete} className="text-second hover:text-del transition-colors">Delete</button>
            </div>
        </div>
    );
}

function UnscheduledChangesView({ tasks, loading, onDelete }: { tasks: UnscheduledTask[]; loading: boolean; onDelete: (id: string) => void }) {
    if (loading) {
        return <div className="text-second-font">Loading...</div>;
    }
    if (tasks.length === 0) {
        return (
            <div className="w-full grid grid-cols-4 auto-rows-fr gap-4">
                <div className="text-second-font p-4">No unscheduled tasks</div>
            </div>
        );
    }
    return (
        <div className="w-full grid grid-cols-4 auto-rows-fr gap-4">
            {tasks.map((t) => (
                <UnscheduledTaskView key={t.task_id} task={t} onDelete={onDelete} />
            ))}
        </div>
    );
}

export default function PendingTasksPage() {
    const [activeView, setActiveView] = useState("unscheduled");
    const [unscheduledTasks, setUnscheduledTasks] = useState<UnscheduledTask[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const fetchUnscheduled = async () => {
        setLoading(true);
        try {
            const response = await api.getUnscheduledTasks();
            setUnscheduledTasks(response.tasks);
            setError("");
        } catch (err) {
            setError("Failed to fetch tasks");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUnscheduled();
    }, []);

    const handleDelete = async (taskId: string) => {
        try {
            await api.deleteTask(taskId, "unscheduled");
            fetchUnscheduled();
        } catch (err) {
            console.error("Failed to delete task:", err);
        }
    };

    const handleSchedule = async () => {
        setLoading(true);
        try {
            await api.runScheduler();
            fetchUnscheduled();
        } catch (err) {
            console.error("Failed to run scheduler:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        try {
            await api.resetProvisional();
        } catch (err) {
            console.error("Failed to reset:", err);
        }
    };

    const handleCommit = async () => {
        try {
            await api.commitProvisional();
        } catch (err) {
            console.error("Failed to commit:", err);
        }
    };

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
                                        <button onClick={handleReset} className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                            Reset to main schedule
                                        </button>
                                        <button onClick={handleCommit} className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                            Submit changes
                                        </button>
                                    </>
                                ) : (
                                    <button onClick={handleSchedule} disabled={loading} className="border border-main-font/30 text-main-font py-4 px-6 rounded-xl text-sm font-medium tracking-wide hover:bg-main-font/10 transition-all">
                                        {loading ? "Scheduling..." : "Schedule the tasks"}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 p-8">
                        {error && <div className="text-red-500 mb-4">{error}</div>}
                        {activeView === "schedule" ? (
                            <ScheduleChangesView loading={loading} />
                        ) : (
                            <UnscheduledChangesView tasks={unscheduledTasks} loading={loading} onDelete={handleDelete} />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}