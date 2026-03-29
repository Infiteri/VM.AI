import MainViewDates from "../components/MainViewDates";
import Sidebar from "../components/Sidebar";

function MainView() {
    return (
        <div className="flex flex-col items-center flex-1 text-main font-bold text-[48px] py-18">
            <h1>YOUR SCHEDULE</h1>

            <MainViewDates />
        </div>
    );
}

export default function HomePage() {
    return (
        <div className="w-screen h-screen bg-main flex">
            <Sidebar />
            <MainView />
        </div>
    );
}