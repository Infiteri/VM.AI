import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import MainViewDates from "../components/MainViewDates";
import Sidebar from "../components/Sidebar";
import TaskView from "../components/TaskView";
import Background from "../components/Background";
import type { Task } from "../types/Task";

const tasks: Task[] = [
    { name: "Morning Gym", location: "Gold's Gym", start: "06:00", deadline: null, duration: "90", difficulty: "0.7", importance: "0.8", fixed_time: true, fixed_start: "06:00", recurrent: false, recurrence_days: null, category: ["fitness"], created_at: "", updated_at: "" },
    { name: "Math Class", location: "School", start: "08:00", deadline: null, duration: "90", difficulty: "0.6", importance: "0.7", fixed_time: true, fixed_start: "08:00", recurrent: false, recurrence_days: null, category: ["education"], created_at: "", updated_at: "" },
    { name: "Project Sync", location: "Discord", start: "11:00", deadline: null, duration: "60", difficulty: "0.5", importance: "0.6", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["work"], created_at: "", updated_at: "" },
    { name: "Grocery Run", location: "Whole Foods", start: "17:00", deadline: null, duration: "60", difficulty: "0.3", importance: "0.7", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["personal"], created_at: "", updated_at: "" },
    { name: "Dinner Date", location: "Pasta Place", start: "19:30", deadline: null, duration: "90", difficulty: "0.4", importance: "0.9", fixed_time: true, fixed_start: "19:30", recurrent: false, recurrence_days: null, category: ["social"], created_at: "", updated_at: "" },
    { name: "Review Code", location: "Office", start: "21:30", deadline: null, duration: "60", difficulty: "0.8", importance: "0.6", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["work"], created_at: "", updated_at: "" },
    { name: "Meditation", location: "Headspace", start: "23:00", deadline: null, duration: "30", difficulty: "0.2", importance: "0.5", fixed_time: false, fixed_start: null, recurrent: false, recurrence_days: null, category: ["wellness"], created_at: "", updated_at: "" }
];

function MainView() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [constraints, setConstraints] = useState({ left: 0, right: 0 });

    useEffect(() => {
        if (containerRef.current) {
            const scrollWidth = containerRef.current.scrollWidth;
            const offsetWidth = containerRef.current.offsetWidth;
            setConstraints({ left: -(scrollWidth - offsetWidth), right: 0 });
        }
    }, []);

    return (
        <div className="flex flex-col gap-15 items-center flex-1 text-main py-18 overflow-hidden">
            <h1 className="font-bold text-[48px] mb-8">YOUR SCHEDULE</h1>
            <MainViewDates />


            <div className="w-full max-w-6xl mx-auto mt-4 rounded-3xl border-2 border-white/5 bg-sec/30 shadow-2xl overflow-hidden cursor-grab active:cursor-grabbing px-8 backdrop-blur-4xl">
                <motion.div
                    ref={containerRef}
                    drag="x"
                    dragConstraints={constraints}
                    className="flex flex-row gap-6 py-4"
                >
                    {tasks.map((t, i) => (
                        <div key={i} className="shrink-0">
                            <TaskView task={t} />
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}

export default function HomePage() {
    return (
        <div className="w-screen h-screen flex overflow-hidden">
            <Background />
            <Sidebar />
            <MainView />
        </div>
    );
}