import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold">{{project_name}}</h1>
      <p className="mt-4">Author: {{author}}</p>
      <p>Created: {{created_at}}</p>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
