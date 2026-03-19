export type AgentOption = {
  id: string;
  name: string;
  slug: string;
  active_version_no: number | null;
  description: string | null;
};

export type ProductOption = {
  id: string;
  name: string;
  client_id: string;
  description: string | null;
};

export type ConversationSummary = {
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

export type KnowledgeSource = {
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

export type ConsorcioQualificationBlock = {
  intent: string;
  questions: string[];
  disqualifiers: string[];
  required_fields: string[];
};

export type ConsorcioObjectionBlock = {
  objection: string;
  response: string;
};

export type ConsorcioPlaybookBlock = {
  positioning: string;
  tone: string;
  qualification: ConsorcioQualificationBlock;
  objections: ConsorcioObjectionBlock[];
  compliance_rules: string[];
  handoff_rules: string[];
  follow_up_rules: string[];
};

export type ConsorcioKnowledgeBlock = {
  product_focus: string[];
  priority_sources: string[];
  official_domains: string[];
  youtube_sources: string[];
  tags: string[];
};

export type ConsorcioStudio = {
  agent: AgentOption;
  active_version: {
    created_at: string;
    prompt_system: string;
    policy_json: Record<string, unknown>;
    tool_config_json: Record<string, unknown>;
    knowledge_config_json: Record<string, unknown>;
    channel_config_json: Record<string, unknown>;
  } | null;
  playbook: ConsorcioPlaybookBlock;
  knowledge: ConsorcioKnowledgeBlock;
};

export function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinLines(value: string[] | undefined): string {
  return (value || []).join("\n");
}

export function parseObjections(value: string): ConsorcioObjectionBlock[] {
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

export function formatObjections(value: ConsorcioObjectionBlock[]): string {
  return value.map((item) => `${item.objection} => ${item.response}`).join("\n");
}

export function badgeTone(status: string): string {
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
