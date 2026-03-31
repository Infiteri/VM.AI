import NLPView from "../components/NLPView"
import Sidebar from "../components/Sidebar"
import TaskModifyView from "../components/TaskModifyView"

export default function AddTaskPage() {
    return (
        <div className="w-screen h-screen bg-main flex overflow-hidden">
            <Sidebar />

            <div className="flex-1 flex items-center justify-center p-6">
                <TaskModifyView />
            </div>

            <main className="flex justify-end">
                <div className="min-w-75 h-full border-l border-white/5 bg-sec/20 shadow-2xl">
                    <NLPView mode={"add"} />
                </div>
            </main>
        </div>
    )
}