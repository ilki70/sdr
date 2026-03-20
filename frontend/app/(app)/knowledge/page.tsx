"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type Product = {
  id: string;
  name: string;
  client_id: string;
  description: string | null;
};

type KnowledgeSource = {
  id: string;
  tenant_id: string;
  product_id: string;
  source_type: string;
  source_ref: string;
  status: string;
  version_no: number;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
};

type KnowledgeJob = {
  id: string;
  tenant_id: string;
  product_id: string;
  source_id: string | null;
  created_by_user_id: string;
  job_type: string;
  status: string;
  input_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
  celery_task_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

type SearchResult = {
  source_id: string;
  product_id: string;
  source: string;
  source_type: string;
  score: number;
  content: string;
};

type KnowledgeDiff = {
  source_id: string;
  current_version_no: number;
  previous_version_no: number | null;
  current_created_at: string | null;
  previous_created_at: string | null;
  diff_text: string;
};

type EvaluationRun = {
  id: string;
  tenant_id: string;
  product_id: string | null;
  created_by_user_id: string;
  evaluation_type: string;
  status: string;
  summary_json: Record<string, unknown> | null;
  report_markdown: string | null;
  error_message: string | null;
  celery_task_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

function badgeTone(status: string): string {
  if (status === "completed" || status === "ready") {
    return "border-emerald-400/25 text-emerald-200";
  }
  if (status === "failed") {
    return "border-red-400/30 text-red-100";
  }
  if (status === "running" || status === "processing") {
    return "border-amber-400/25 text-amber-100";
  }
  return "border-white/10 text-white/60";
}

function formatSourceType(sourceType: string): string {
  const labels: Record<string, string> = {
    youtube_video: "YouTube",
    web_page: "Pagina web",
    pdf: "PDF",
    docx: "DOCX",
    text: "Texto",
    pending_upload: "Upload pendente",
    playbook_note: "Nota interna",
    vinac_playbook: "Playbook VINAC",
  };
  return labels[sourceType] || sourceType;
}

function sourceTypeHint(sourceType: string): string | null {
  if (sourceType === "youtube_video") {
    return "Transcript entra quando a legenda publica estiver disponivel.";
  }
  return null;
}

function sourceTypeAddon(sourceType: string): string | null {
  if (sourceType === "youtube_video") {
    return "Transcript";
  }
  return null;
}

export default function KnowledgePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [jobs, setJobs] = useState<KnowledgeJob[]>([]);
  const [latestEvaluation, setLatestEvaluation] = useState<EvaluationRun | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [queryInput, setQueryInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [diff, setDiff] = useState<KnowledgeDiff | null>(null);
  const [diffSourceId, setDiffSourceId] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const [isSubmittingUrl, setIsSubmittingUrl] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isSeedingVinac, setIsSeedingVinac] = useState(false);
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);
  const [isRunningSegmentEvaluation, setIsRunningSegmentEvaluation] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [reingestingId, setReingestingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) || null,
    [products, selectedProductId],
  );

  async function refreshKnowledgeState(productId: string) {
    const [sourceItems, jobItems, evaluation] = await Promise.all([
      fetchJson<KnowledgeSource[]>(`/api/proxy/knowledge/sources?product_id=${encodeURIComponent(productId)}`),
      fetchJson<KnowledgeJob[]>(`/api/proxy/knowledge/jobs?product_id=${encodeURIComponent(productId)}&limit=12`),
      fetchJson<EvaluationRun | null>(`/api/proxy/knowledge/evaluations/latest?product_id=${encodeURIComponent(productId)}`),
    ]);
    setSources(sourceItems);
    setJobs(jobItems);
    setLatestEvaluation(evaluation);
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsBooting(true);
      setError(null);
      try {
        const items = await fetchJson<Product[]>("/api/proxy/products");
        if (cancelled) {
          return;
        }
        setProducts(items);
        const firstProductId = items[0]?.id || "";
        setSelectedProductId(firstProductId);
        if (firstProductId) {
          await refreshKnowledgeState(firstProductId);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar produtos.");
        }
      } finally {
        if (!cancelled) {
          setIsBooting(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedProductId) {
      setSources([]);
      setJobs([]);
      setLatestEvaluation(null);
      setResults([]);
      return;
    }
    void refreshKnowledgeState(selectedProductId);
  }, [selectedProductId]);

  useEffect(() => {
    if (!selectedProductId) {
      return;
    }
    const shouldPoll =
      jobs.some((job) => job.status === "queued" || job.status === "running") ||
      latestEvaluation?.status === "queued" ||
      latestEvaluation?.status === "running";
    if (!shouldPoll) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshKnowledgeState(selectedProductId);
    }, 3500);
    return () => window.clearInterval(timer);
  }, [jobs, latestEvaluation, selectedProductId]);

  async function handleSubmitUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProductId || !urlInput.trim()) {
      return;
    }
    setIsSubmittingUrl(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<KnowledgeJob>("/api/proxy/knowledge/jobs/url", {
        method: "POST",
        body: JSON.stringify({ product_id: selectedProductId, source_ref: urlInput.trim() }),
      });
      await refreshKnowledgeState(selectedProductId);
      setUrlInput("");
      setNotice("URL enviada para a fila de ingestao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao enfileirar URL.");
    } finally {
      setIsSubmittingUrl(false);
    }
  }

  async function handleUploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProductId || !selectedFile) {
      return;
    }
    setIsUploadingFile(true);
    setError(null);
    setNotice(null);
    try {
      const formData = new FormData();
      formData.append("product_id", selectedProductId);
      formData.append("file", selectedFile);
      const response = await fetch("/api/proxy/knowledge/jobs/upload", {
        method: "POST",
        body: formData,
        cache: "no-store",
      });
      if (!response.ok) {
        let message = `Falha no upload: ${response.status}`;
        try {
          const payload = (await response.json()) as { detail?: string; message?: string };
          message = payload.detail || payload.message || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }
      await refreshKnowledgeState(selectedProductId);
      setSelectedFile(null);
      const fileInput = document.getElementById("knowledge-file-input") as HTMLInputElement | null;
      if (fileInput) {
        fileInput.value = "";
      }
      setNotice("Documento enviado para a fila de ingestao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao enfileirar documento.");
    } finally {
      setIsUploadingFile(false);
    }
  }

  async function handleSeedVinac() {
    if (!selectedProductId) {
      return;
    }
    setIsSeedingVinac(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<KnowledgeJob>("/api/proxy/knowledge/jobs/vinac", {
        method: "POST",
        body: JSON.stringify({ product_id: selectedProductId }),
      });
      await refreshKnowledgeState(selectedProductId);
      setNotice("Base oficial enviada para ingestao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao enfileirar base oficial.");
    } finally {
      setIsSeedingVinac(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!queryInput.trim()) {
      return;
    }
    setIsSearching(true);
    setError(null);
    setNotice(null);
    try {
      const params = new URLSearchParams({ q: queryInput.trim(), limit: "6" });
      if (selectedProductId) {
        params.set("product_id", selectedProductId);
      }
      const items = await fetchJson<SearchResult[]>(`/api/proxy/knowledge/search?${params.toString()}`);
      setResults(items);
      if (items.length === 0) {
        setNotice("Nenhum trecho relevante encontrado para essa consulta.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao consultar conhecimento.");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleReingest(sourceId: string) {
    setReingestingId(sourceId);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<KnowledgeJob>(`/api/proxy/knowledge/sources/${sourceId}/reingest`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshKnowledgeState(selectedProductId);
      setNotice("Fonte enviada para reindexacao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao reindexar fonte.");
    } finally {
      setReingestingId(null);
    }
  }

  async function handleLoadDiff(sourceId: string) {
    setDiffSourceId(sourceId);
    setError(null);
    try {
      const payload = await fetchJson<KnowledgeDiff>(`/api/proxy/knowledge/sources/${sourceId}/diff`);
      setDiff(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar diff.");
      setDiff(null);
    } finally {
      setDiffSourceId(null);
    }
  }

  async function handleRunEvaluation() {
    if (!selectedProductId) {
      return;
    }
    setIsRunningEvaluation(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<EvaluationRun>("/api/proxy/knowledge/evaluations/vinac", {
        method: "POST",
        body: JSON.stringify({ product_id: selectedProductId }),
      });
      await refreshKnowledgeState(selectedProductId);
      setNotice("Laboratorio de consorcios enfileirado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar laboratorio de consorcios.");
    } finally {
      setIsRunningEvaluation(false);
    }
  }

  async function handleRunSegmentEvaluation() {
    if (!selectedProductId) {
      return;
    }
    setIsRunningSegmentEvaluation(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<EvaluationRun>("/api/proxy/knowledge/evaluations/segment", {
        method: "POST",
        body: JSON.stringify({ product_id: selectedProductId }),
      });
      await refreshKnowledgeState(selectedProductId);
      setNotice("Laboratorio por segmento enfileirado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar laboratorio por segmento.");
    } finally {
      setIsRunningSegmentEvaluation(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(244,211,94,0.12),transparent_30%),linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))]">
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <p className="text-[11px] uppercase tracking-[0.26em] text-[var(--accent)]">Knowledge Ops</p>
            <div>
              <h1 className="text-3xl font-semibold">RAG operacional e laboratório de consórcios</h1>
              <p className="mt-2 max-w-2xl text-sm text-white/70">
                Ingestao assíncrona, versionamento de fontes, diff entre versões e avaliação automatizada do agente com
                cenários de venda do playbook ativo.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void handleSeedVinac()}
                disabled={!selectedProductId || isSeedingVinac}
                className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
              >
                {isSeedingVinac ? "Enfileirando..." : "Ingerir base oficial"}
              </button>
              <button
                type="button"
                onClick={() => void handleRunEvaluation()}
                disabled={!selectedProductId || isRunningEvaluation}
                className="rounded-full border border-[var(--accent)]/40 px-4 py-2 text-sm text-[var(--accent)] disabled:opacity-60"
              >
                {isRunningEvaluation ? "Enfileirando lab..." : "Executar laboratório"}
              </button>
              <button
                type="button"
                onClick={() => void handleRunSegmentEvaluation()}
                disabled={!selectedProductId || isRunningSegmentEvaluation}
                className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/80 disabled:opacity-60"
              >
                {isRunningSegmentEvaluation ? "Enfileirando..." : "Executar laboratório do segmento"}
              </button>
            </div>
            <div className="inline-flex rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs uppercase tracking-[0.22em] text-white/60">
              YouTube com transcript quando houver legenda publica
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-black/20 p-5">
            <label className="text-[11px] uppercase tracking-[0.22em] text-white/45" htmlFor="knowledge-product">
              Produto ativo
            </label>
            <select
              id="knowledge-product"
              value={selectedProductId}
              onChange={(event) => setSelectedProductId(event.target.value)}
              className="mt-3 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none focus:border-[var(--accent)]"
              disabled={isBooting || products.length === 0}
            >
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
            {!isBooting && products.length === 0 ? (
              <p className="mt-3 text-sm text-white/65">
                Nenhum produto encontrado. Cadastre um produto em{" "}
                <Link href="/products" className="text-[var(--accent)]">
                  Products
                </Link>
                .
              </p>
            ) : null}
            <p className="mt-4 text-sm text-white/70">
              Caso de laboratório: <a href="https://www.turn2c.com/aplicativo/b2b" target="_blank" rel="noreferrer" className="text-[var(--accent)]">Turn2C</a>
            </p>
          </div>
        </div>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-5">
          <form onSubmit={handleSubmitUrl} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Ingerir URL</p>
            <input
              value={urlInput}
              onChange={(event) => setUrlInput(event.target.value)}
              placeholder="https://vinac.com.br/adesao/"
              className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none focus:border-[var(--accent)]"
            />
            <p className="mt-3 text-xs leading-6 text-white/55">
              Aceita pagina web, PDF e YouTube. Em videos com legenda publica, o transcript entra na indexacao.
            </p>
            <button
              type="submit"
              disabled={!selectedProductId || isSubmittingUrl || urlInput.trim().length === 0}
              className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:opacity-60"
            >
              {isSubmittingUrl ? "Enfileirando..." : "Enviar URL para fila"}
            </button>
          </form>

          <form onSubmit={handleUploadFile} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Upload de documento</p>
            <label
              htmlFor="knowledge-file-input"
              className="mt-4 flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-[24px] border border-dashed border-white/15 bg-black/20 px-4 py-6 text-center"
            >
              <span className="text-sm text-white/75">
                {selectedFile ? selectedFile.name : "Clique para selecionar um arquivo"}
              </span>
              <span className="mt-2 text-xs text-white/45">PDF, DOCX, TXT e MD. Arquivos .doc ficam fora do MVP.</span>
            </label>
            <input
              id="knowledge-file-input"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />
            <button
              type="submit"
              disabled={!selectedProductId || isUploadingFile || !selectedFile}
              className="mt-4 w-full rounded-full border border-[var(--accent)]/35 bg-[var(--accent)]/95 px-4 py-3 text-sm font-semibold text-black disabled:opacity-60"
            >
              {isUploadingFile ? "Enfileirando..." : "Enviar documento para fila"}
            </button>
          </form>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Fila recente</p>
            <div className="mt-4 space-y-3">
              {jobs.map((job) => (
                <article key={job.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-sm">{job.job_type}</strong>
                    <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${badgeTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <p className="mt-2 break-all text-xs text-white/60">
                    {String(job.input_json.source_ref || job.input_json.seed || job.input_json.source_id || job.id)}
                  </p>
                  <p className="mt-3 text-[11px] uppercase tracking-wide text-white/40">
                    Criado em {formatDateTimeSP(job.created_at)}
                  </p>
                  {job.error_message ? <p className="mt-2 text-xs text-red-200">{job.error_message}</p> : null}
                </article>
              ))}
              {!isBooting && jobs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 px-4 py-6 text-sm text-white/60">
                  Nenhum job recente.
                </div>
              ) : null}
            </div>
          </section>
        </aside>

        <section className="space-y-5">
          <section className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Recuperacao</p>
                <h2 className="mt-2 text-2xl font-semibold">Teste a busca semantica</h2>
                <p className="mt-2 text-sm text-white/65">
                  Produto ativo: {selectedProduct?.name || "nenhum"}. Use perguntas reais de lead antes de ligar o Chatwoot.
                </p>
              </div>
              <div className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs uppercase tracking-wide text-white/55">
                {sources.length} fontes cadastradas
              </div>
            </div>

            <form onSubmit={handleSearch} className="mt-5 flex flex-col gap-3 lg:flex-row">
              <input
                value={queryInput}
                onChange={(event) => setQueryInput(event.target.value)}
                placeholder="Ex.: seminovo pode ter ate quantos anos?"
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none focus:border-[var(--accent)]"
              />
              <button
                type="submit"
                disabled={isSearching || queryInput.trim().length < 2}
                className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-black disabled:opacity-60"
              >
                {isSearching ? "Consultando..." : "Buscar"}
              </button>
            </form>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {results.map((item) => (
                <article key={`${item.source_id}-${item.score}`} className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">{formatSourceType(item.source_type)}</p>
                        {sourceTypeAddon(item.source_type) ? (
                          <span className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-2 py-1 text-[10px] uppercase tracking-wide text-[var(--accent)]">
                            {sourceTypeAddon(item.source_type)}
                          </span>
                        ) : null}
                      </div>
                      <h3 className="mt-2 line-clamp-2 text-sm font-semibold">{item.source}</h3>
                    </div>
                    <div className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/60">
                      score {item.score.toFixed(3)}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-white/72">{item.content}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-[30px] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Fontes registradas</p>
                  <h2 className="mt-2 text-2xl font-semibold">Inventario do produto</h2>
                </div>
              </div>
              <div className="mt-5 space-y-4">
                {sources.map((source) => (
                  <article key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-wide text-[var(--accent)]">
                            {formatSourceType(source.source_type)}
                          </span>
                          {sourceTypeAddon(source.source_type) ? (
                            <span className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-3 py-1 text-[11px] uppercase tracking-wide text-[var(--accent)]">
                              {sourceTypeAddon(source.source_type)}
                            </span>
                          ) : null}
                          <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${badgeTone(source.status)}`}>
                            {source.status}
                          </span>
                          <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-wide text-white/50">
                            v{source.version_no}
                          </span>
                        </div>
                        <p className="mt-3 break-all text-sm text-white/78">{source.source_ref}</p>
                        {sourceTypeHint(source.source_type) ? (
                          <p className="mt-2 text-xs leading-6 text-white/55">{sourceTypeHint(source.source_type)}</p>
                        ) : null}
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => void handleLoadDiff(source.id)}
                          disabled={diffSourceId === source.id}
                          className="rounded-full border border-white/15 px-4 py-2 text-sm text-white/80 disabled:opacity-60"
                        >
                          {diffSourceId === source.id ? "Carregando..." : "Ver diff"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleReingest(source.id)}
                          disabled={reingestingId === source.id}
                          className="rounded-full border border-[var(--accent)]/35 px-4 py-2 text-sm text-[var(--accent)] disabled:opacity-60"
                        >
                          {reingestingId === source.id ? "Enfileirando..." : "Reindexar"}
                        </button>
                      </div>
                    </div>
                    <dl className="mt-4 grid gap-3 text-xs text-white/55 sm:grid-cols-3">
                      <div>
                        <dt className="uppercase tracking-wide text-white/35">Ultima indexacao</dt>
                        <dd className="mt-1">{formatDateTimeSP(source.last_indexed_at)}</dd>
                      </div>
                      <div>
                        <dt className="uppercase tracking-wide text-white/35">Criado em</dt>
                        <dd className="mt-1">{formatDateTimeSP(source.created_at)}</dd>
                      </div>
                      <div>
                        <dt className="uppercase tracking-wide text-white/35">Atualizado em</dt>
                        <dd className="mt-1">{formatDateTimeSP(source.updated_at)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </div>

            <div className="space-y-5">
              <section className="rounded-[30px] border border-white/10 bg-white/5 p-6">
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Diff entre versões</p>
                {diff ? (
                  <div className="mt-4 rounded-[24px] border border-white/10 bg-black/20 p-4">
                    <p className="text-xs text-white/50">
                      v{diff.previous_version_no ?? 0} ({formatDateTimeSP(diff.previous_created_at)}) → v{diff.current_version_no} ({formatDateTimeSP(diff.current_created_at)})
                    </p>
                    <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-white/78">{diff.diff_text}</pre>
                  </div>
                ) : (
                  <div className="mt-4 rounded-[24px] border border-dashed border-white/15 bg-black/20 px-4 py-6 text-sm text-white/60">
                    Selecione uma fonte e clique em “Ver diff”.
                  </div>
                )}
              </section>

              <section className="rounded-[30px] border border-white/10 bg-white/5 p-6">
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Laboratório de consórcios</p>
                <div className="mt-4 rounded-[24px] border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <strong className="text-sm">Última execução</strong>
                    <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${badgeTone(latestEvaluation?.status || "idle")}`}>
                      {latestEvaluation?.status || "sem execucao"}
                    </span>
                  </div>
                  {latestEvaluation?.summary_json ? (
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm text-white/72">
                      <div>
                        <dt className="text-[11px] uppercase tracking-wide text-white/40">Cenários</dt>
                        <dd className="mt-1">{String(latestEvaluation.summary_json.scenario_count || "-")}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase tracking-wide text-white/40">Aprovados</dt>
                        <dd className="mt-1">{String(latestEvaluation.summary_json.passed_count || "-")}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase tracking-wide text-white/40">Reprovados</dt>
                        <dd className="mt-1">{String(latestEvaluation.summary_json.failed_count || "-")}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase tracking-wide text-white/40">Média</dt>
                        <dd className="mt-1">{String(latestEvaluation.summary_json.average_score || "-")}</dd>
                      </div>
                    </dl>
                  ) : (
                    <p className="mt-4 text-sm text-white/60">Ainda sem relatório consolidado.</p>
                  )}
                  {latestEvaluation?.error_message ? <p className="mt-3 text-sm text-red-100">{latestEvaluation.error_message}</p> : null}
                  {latestEvaluation?.report_markdown ? (
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm text-[var(--accent)]">Abrir relatório</summary>
                      <pre className="mt-3 max-h-[320px] overflow-auto whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/30 p-4 text-xs leading-6 text-white/75">
                        {latestEvaluation.report_markdown}
                      </pre>
                    </details>
                  ) : null}
                </div>
              </section>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}
