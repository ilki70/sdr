"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP } from "@/lib/datetime";

type AgentOption = {
  id: string;
  name: string;
  slug: string;
  active_version_no: number | null;
  description: string | null;
};

type ProductOption = {
  id: string;
  name: string;
  client_id: string;
  description: string | null;
};

type ConversationSummary = {
  id: string;
  agent_id: string | null;
  title: string;
  channel: string;
  status: string;
  lead_id: string;
  started_at: string;
  updated_at: string;
  last_message_preview: string | null;
  message_count: number;
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

type ConsorcioQualificationBlock = {
  intent: string;
  questions: string[];
  disqualifiers: string[];
  required_fields: string[];
};

type ConsorcioObjectionBlock = {
  objection: string;
  response: string;
};

type ConsorcioPlaybookBlock = {
  positioning: string;
  tone: string;
  qualification: ConsorcioQualificationBlock;
  objections: ConsorcioObjectionBlock[];
  compliance_rules: string[];
  handoff_rules: string[];
  follow_up_rules: string[];
};

type ConsorcioKnowledgeBlock = {
  product_focus: string[];
  priority_sources: string[];
  official_domains: string[];
  youtube_sources: string[];
  tags: string[];
};

type ConsorcioStudio = {
  agent: AgentOption;
  active_version: {
    prompt_system: string;
    policy_json: Record<string, unknown>;
    tool_config_json: Record<string, unknown>;
    knowledge_config_json: Record<string, unknown>;
    channel_config_json: Record<string, unknown>;
  } | null;
  playbook: ConsorcioPlaybookBlock;
  knowledge: ConsorcioKnowledgeBlock;
};

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinLines(value: string[] | undefined): string {
  return (value || []).join("\n");
}

function parseObjections(value: string): ConsorcioObjectionBlock[] {
  return splitLines(value)
    .map((line) => {
      const [objection, ...rest] = line.split("=>");
      if (!objection || rest.length === 0) {
        return null;
      }
      const response = rest.join("=>").trim();
      return { objection: objection.trim(), response };
    })
    .filter((item): item is ConsorcioObjectionBlock => Boolean(item?.objection && item?.response));
}

function formatObjections(value: ConsorcioObjectionBlock[]): string {
  return value.map((item) => `${item.objection} => ${item.response}`).join("\n");
}

function getStringList(value: Record<string, unknown>, key: string): string[] {
  const raw = value[key];
  return Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string") : [];
}

export default function ConsorciosPage() {
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [studio, setStudio] = useState<ConsorcioStudio | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [knowledgeRef, setKnowledgeRef] = useState("");
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    prompt_system: "",
    positioning: "",
    tone: "consultivo",
    qualification_intent: "qualificar lead de consorcio",
    qualification_questions: "",
    qualification_disqualifiers: "",
    qualification_required_fields: "",
    objections: "",
    compliance_rules: "",
    handoff_rules: "",
    follow_up_rules: "",
    product_focus: "",
    priority_sources: "",
    official_domains: "",
    youtube_sources: "",
    tags: "",
  });

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId],
  );

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) || null,
    [products, selectedProductId],
  );

  async function loadSources(productId: string) {
    if (!productId) {
      setSources([]);
      return;
    }
    const items = await fetchJson<KnowledgeSource[]>(`/api/proxy/knowledge/sources?product_id=${encodeURIComponent(productId)}`);
    setSources(items);
  }

  async function loadStudio(agentId: string) {
    if (!agentId) {
      setStudio(null);
      return;
    }
    const payload = await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${agentId}/consorcio-studio`);
    setStudio(payload);
    setForm({
      name: payload.agent.name,
      description: payload.agent.description || "",
      prompt_system:
        payload.active_version?.prompt_system ||
        "Voce e um agente comercial consultivo para operacao interna de consorcios. Atenda com clareza, sustente fatos oficiais e conduza para o proximo passo.",
      positioning: payload.playbook.positioning,
      tone: payload.playbook.tone,
      qualification_intent: payload.playbook.qualification.intent,
      qualification_questions: joinLines(payload.playbook.qualification.questions),
      qualification_disqualifiers: joinLines(payload.playbook.qualification.disqualifiers),
      qualification_required_fields: joinLines(payload.playbook.qualification.required_fields),
      objections: formatObjections(payload.playbook.objections),
      compliance_rules: joinLines(payload.playbook.compliance_rules),
      handoff_rules: joinLines(payload.playbook.handoff_rules),
      follow_up_rules: joinLines(payload.playbook.follow_up_rules),
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
      setIsLoading(true);
      setError(null);
      try {
        const [agentItems, productItems, conversationItems] = await Promise.all([
          fetchJson<AgentOption[]>("/api/proxy/agents"),
          fetchJson<ProductOption[]>("/api/proxy/products"),
          fetchJson<ConversationSummary[]>("/api/proxy/messages/conversations"),
        ]);
        if (cancelled) {
          return;
        }
        setAgents(agentItems);
        setProducts(productItems);
        setConversations(conversationItems);
        const agentId = agentItems[0]?.id || "";
        const productId = productItems[0]?.id || "";
        setSelectedAgentId(agentId);
        setSelectedProductId(productId);
        if (agentId) {
          await loadStudio(agentId);
        }
        if (productId) {
          await loadSources(productId);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Falha ao carregar estúdio de consórcios.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
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
      setError(cause instanceof Error ? cause.message : "Falha ao carregar playbook do agente."),
    );
  }, [selectedAgentId]);

  useEffect(() => {
    if (!selectedProductId) {
      setSources([]);
      return;
    }
    void loadSources(selectedProductId).catch((cause) =>
      setError(cause instanceof Error ? cause.message : "Falha ao carregar fontes de conhecimento."),
    );
  }, [selectedProductId]);

  async function handleSavePlaybook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAgentId) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      const currentToolConfig = studio?.active_version?.tool_config_json || { rag_enabled: true, web_allowlist_enabled: true };
      const currentChannelConfig = studio?.active_version?.channel_config_json || {
        default_channel: "whatsapp",
        allowed_channels: ["whatsapp", "lab"],
      };
      await fetchJson<ConsorcioStudio>(`/api/proxy/agents/${selectedAgentId}/consorcio-studio`, {
        method: "PATCH",
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          prompt_system: form.prompt_system,
          playbook: {
            positioning: form.positioning,
            tone: form.tone,
            qualification: {
              intent: form.qualification_intent,
              questions: splitLines(form.qualification_questions),
              disqualifiers: splitLines(form.qualification_disqualifiers),
              required_fields: splitLines(form.qualification_required_fields),
            },
            objections: parseObjections(form.objections),
            compliance_rules: splitLines(form.compliance_rules),
            handoff_rules: splitLines(form.handoff_rules),
            follow_up_rules: splitLines(form.follow_up_rules),
          },
          knowledge: {
            product_focus: splitLines(form.product_focus),
            priority_sources: splitLines(form.priority_sources),
            official_domains: splitLines(form.official_domains),
            youtube_sources: splitLines(form.youtube_sources),
            tags: splitLines(form.tags),
          },
          tool_config_json: currentToolConfig,
          channel_config_json: currentChannelConfig,
          publish: true,
        }),
      });
      await loadStudio(selectedAgentId);
      setNotice("Playbook publicado com sucesso.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao salvar playbook.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleIngestUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProductId || !knowledgeRef.trim()) {
      return;
    }
    setIsIngesting(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson("/api/proxy/knowledge/sources/url", {
        method: "POST",
        body: JSON.stringify({ product_id: selectedProductId, source_ref: knowledgeRef.trim() }),
      });
      setKnowledgeRef("");
      await loadSources(selectedProductId);
      setNotice("Fonte enviada para ingestao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao ingerir fonte.");
    } finally {
      setIsIngesting(false);
    }
  }

  async function handleUploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProductId || !knowledgeFile) {
      return;
    }
    setIsIngesting(true);
    setError(null);
    setNotice(null);
    try {
      const formData = new FormData();
      formData.append("product_id", selectedProductId);
      formData.append("file", knowledgeFile);
      const response = await fetch("/api/proxy/knowledge/sources/upload", {
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
      setKnowledgeFile(null);
      const fileInput = document.getElementById("consorcio-file-input") as HTMLInputElement | null;
      if (fileInput) {
        fileInput.value = "";
      }
      await loadSources(selectedProductId);
      setNotice("Documento enviado para ingestao.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao enviar documento.");
    } finally {
      setIsIngesting(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(37,211,102,0.10),rgba(255,255,255,0.04))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Consorcios Studio</p>
        <h1 className="mt-3 text-3xl font-semibold">Operacao interna de consorcios</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Configure o playbook do agente, organize a base de conhecimento e acompanhe as conversas do time antes do handoff para a Turn2C.
        </p>
      </section>

      {error ? <p className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p> : null}
      {notice ? <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{notice}</p> : null}

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">Playbook do agente</h2>
              <p className="mt-2 text-sm text-white/60">
                Versione qualificacao, objeções, compliance, follow-up e o texto base do agente de consorcio.
              </p>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
              {isLoading ? "carregando" : selectedAgent?.slug || "sem agente"}
            </span>
          </div>

          <form onSubmit={handleSavePlaybook} className="mt-6 space-y-4">
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
                <span>Nome</span>
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
                />
              </label>
            </div>

            <label className="space-y-2 text-sm text-white/70">
              <span>Descricao</span>
              <textarea
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                rows={3}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>

            <label className="space-y-2 text-sm text-white/70">
              <span>Prompt base</span>
              <textarea
                value={form.prompt_system}
                onChange={(event) => setForm((current) => ({ ...current, prompt_system: event.target.value }))}
                rows={5}
                className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-white/70 md:col-span-2">
                <span>Posicionamento</span>
                <textarea
                  value={form.positioning}
                  onChange={(event) => setForm((current) => ({ ...current, positioning: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Tom</span>
                <input
                  value={form.tone}
                  onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Intencao da qualificacao</span>
                <input
                  value={form.qualification_intent}
                  onChange={(event) => setForm((current) => ({ ...current, qualification_intent: event.target.value }))}
                  className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70 md:col-span-2">
                <span>Perguntas de qualificacao, uma por linha</span>
                <textarea
                  value={form.qualification_questions}
                  onChange={(event) => setForm((current) => ({ ...current, qualification_questions: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Desqualificadores, um por linha</span>
                <textarea
                  value={form.qualification_disqualifiers}
                  onChange={(event) => setForm((current) => ({ ...current, qualification_disqualifiers: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Campos obrigatorios, um por linha</span>
                <textarea
                  value={form.qualification_required_fields}
                  onChange={(event) => setForm((current) => ({ ...current, qualification_required_fields: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70 md:col-span-2">
                <span>Objeções no formato "objeção =&gt; resposta", uma por linha</span>
                <textarea
                  value={form.objections}
                  onChange={(event) => setForm((current) => ({ ...current, objections: event.target.value }))}
                  rows={5}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-white/70">
                <span>Regras de compliance, uma por linha</span>
                <textarea
                  value={form.compliance_rules}
                  onChange={(event) => setForm((current) => ({ ...current, compliance_rules: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Regras de handoff, uma por linha</span>
                <textarea
                  value={form.handoff_rules}
                  onChange={(event) => setForm((current) => ({ ...current, handoff_rules: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Regras de follow-up, uma por linha</span>
                <textarea
                  value={form.follow_up_rules}
                  onChange={(event) => setForm((current) => ({ ...current, follow_up_rules: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Focus do produto, uma por linha</span>
                <textarea
                  value={form.product_focus}
                  onChange={(event) => setForm((current) => ({ ...current, product_focus: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="space-y-2 text-sm text-white/70">
                <span>Fontes prioritarias</span>
                <textarea
                  value={form.priority_sources}
                  onChange={(event) => setForm((current) => ({ ...current, priority_sources: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Dominios oficiais</span>
                <textarea
                  value={form.official_domains}
                  onChange={(event) => setForm((current) => ({ ...current, official_domains: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
              <label className="space-y-2 text-sm text-white/70">
                <span>Videos YouTube</span>
                <textarea
                  value={form.youtube_sources}
                  onChange={(event) => setForm((current) => ({ ...current, youtube_sources: event.target.value }))}
                  rows={4}
                  className="w-full rounded-3xl border border-white/15 bg-black/25 px-4 py-4 text-white outline-none"
                />
              </label>
            </div>

            <label className="space-y-2 text-sm text-white/70">
              <span>Tags</span>
              <input
                value={form.tags}
                onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))}
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-white outline-none"
              />
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-full bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? "Publicando..." : "Publicar playbook"}
              </button>
              <Link href="/agents" className="rounded-full border border-white/12 px-5 py-2 text-sm text-white/80">
                Abrir Agents
              </Link>
            </div>
          </form>
        </article>

        <article className="rounded-[28px] border border-white/10 bg-white/5 p-6">
          <h2 className="text-2xl font-semibold">Knowledge e acompanhamento</h2>
          <p className="mt-2 text-sm text-white/60">
            Ingerir docs, links e videos para o agente e acompanhar as conversas que alimentam o handoff humano.
          </p>

          <div className="mt-6 space-y-4">
            <label className="space-y-2 text-sm text-white/70">
              <span>Produto alvo</span>
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

            <form onSubmit={handleIngestUrl} className="space-y-3 rounded-[24px] border border-white/10 bg-black/20 p-4">
              <p className="text-sm font-semibold">Ingerir URL, pagina oficial ou video YouTube</p>
              <input
                value={knowledgeRef}
                onChange={(event) => setKnowledgeRef(event.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm text-white outline-none"
              />
              <button
                type="submit"
                disabled={isIngesting || !selectedProductId}
                className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isIngesting ? "Enviando..." : "Ingerir URL / YouTube"}
              </button>
            </form>

            <form onSubmit={handleUploadFile} className="space-y-3 rounded-[24px] border border-white/10 bg-black/20 p-4">
              <p className="text-sm font-semibold">Ingerir documento</p>
              <input
                id="consorcio-file-input"
                type="file"
                onChange={(event) => setKnowledgeFile(event.target.files?.[0] || null)}
                className="block w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm text-white file:mr-4 file:rounded-full file:border-0 file:bg-white file:px-4 file:py-2 file:text-sm file:font-semibold file:text-black"
              />
              <button
                type="submit"
                disabled={isIngesting || !selectedProductId || !knowledgeFile}
                className="rounded-full border border-white/12 px-4 py-2 text-sm text-white/80 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isIngesting ? "Enviando..." : "Ingerir documento"}
              </button>
            </form>

            <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Fontes ativas</p>
                  <h3 className="mt-1 text-lg font-semibold">{selectedProduct?.name || "Produto"}</h3>
                </div>
                <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/55">{sources.length} itens</span>
              </div>
              <div className="mt-4 space-y-3">
                {sources.map((source) => (
                  <article key={source.id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <strong className="text-sm">{source.source_type}</strong>
                      <span className="text-xs uppercase tracking-wide text-white/45">{source.status}</span>
                    </div>
                    <p className="mt-2 text-xs text-white/55 break-all">{source.source_ref}</p>
                    <p className="mt-2 text-[11px] text-white/40">
                      Atualizado em {source.updated_at ? formatDateTimeSP(source.updated_at) : "-"}
                    </p>
                  </article>
                ))}
                {sources.length === 0 ? <p className="text-sm text-white/50">Nenhuma fonte cadastrada para este produto.</p> : null}
              </div>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">Atendimentos</p>
                  <h3 className="mt-1 text-lg font-semibold">Conversas recentes</h3>
                </div>
                <Link href="/conversations" className="rounded-full border border-white/12 px-3 py-1 text-xs text-white/75">
                  Abrir inbox
                </Link>
              </div>
              <div className="mt-4 space-y-3">
                {conversations.slice(0, 6).map((conversation) => (
                  <article key={conversation.id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <strong className="text-sm">{conversation.title}</strong>
                      <span className="text-xs uppercase tracking-wide text-white/45">{conversation.channel}</span>
                    </div>
                    <p className="mt-2 text-sm text-white/65">{conversation.last_message_preview || "Sem mensagens."}</p>
                    <p className="mt-2 text-[11px] text-white/40">
                      {conversation.message_count} mensagens • {formatDateTimeSP(conversation.updated_at)}
                    </p>
                  </article>
                ))}
                {conversations.length === 0 ? <p className="text-sm text-white/50">Ainda não há conversas.</p> : null}
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}
