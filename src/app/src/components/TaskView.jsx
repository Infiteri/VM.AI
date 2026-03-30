import React, { useState } from 'react';
import { CheckCircle2, CircleOff, MessageSquareText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function TaskView({ task }) {
    const [isNoteOpen, setIsNoteOpen] = useState(false);

    const [taskData, setTaskData] = useState({
        realization: task?.realization ?? null, // null = untouched, true = done, false = skipped
        duration: task?.time || 0,
        difficulty: task?.difficulty || 50
    });

    const {
        name = "Task name",
        locationValue = "School",
        startTime = "07:00",
        endTime = "08:00",
    } = task || {};

    const handleSave = () => {
        console.log("Saving Task Data:", { name, ...taskData });
    };

    return (
        <div className="flex flex-row items-stretch">
            {/* MAIN CARD */}
            <div className={`
                bg-main p-4 flex flex-col gap-3 w-56 border border-white/5 shadow-xl z-20 transition-all duration-300
                ${isNoteOpen ? 'rounded-l-xl border-r-0' : 'rounded-xl'}
            `}>
                <h2 className="text-main text-lg font-semibold text-center mt-2 truncate">{name}</h2>

                <div className="flex items-center justify-between">
                    <div className="bg-sec border border-main/20 px-2 py-1 rounded flex gap-1.5 items-center text-xs">
                        <span className="text-main/60">Location</span>
                        <span className="text-main/30">|</span>
                        <span className="text-main/80 truncate max-w-[60px]">{locationValue}</span>
                    </div>

                    <button
                        onClick={() => setIsNoteOpen(!isNoteOpen)}
                        className={`transition-all ${isNoteOpen ? 'text-mod scale-110' : 'text-main opacity-80 hover:opacity-100'}`}
                    >
                        <MessageSquareText size={16} />
                    </button>
                </div>

                <div className="bg-main-font text-background py-1.5 rounded-lg font-bold text-sm text-center">
                    {startTime} - {endTime}
                </div>

                <div className="flex justify-between mt-1 px-1 text-[9px] font-medium uppercase tracking-tighter">
                    <button className="text-second hover:text-main transition-colors">Modify</button>
                    <button className="text-second hover:text-del transition-colors">Delete</button>
                </div>
            </div>

            {/* INTEGRATED EXTENSION */}
            <AnimatePresence>
                {isNoteOpen && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: "auto", opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ type: "spring", bounce: 0, duration: 0.4 }}
                        className="bg-main border border-white/5 border-l-0 rounded-r-xl overflow-hidden shadow-xl z-10"
                    >
                        <div className="p-5 h-full min-w-[220px] flex flex-col gap-4 border-l border-white/10 justify-center">

                            {/* Realization Row - Improved UX */}
                            <div className="flex items-center justify-between gap-4">
                                <span className="text-xs text-main/90 font-medium">Realization:</span>
                                <div className="flex gap-3">
                                    <CheckCircle2
                                        size={20}
                                        style={{
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease',
                                            color: taskData.realization === true ? 'var(--main-font)' : 'var(--main-font)',
                                            opacity: taskData.realization === true ? 1 : 0.2
                                        }}
                                        onClick={() => setTaskData({ ...taskData, realization: true })}
                                    />
                                    <CircleOff
                                        size={20}
                                        style={{
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease',
                                            color: taskData.realization === false ? '#ff5f5f' : 'var(--main-font)',
                                            opacity: taskData.realization === false ? 1 : 0.2
                                        }}
                                        onClick={() => setTaskData({ ...taskData, realization: false })}
                                    />
                                </div>
                            </div>

                            {/* Duration Row */}
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-main/90 font-medium whitespace-nowrap">Duration:</span>
                                <div className="border-b border-second/50 flex-1 flex items-baseline gap-1" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                                    <input
                                        type="number"
                                        value={taskData.duration}
                                        onChange={(e) => setTaskData({ ...taskData, duration: e.target.value })}
                                        style={{ backgroundColor: 'transparent', width: '100%', fontSize: '12px', color: 'white', outline: 'none', textAlign: 'right' }}
                                        placeholder="0"
                                    />
                                    <span className="text-[10px] text-second" style={{ opacity: 0.5 }}>min</span>
                                </div>
                            </div>

                            {/* Difficulty Slider */}
                            <div className="flex flex-col gap-1">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-main/90 font-medium">Difficulty:</span>
                                    <span className="text-[10px]" style={{ color: 'var(--main-font)', opacity: 0.8 }}>{taskData.difficulty}%</span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={taskData.difficulty}
                                    onChange={(e) => setTaskData({ ...taskData, difficulty: e.target.value })}
                                    style={{ width: '100%', height: '4px', borderRadius: '8px', cursor: 'pointer', accentColor: 'var(--main-font)' }}
                                />
                            </div>

                            {/* Save Button */}
                            <button
                                onClick={handleSave}
                                style={{
                                    marginTop: '8px',
                                    fontSize: '11px',
                                    fontWeight: 'bold',
                                    letterSpacing: '0.1em',
                                    color: 'white',
                                    opacity: 0.9,
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer'
                                }}
                                className="hover:text-mod active:scale-95 transition-all"
                            >
                                SAVE
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}