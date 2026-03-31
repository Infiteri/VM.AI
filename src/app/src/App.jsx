import { BrowserRouter, Route, Router, Routes } from "react-router-dom"
import HomePage from "./pages/HomePage"
import AddTaskPage from "./pages/AddTaskPage"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/task" element={<AddTaskPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
