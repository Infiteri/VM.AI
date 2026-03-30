import { Calendar, Calendar1, BarChart } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Field({ data, isSelected, onTap }) {
    const iconMap = {
        schedule: Calendar,
        task: Calendar1,
        stats: BarChart,
    };

    const IconComp = iconMap[data.icon];

    return (
        <div
            className={`
        flex flex-row items-center gap-2 text-main cursor-pointer
        transition-all duration-300 ease-out
        ${isSelected ? 'ml-10' : ''}
      `}
            onClick={onTap}
        >
            <h1 className="text-[16px] font-light">{data.name}</h1>
            <IconComp size={22} strokeWidth={2} />
        </div>
    );
}

export default function Sidebar({ firstIcon = false }) {
    const [selectedId, setSelectedId] = useState(null);
    const navigate = useNavigate();

    const fields = [
        { id: 1, name: "Schedule", icon: "schedule", path: "/" },
        { id: 2, name: "Add a task", icon: "task", path: "/" },
        { id: 3, name: "Statistics", icon: "stats", path: "/" },
    ];

    const handleFieldTap = (field) => {
        setSelectedId(field.id);
        navigate(field.path);
    };

    return (
        <div className="w-67 bg-main h-full flex flex-col p-4 gap-4 border-4 border-r-[#152032]">
            <div className="py-4">
                <h1 className="text-main text-[68px] mb-0">VM.AI</h1>
                <h2 className="text-second font-bold text-[24px] -mt-5">set your day</h2>
            </div>

            <div className="py-3 flex flex-col gap-5">
                {fields.map((field, i) => (
                    <Field
                        key={field.id}
                        data={field}
                        isSelected={selectedId === field.id || (firstIcon && i === 0 && selectedId === null)}
                        onTap={() => handleFieldTap(field)}
                    />
                ))}
            </div>
        </div>
    );
}