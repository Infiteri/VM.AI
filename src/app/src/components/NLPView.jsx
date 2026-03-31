import React, { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

export default function NLPView({ mode }) {
    const [modeText, setModeText] = useState("Add");

    useEffect(() => {
        if (mode === "add") setModeText("Add");
        else setModeText("Modify");
    }, [mode]);

    return (
        <div className="flex flex-col items-center justify-between h-full py-24 px-8 bg-main">
            <div className="flex flex-col items-center gap-2">
                    <h1 className="text-main font-bold text-6xl tracking-tight">
                        {modeText}
                    </h1>
            </div>

            <div className="w-full flex-1 max-h-125 mt-12 mb-8 rounded-[40px] border border-white/5 bg-sec/10 relative flex flex-col p-4 shadow-inner">
                <div className="flex-1 overflow-y-auto p-4 text-main/40 font-light italic">
                    Start describing your task...
                </div>

                <div className="relative mt-auto">
                    <input
                        type="text"
                        placeholder="Add a new task"
                        className="w-full bg-main border border-white/10 rounded-2xl py-4 px-6 text-main placeholder:text-main/20 outline-none focus:border-main-font/40 transition-colors pr-14"
                    />
                    <button className="absolute right-3 top-1/2 -translate-y-1/2 bg-main-font p-2 rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg">
                        <ArrowUp size={20} className="text-background" />
                    </button>
                </div>
            </div>

            <button className="w-full bg-main-font text-background font-bold py-5 rounded-[20px] text-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-xl uppercase tracking-widest">
                Submit task
            </button>
        </div>
    );
}