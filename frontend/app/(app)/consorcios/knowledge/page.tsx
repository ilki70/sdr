"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";
import {
  badgeTone,
  type AgentOption,
  type ConsorcioStudio,
  type KnowledgeSource,
  joinLines,
  splitLines,
} from "../_shared";

type Product = {
  id: string;
  name: string;
  client_id: string;
  description: string | null;
};

type KnowledgeJob = {
  id: string;
  product_id: string;
  source_id: string | null;
  job_type: string;
  status: string;
  input_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
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
  product_id: string | null;
  evaluation_type: string;
  status: string;
  summary_json: Record<string, unknown> | null;
  report_markdown: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

const DEFAULT_PROMPT =
  "Voce e um agente comercial consultivo para operacao interna de consorcios. Atenda com clareza, sustente fatos oficiais e conduza para o proximo passo.";

export default function ConsorciosKnowledgePage() {
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedProductId, setSelectedProductId] = useState("");
  const [studio, setStudio] = useState<ConsorcioStudio | null>(null);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [jobs, setJobs] = useState<KnowledgeJob[]>([]);
  const [latestEvaluation, setLatestEvaluation] = useState<EvaluationRun | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [diff, setDiff] = useState<KnowledgeDiff | null>(null);
  const [diffSourceId, setDiffSourceId] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const [queryInput, setQueryInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    product_focus: "",
    priority_sources: "",
    official_domains: "",
    youtube_sources: "",
    tags: "",
  });
  const [isBooting, setIsBooting] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmittingUrl, setIsSubmittingUrl] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);
  const [isRunningSegmentEvaluation, setIsRunningSegmentEvaluation] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [reingestingId, setReingestingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId],
  );
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

  async function loadStudio(agentId: string) {
    if (!agentId) {
      setStudio(null);
      return;
    }
    const payload = await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${agentId}/consorcio-studio`);
    setStudio(payload);
    setForm({
      product_focus: joinLines(payload.knowledge.product_focus),
      priority_sources: joinLines(payload.knowledge.priority_sources),
      official_domains: joinLines(payload.knowledge.official_domains),
      youtube_sources: joinLines(payload.knowledge.youtube_sources),
      tags: joinLines(payload.knowledge.tags),
    });
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsBooting(true);
      setError(null);
      try {
        const [agentItems, productItems] = await Promise.all([
          fetchJson<AgentOption[]>("/api/proxy/agents"),
          fetchJson<Product[]>("/api/proxy/products"),
        ]);
        if (cancelled) {
          return;
        }
        setAgents(agentItems);
        setProducts(productItems);
        const agentId = agentItems[0]?.id || "";
        const productId = productItems[0]?.id || "";
        setSelectedAgentId(agentId);
        setSelectedProductId(productId);
        if (agentId) {
          await loadStudio(agentId);
        }
        if (productId) {
          await refreshKnowledgeState(productId);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar conhecimento.");
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
    if (!selectedAgentId) {
      return;
    }
    void loadStudio(selectedAgentId).catch((cause) =>
      setError(cause instanceof Error ? cause.message : "Falha ao carregar playbook de conhecimento."),
    );
  }, [selectedAgentId]);

  useEffect(() => {
    if (!selectedProductId) {
      setSources([]);
      setJobs([]);
      setLatestEvaluation(null);
      setResults([]);
      return;
    }
    void refreshKnowledgeState(selectedProductId).catch((cause) =>
      setError(cause instanceof Error ? cause.message : "Falha ao carregar fila de conhecimento."),
    );
  }, [selectedProductId]);

  async function handleSaveKnowledge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAgentId || !studio) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${selectedAgentId}/consorcio-studio`, {
        method: "PATCH",
        body: JSON.stringify({
          name: studio.agent.name,
          description: studio.agent.description,
          prompt_system: studio.active_version?.prompt_system || DEFAULT_PROMPT,
          playbook: studio.playbook,
          knowledge: {
            product_focus: splitLines(form.product_focus),
            priority_sources: splitLines(form.priority_sources),
            official_domains: splitLines(form.official_domains),
            youtube_sources: splitLines(form.youtube_sources),
            tags: splitLines(form.tags),
          },
          tool_config_json: studio.active_version?.tool_config_json || { rag_enabled: true, web_allowlist_enabled: true, consorcio_mode: true },
          channel_config_json: studio.active_version?.channel_config_json || {
            default_channel: "whatsapp",
            allowed_channels: ["whatsapp", "lab"],
          },
          publish: true,
        }),
      });
      await loadStudio(selectedAgentId);
      setNotice("Configuracao de knowledge publicada.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao salvar knowledge.");
    } finally {
      setIsSaving(false);
    }
  }

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
      setNotice("URL enviada para ingestao.");
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
        const text = await response.text();
        throw new Error(text || `Falha no upload: ${response.status}`);
      }
      await refreshKnowledgeState(selectedProductId);
      setSelectedFile(null);
      const input = document.getElementById("consorcio-knowledge-file") as HTMLInputElement | null;
      if (input) {
        input.value = "";
      }
      setNotice("Documento enviado para a fila.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao enfileirar documento.");
    } finally {
      setIsUploadingFile(false);
    }
  }

  async function handleSeedBase() {
    if (!selectedProductId) {
      return;
    }
    setIsSeeding(true);
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
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar a base oficial.");
    } finally {
      setIsSeeding(false);
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
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar laboratorio.");
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
      setNotice("Laboratorio do segmento enfileirado.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao iniciar laboratorio do segmento.");
    } finally {
      setIsRunningSegmentEvaluation(false);
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
        setNotice("Nenhum trecho relevante encontrado.");
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

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(244,211,94,0.12),rgba(255,255,255,0.04))] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Consorcios / Knowledge</p>
            <h1 className="mt-3 text-3xl font-semibold">Base de conhecimento e RAG</h1>
            <p className="mt-2 max-w-3xl text-sm text-white/70">
              Ingestao de documentos, URLs e YouTube, com configuracao de fontes oficiais, prioridade e tags do agente.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/consorcios" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Hub
            </Link>
            <Link href="/consorcios/playbook" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Playbook
            </Link>
            <Link href="/consorcios/inbox" className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80">
              Inbox
            </Link>
          </div>
        </div>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">Perfil de conhecimento</h2>
              <p className="mt-2 text-sm text-white/60">O que entra na memória do agente e quais fontes têm prioridade.</p>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
              {isBooting ? "carregando" : selectedAgent?.slug || "sem agente"}
            </span>
          </div>

          <form onSubmit={handleSaveKnowledge} className="mt-6 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-white/70">
                <span>Agente</span>
                <select
                  value={selectedAgentId}
                  onChange={(event) => setSelectedAgentId(event.target.value)}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Produto ativo para ingestao</span>
                <select
                  value={selectedProductId}
                  onChange={(event) => setSelectedProductId(event.target.value)}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
                >
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-white/70">
                <span>Foco do produto, um por linha</span>
                <textarea
                  value={form.product_focus}
                  onChange={(event) => setForm((current) => ({ ...current, product_focus: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Tags, uma por linha</span>
                <textarea
                  value={form.tags}
                  onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Fontes prioritárias, uma por linha</span>
                <textarea
                  value={form.priority_sources}
                  onChange={(event) => setForm((current) => ({ ...current, priority_sources: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Domínios oficiais, um por linha</span>
                <textarea
                  value={form.official_domains}
                  onChange={(event) => setForm((current) => ({ ...current, official_domains: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70 md:col-span-2">
                <span>Fontes YouTube, uma por linha</span>
                <textarea
                  value={form.youtube_sources}
                  onChange={(event) => setForm((current) => ({ ...current, youtube_sources: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? "Publicando..." : "Publicar knowledge"}
              </button>
              <span className="text-xs text-white/45">
                Base ativa: {studio?.active_version ? formatDateTimeSP(studio.active_version.created_at) : "sem versão publicada"}
              </span>
            </div>
          </form>
        </article>

        <div className="space-y-5">
          <form onSubmit={handleSubmitUrl} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Ingerir URL</p>
            <input
              value={urlInput}
              onChange={(event) => setUrlInput(event.target.value)}
              placeholder="https://..."
              className="mt-4 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none focus:border-[var(--accent)]"
            />
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
              htmlFor="consorcio-knowledge-file"
              className="mt-4 flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-[24px] border border-dashed border-white/15 bg-black/20 px-4 py-6 text-center"
            >
              <span className="text-sm text-white/75">{selectedFile ? selectedFile.name : "Clique para selecionar um arquivo"}</span>
              <span className="mt-2 text-xs text-white/45">PDF, DOCX, TXT e MD. O foco é material oficial.</span>
            </label>
            <input
              id="consorcio-knowledge-file"
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
            <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Ações rápidas</p>
            <div className="mt-4 grid gap-3">
              <button
                type="button"
                onClick={() => void handleSeedBase()}
                disabled={!selectedProductId || isSeeding}
                className="rounded-2xl border border-white/12 px-4 py-3 text-left text-sm text-white/80 disabled:opacity-60"
              >
                {isSeeding ? "Enfileirando..." : "Ingerir base oficial"}
              </button>
              <button
                type="button"
                onClick={() => void handleRunEvaluation()}
                disabled={!selectedProductId || isRunningEvaluation}
                className="rounded-2xl border border-white/12 px-4 py-3 text-left text-sm text-white/80 disabled:opacity-60"
              >
                {isRunningEvaluation ? "Enfileirando..." : "Executar laboratório"}
              </button>
              <button
                type="button"
                onClick={() => void handleRunSegmentEvaluation()}
                disabled={!selectedProductId || isRunningSegmentEvaluation}
                className="rounded-2xl border border-white/12 px-4 py-3 text-left text-sm text-white/80 disabled:opacity-60"
              >
                {isRunningSegmentEvaluation ? "Enfileirando..." : "Executar laboratório do segmento"}
              </button>
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Fontes indexadas</h2>
              <p className="mt-1 text-sm text-white/60">Inventario da base atual do produto selecionado.</p>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{sources.length} itens</span>
          </div>
          <div className="mt-4 space-y-3">
            {sources.slice(0, 6).map((source) => (
              <article key={source.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{source.source_type}</strong>
                  <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${badgeTone(source.status)}`}>
                    {source.status}
                  </span>
                </div>
                <p className="mt-2 break-all text-xs text-white/60">{source.source_ref}</p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-white/45">
                  <span>Versao {source.version_no}</span>
                  <span>Atualizado em {formatDateTimeSP(source.updated_at)}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleReingest(source.id)}
                    disabled={reingestingId === source.id}
                    className="rounded-full border border-white/12 px-3 py-1 text-xs text-white/75 disabled:opacity-60"
                  >
                    {reingestingId === source.id ? "Reindexando..." : "Reindexar"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleLoadDiff(source.id)}
                    disabled={diffSourceId === source.id}
                    className="rounded-full border border-white/12 px-3 py-1 text-xs text-white/75 disabled:opacity-60"
                  >
                    {diffSourceId === source.id ? "Carregando..." : "Ver diff"}
                  </button>
                </div>
              </article>
            ))}
            {sources.length === 0 ? <p className="text-sm text-white/50">Nenhuma fonte ativa.</p> : null}
          </div>
        </article>

        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Fila e validação</h2>
          <div className="mt-4 space-y-3">
            <form onSubmit={handleSearch} className="flex flex-col gap-3 lg:flex-row">
              <input
                value={queryInput}
                onChange={(event) => setQueryInput(event.target.value)}
                placeholder="Pesquisar trechos da base"
                className="min-w-0 flex-1 rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
              />
              <button
                type="submit"
                disabled={isSearching || queryInput.trim().length === 0}
                className="rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:opacity-60"
              >
                {isSearching ? "Buscando..." : "Buscar"}
              </button>
            </form>

            {latestEvaluation ? (
              <article className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">Ultimo laboratorio</strong>
                  <span className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide ${badgeTone(latestEvaluation.status)}`}>
                    {latestEvaluation.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-white/70">{latestEvaluation.evaluation_type}</p>
                <p className="mt-2 text-xs text-white/45">Atualizado em {formatDateTimeSP(latestEvaluation.updated_at)}</p>
              </article>
            ) : (
              <p className="text-sm text-white/50">Nenhum laboratorio executado ainda.</p>
            )}

            {diff ? (
              <article className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">Diff da fonte</strong>
                  <span className="text-xs text-white/45">v{diff.previous_version_no || 0} → v{diff.current_version_no}</span>
                </div>
                <pre className="mt-3 overflow-auto whitespace-pre-wrap break-words text-xs text-white/70">{diff.diff_text}</pre>
              </article>
            ) : null}

            {results.length > 0 ? (
              <div className="space-y-3">
                {results.map((item) => (
                  <article key={`${item.source_id}-${item.score}`} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <strong className="text-sm">{item.source}</strong>
                      <span className="text-xs text-white/45">Score {item.score.toFixed(2)}</span>
                    </div>
                    <p className="mt-2 text-sm text-white/70">{item.content}</p>
                    <p className="mt-2 text-[11px] uppercase tracking-wide text-white/40">{item.source_type}</p>
                  </article>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Fila recente</h2>
          <div className="mt-4 space-y-3">
            {jobs.slice(0, 10).map((job) => (
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
                <p className="mt-3 text-[11px] uppercase tracking-wide text-white/40">Criado em {formatDateTimeSP(job.created_at)}</p>
                {job.error_message ? <p className="mt-2 text-xs text-red-100">{job.error_message}</p> : null}
              </article>
            ))}
          </div>
        </article>

        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-semibold">Hub operacional</h2>
          <p className="mt-2 text-sm text-white/65">
            A knowledge area mantém o RAG separado do playbook e da inbox. O agente consome o material publicado aqui.
          </p>
          <div className="mt-4 space-y-2 text-sm text-white/70">
            <p>• Priorize domínios oficiais e conteúdos de treinamento.</p>
            <p>• Reindexe somente quando a fonte mudar de fato.</p>
            <p>• Use YouTube como insumo de suporte, nao como única fonte de verdade.</p>
            <p>• O fechamento continua fora desta tela, na Turn2C e no fluxo humano.</p>
          </div>
          <div className="mt-5 rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-white/65">
            Produto ativo: {selectedProduct?.name || "nenhum"}.
          </div>
        </article>
      </section>
    </main>
  );
}
