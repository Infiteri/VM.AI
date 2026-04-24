import { useState } from "react";
import { MapPin, Clock, Calendar, Dumbbell, BookOpen, MessageSquare, ShoppingCart, Utensils, Code, Moon, MoreHorizontal } from "lucide-react";
import Sidebar from "../components/Sidebar";
import Background from "../components/Background";
import TaskView from "../components/TaskView";

const tasks = [
    { id: 1, name: "Morning Gym", locationLabel: "Location", locationValue: "Gold's Gym", startTime: "06:00", endTime: "07:30", icon: Dumbbell },
    { id: 2, name: "Math Class", locationLabel: "Location", locationValue: "School", startTime: "08:00", endTime: "09:30", icon: BookOpen },
    { id: 3, name: "Project Sync", locationLabel: "Location", locationValue: "Discord", startTime: "11:00", endTime: "12:00", icon: MessageSquare },
    { id: 4, name: "Grocery Run", locationLabel: "Store", locationValue: "Whole Foods", startTime: "17:00", endTime: "18:00", icon: ShoppingCart },
    { id: 5, name: "Dinner Date", locationLabel: "Venue", locationValue: "Pasta Place", startTime: "19:30", endTime: "21:00", icon: Utensils },
    { id: 6, name: "Review Code", locationLabel: "Home", locationValue: "Office", startTime: "21:30", endTime: "22:30", icon: Code },
    { id: 7, name: "Meditation", locationLabel: "App", locationValue: "Headspace", startTime: "23:00", endTime: "23:30", icon: Moon }
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

function UnscheduledTaskView({ task }) {
    const Icon = task.icon;

    const tags = [
        { icon: MapPin, value: task.locationValue }
    ];

    return (
        <div className="flex flex-col gap-3 p-4 border border-white/20 rounded-lg bg-white/5">
            <div className="flex flex-row items-center justify-between">
                <span className="text-lg text-main-font font-medium">{task.name}</span>
                <span className="text-sm text-second-font">{task.startTime} - {task.endTime}</span>
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
                <div className="w-[1100px] h-[700px] rounded-[40px] border border-white/5 bg-sec/30 shadow-2xl backdrop-blur-xl flex flex-col overflow-hidden">
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