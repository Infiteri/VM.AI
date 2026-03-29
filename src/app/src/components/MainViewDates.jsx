import { useState } from "react";
import { ChevronsLeftRight } from "lucide-react"; // Ensure your library matches this import

function generateDates(startDate, backCount) {
    const dates = [];
    // Standardize to midnight to avoid time-offset bugs
    const start = new Date(startDate);
    start.setHours(0, 0, 0, 0);

    for (let i = -backCount; i <= 6; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        dates.push(d);
    }
    return dates;
}

function formatDate(date) {
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${day}.${month}`;
}

export default function MainViewDates() {
    const [today] = useState(() => {
        const d = new Date();
        d.setHours(0, 0, 0, 0);
        return d;
    });

    const [visibleBack, setVisibleBack] = useState(0);
    const [selectedDate, setSelectedDate] = useState(today);

    const dates = generateDates(today, visibleBack);

    const toggleBack = () => {
        // Toggles between 0 and 3 days backward all at once
        setVisibleBack((prev) => (prev === 0 ? 3 : 0));
    };

    // CRITICAL FIX: Compare the formatted strings, not the Date objects
    const isSameDay = (d1, d2) => formatDate(d1) === formatDate(d2);

    return (
        <div className="flex items-center gap-1 p-1.5 bg-[#0a0f1a]/90 backdrop-blur-md border border-white/10 rounded-full w-fit shadow-xl">
            {/* Expand/Collapse Toggle */}
            <button
                onClick={toggleBack}
                className={`p-2 transition-all duration-300 ${visibleBack > 0 ? "text-white rotate-180" : "text-white/40 hover:text-white"
                    }`}
            >
                <ChevronsLeftRight size={20} strokeWidth={2.5} />
            </button>

            <div className="flex items-center gap-2 pr-2">
                {dates.map((date) => {
                    const isSel = isSameDay(date, selectedDate);
                    const isTdy = isSameDay(date, today);
                    const dateStr = formatDate(date);

                    return (
                        <button
                            key={dateStr}
                            onClick={() => setSelectedDate(date)}
                            className={`
                px-4 py-1.5 rounded-full text-[13px] font-bold transition-all duration-200
                ${isSel
                                    ? "bg-[#fef3c7] text-[#0a0f1a]" // Selected: Solid Cream
                                    : isTdy
                                        ? "border border-[#fef3c7] text-[#fef3c7] bg-[#161d2f]" // Today: Cream Outline
                                        : "bg-[#161d2f] text-white/80 hover:bg-[#1e293b]" // Others: Dark Capsule
                                }
              `}
                        >
                            {dateStr}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}