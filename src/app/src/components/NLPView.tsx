import React, { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";
import { api } from "../services/api";
import type { Task } from "../types/Task";

interface NLPViewProps {
  mode: "add" | "modify";
  onParsedTask?: (task: Task) => void;
}

export default function NLPView({ mode, onParsedTask }: NLPViewProps) {
    const [modeText, setModeText] = useState("Add");
    const [inputText, setInputText] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [parsedResult, setParsedResult] = useState<any>(null);

    useEffect(() => {
        if (mode === "add") setModeText("Add");
        else setModeText("Modify");
    }, [mode]);

    const handleSubmit = async () => {
        if (!inputText.trim()) return;
        
        setLoading(true);
        setError("");
        
        try {
            const result = await api.parseNLPAdd(inputText);
            setParsedResult(result.task);
            if (onParsedTask) {
                onParsedTask(result.task);
            }
        } catch (err: any) {
            setError(err.message || "Failed to parse task");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="flex flex-col items-center justify-between h-full py-24 px-8 bg-main">
            <div className="flex flex-col items-center gap-2">
                    <h1 className="text-main font-bold text-6xl tracking-tight">
                        {modeText}
                    </h1>
            </div>

            <div className="w-full flex-1 max-h-125 mt-12 mb-8 rounded-[40px] border border-white/5 bg-sec/10 relative flex flex-col p-4 shadow-inner">
                <div className="flex-1 overflow-y-auto p-4 text-main/40 font-light italic">
                    {parsedResult ? (
                        <div className="text-main font-normal">
                            <p><strong>Name:</strong> {parsedResult.name}</p>
                            <p><strong>Duration:</strong> {parsedResult.duration} min</p>
                            <p><strong>Difficulty:</strong> {parsedResult.difficulty}</p>
                            <p><strong>Category:</strong> {parsedResult.category?.join(", ")}</p>
                            <p><strong>Location:</strong> {parsedResult.location}</p>
                            <p><strong>Importance:</strong> {parsedResult.importance}</p>
                        </div>
                    ) : (
                        "Start describing your task..."
                    )}
                </div>
                
                {error && (
                    <div className="text-red-400 text-sm p-2">{error}</div>
                )}

                <div className="relative mt-auto">
                    <input
                        type="text"
                        placeholder="Add a new task"
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={handleKeyPress}
                        disabled={loading}
                        className="w-full bg-main border border-white/10 rounded-2xl py-4 px-6 text-main placeholder:text-main/20 outline-none focus:border-main-font/40 transition-colors pr-14"
                    />
                    <button 
                        onClick={handleSubmit}
                        disabled={loading || !inputText.trim()}
                        className="absolute right-3 top-1/2 -translate-y-1/2 bg-main-font p-2 rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg disabled:opacity-50"
                    >
                        <ArrowUp size={20} className="text-background" />
                    </button>
                </div>
            </div>

            <button 
                onClick={handleSubmit}
                disabled={loading || !inputText.trim()}
                className="w-full bg-main-font text-background font-bold py-5 rounded-[20px] text-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-xl uppercase tracking-widest disabled:opacity-50"
            >
                {loading ? "Parsing..." : "Submit request"}
            </button>
        </div>
    );
}