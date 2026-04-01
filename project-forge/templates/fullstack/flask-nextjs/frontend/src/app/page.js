export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <h1 className="text-4xl font-bold">{{project_name}}</h1>
      <p className="mt-4">Author: {{author}}</p>
      <p>Created: {{created_at}}</p>
    </main>
  );
}
