import React, { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import MainViewDates from "../components/MainViewDates";
import Sidebar from "../components/Sidebar";
import TaskView from "../components/TaskView";
import Background from "../components/Background";

const tasks = [
    { id: 1, name: "Morning Gym", locationLabel: "Location", locationValue: "Gold's Gym", startTime: "06:00", endTime: "07:30" },
    { id: 2, name: "Math Class", locationLabel: "Location", locationValue: "School", startTime: "08:00", endTime: "09:30" },
    { id: 3, name: "Project Sync", locationLabel: "Location", locationValue: "Discord", startTime: "11:00", endTime: "12:00" },
    { id: 4, name: "Grocery Run", locationLabel: "Store", locationValue: "Whole Foods", startTime: "17:00", endTime: "18:00" },
    { id: 5, name: "Dinner Date", locationLabel: "Venue", locationValue: "Pasta Place", startTime: "19:30", endTime: "21:00" },
    { id: 6, name: "Review Code", locationLabel: "Home", locationValue: "Office", startTime: "21:30", endTime: "22:30" },
    { id: 7, name: "Meditation", locationLabel: "App", locationValue: "Headspace", startTime: "23:00", endTime: "23:30" }
];

function MainView() {
    const containerRef = useRef(null);
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
                    {tasks.map((t) => (
                        <div key={t.id} className="shrink-0">
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
            <Sidebar firstIcon={true} />
            <MainView />
        </div>
    );
}