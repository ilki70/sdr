export default function DemoPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-4xl px-6 py-16">
      <h1 className="text-3xl font-semibold">Demo de Conversa</h1>
      <p className="mt-4 text-white/80">
        Esta tela sera conectada ao simulador SSE do agente nas proximas tasks.
      </p>
      <div className="mt-8 rounded-lg border border-white/15 bg-white/5 p-6">
        <p className="text-sm text-white/70">Lead:</p>
        <p className="mt-2">Quero saber se consorcio vale a pena para meu perfil.</p>
      </div>
    </main>
  );
}
