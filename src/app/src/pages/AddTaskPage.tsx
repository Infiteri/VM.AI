import { useLocation } from "react-router-dom"
import Background from "../components/Background"
import NLPView from "../components/NLPView"
import Sidebar from "../components/Sidebar"
import TaskModifyView from "../components/TaskModifyView"
import { createDefaultTask } from "../types/Task"

export default function AddTaskPage() {
    const location = useLocation()
    const openMode = location.state?.openMode ?? "add";
    const task = location.state?.task ?? createDefaultTask()
    console.log(task);
    


    return (
        <div className="w-screen h-screen flex overflow-hidden">
            <Background />
            <Sidebar />

            <div className="flex-1 flex items-center justify-center p-6">
                <TaskModifyView task={task} />
            </div>

            <main className="flex justify-end">
                <div className="min-w-75 h-full border-l border-white/5 bg-sec/20 shadow-2xl">
                    <NLPView mode={openMode} />
                </div>
            </main>
        </div>
    )
}