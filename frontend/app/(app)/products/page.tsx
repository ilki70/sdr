"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchJson } from "@/lib/api";
import { formatDateTimeSP, formatMoneyBRL } from "@/lib/datetime";
import { EmptyState } from "@/components/shared/empty-state";

type Client = {
  id: string;
  name: string;
};

type Product = {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  description: string | null;
  base_price: string | null;
  currency: string;
  sales_terms_json: Record<string, unknown> | null;
  is_active: boolean;
  version_no: number;
  created_at: string;
  updated_at: string;
};

type ProductEditorForm = {
  name: string;
  description: string;
  base_price: string;
  currency: string;
  is_active: boolean;
};

const createTemplate = {
  client_id: "",
  name: "",
  description: "",
  base_price: "1000",
  currency: "BRL",
  is_active: true,
};

function buildEditorForm(product?: Product | null): ProductEditorForm {
  return {
    name: product?.name || "",
    description: product?.description || "",
    base_price: product?.base_price ? String(product.base_price) : "",
    currency: product?.currency || "BRL",
    is_active: product?.is_active ?? true,
  };
}

export default function ProductsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [createForm, setCreateForm] = useState(createTemplate);
  const [editorForm, setEditorForm] = useState<ProductEditorForm>(buildEditorForm());
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedProductId) || null,
    [products, selectedProductId],
  );

  async function loadProducts(preferredProductId?: string) {
    setIsLoading(true);
    setError(null);
    try {
      const [clientItems, productItems] = await Promise.all([
        fetchJson<Client[]>("/api/proxy/clients"),
        fetchJson<Product[]>("/api/proxy/products"),
      ]);
      setClients(clientItems);
      setProducts(productItems);

      const nextSelectedId = preferredProductId || selectedProductId || productItems[0]?.id || "";
      setSelectedProductId(nextSelectedId);
      setCreateForm((previous) => ({
        ...previous,
        client_id: previous.client_id || clientItems[0]?.id || "",
      }));
      if (nextSelectedId) {
        const nextProduct = productItems.find((product) => product.id === nextSelectedId) || null;
        setEditorForm(buildEditorForm(nextProduct));
      } else {
        setEditorForm(buildEditorForm());
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar produtos.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadProducts();
  }, []);

  useEffect(() => {
    if (selectedProduct) {
      setEditorForm(buildEditorForm(selectedProduct));
    }
  }, [selectedProduct]);

  async function handleCreateProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await fetchJson<Product>("/api/proxy/products", {
        method: "POST",
        body: JSON.stringify({
          client_id: createForm.client_id,
          name: createForm.name,
          description: createForm.description || undefined,
          base_price: createForm.base_price ? Number(createForm.base_price) : null,
          currency: createForm.currency,
          sales_terms_json: null,
          is_active: createForm.is_active,
        }),
      });
      setNotice(`Produto ${created.name} criado com sucesso.`);
      setCreateForm({
        client_id: createForm.client_id,
        name: "",
        description: "",
        base_price: "1000",
        currency: "BRL",
        is_active: true,
      });
      await loadProducts(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao criar produto.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSaveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProduct) {
      return;
    }
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson<Product>(`/api/proxy/products/${selectedProduct.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editorForm.name,
          description: editorForm.description,
          base_price: editorForm.base_price ? Number(editorForm.base_price) : null,
          currency: editorForm.currency,
          is_active: editorForm.is_active,
        }),
      });
      setNotice(`Produto ${editorForm.name} atualizado.`);
      await loadProducts(selectedProduct.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao atualizar produto.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteProduct() {
    if (!selectedProduct) {
      return;
    }
    const confirmed = window.confirm(`Excluir o produto "${selectedProduct.name}"?`);
    if (!confirmed) {
      return;
    }
    setIsDeleting(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJson(`/api/proxy/products/${selectedProduct.id}`, { method: "DELETE" });
      setNotice(`Produto ${selectedProduct.name} excluído.`);
      await loadProducts();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao excluir produto.");
    } finally {
      setIsDeleting(false);
    }
  }

  const selectedClient = clients.find((client) => client.id === selectedProduct?.client_id) || null;

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Operations</p>
        <h1 className="mt-3 text-3xl font-semibold">Produtos</h1>
        <p className="mt-2 max-w-3xl text-sm text-white/70">
          Crie, edite e exclua produtos com um fluxo único. Cada produto alimenta conhecimento, regras comerciais e
          relatórios operacionais do tenant.
        </p>
      </section>

      {(error || notice) && (
        <section className={`rounded-2xl border px-4 py-3 text-sm ${error ? "border-red-400/30 bg-red-500/10 text-red-100" : "border-emerald-400/30 bg-emerald-500/10 text-emerald-50"}`}>
          {error || notice}
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <form onSubmit={handleCreateProduct} className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--accent)]">Novo produto</p>
          <label className="mt-4 block text-xs uppercase tracking-[0.18em] text-white/45">Cliente</label>
          <select
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            value={createForm.client_id}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, client_id: event.target.value }))}
          >
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
          <label className="mt-3 block text-xs uppercase tracking-[0.18em] text-white/45">Nome</label>
          <input
            className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            placeholder="Nome do produto"
            value={createForm.name}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, name: event.target.value }))}
          />
          <label className="mt-3 block text-xs uppercase tracking-[0.18em] text-white/45">Descrição</label>
          <textarea
            className="mt-2 min-h-[120px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
            placeholder="Descrição comercial"
            value={createForm.description}
            onChange={(event) => setCreateForm((previous) => ({ ...previous, description: event.target.value }))}
          />
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Preço base</label>
              <input
                className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                placeholder="1000"
                inputMode="decimal"
                value={createForm.base_price}
                onChange={(event) => setCreateForm((previous) => ({ ...previous, base_price: event.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Moeda</label>
              <select
                className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                value={createForm.currency}
                onChange={(event) => setCreateForm((previous) => ({ ...previous, currency: event.target.value }))}
              >
                <option value="BRL">BRL</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-white/75">
            <input
              type="checkbox"
              checked={createForm.is_active}
              onChange={(event) => setCreateForm((previous) => ({ ...previous, is_active: event.target.checked }))}
            />
            Produto ativo
          </label>
          <button
            className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isCreating || clients.length === 0}
          >
            {isCreating ? "Criando..." : "Criar produto"}
          </button>
          {clients.length === 0 ? (
            <p className="mt-3 text-sm text-amber-100/90">Cadastre um cliente primeiro para conseguir criar produtos.</p>
          ) : null}
        </form>

        <section className="grid gap-5 lg:grid-cols-[280px_1fr]">
          <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-semibold">Inventário</h2>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/50">
                {products.length} itens
              </span>
            </div>
            <div className="mt-5 space-y-3">
              {products.map((product) => {
                const clientName = clients.find((client) => client.id === product.client_id)?.name || "Cliente";
                const isSelected = product.id === selectedProductId;
                return (
                  <button
                    key={product.id}
                    type="button"
                    onClick={() => setSelectedProductId(product.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      isSelected ? "border-[var(--accent)] bg-[var(--accent)]/10" : "border-white/10 bg-black/20 hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <strong className="block text-sm">{product.name}</strong>
                        <p className="mt-1 text-xs text-white/45">{clientName}</p>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${product.is_active ? "bg-emerald-500/15 text-emerald-200" : "bg-white/10 text-white/50"}`}>
                        {product.is_active ? "Ativo" : "Inativo"}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-[var(--accent)]">{formatMoneyBRL(product.base_price)}</p>
                    <p className="mt-1 text-xs text-white/40">v{product.version_no} • {formatDateTimeSP(product.updated_at)}</p>
                  </button>
                );
              })}
              {products.length === 0 ? (
                <EmptyState
                  title="Nenhum produto cadastrado."
                  description="Produtos alimentam conhecimento, regras de comissão e a estrutura comercial do tenant."
                />
              ) : null}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold">Editar produto</h2>
                <p className="mt-1 text-sm text-white/55">
                  {selectedProduct ? "Atualize os dados do produto selecionado abaixo." : "Selecione um produto na lista para editar."}
                </p>
              </div>
              {selectedProduct ? (
                <button
                  type="button"
                  onClick={handleDeleteProduct}
                  disabled={isDeleting}
                  className="rounded-full border border-red-400/30 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isDeleting ? "Excluindo..." : "Excluir produto"}
                </button>
              ) : null}
            </div>

            {selectedProduct ? (
              <form onSubmit={handleSaveProduct} className="mt-5 grid gap-4 lg:grid-cols-[1fr_280px]">
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Produto</label>
                      <input
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                        value={editorForm.name}
                        onChange={(event) => setEditorForm((previous) => ({ ...previous, name: event.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Cliente vinculado</label>
                      <input
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm text-white/60 outline-none"
                        value={selectedClient?.name || selectedProduct.client_id}
                        disabled
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Descrição</label>
                    <textarea
                      className="mt-2 min-h-[140px] w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                      value={editorForm.description}
                      onChange={(event) => setEditorForm((previous) => ({ ...previous, description: event.target.value }))}
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Preço base</label>
                      <input
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                        inputMode="decimal"
                        value={editorForm.base_price}
                        onChange={(event) => setEditorForm((previous) => ({ ...previous, base_price: event.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-[0.18em] text-white/45">Moeda</label>
                      <select
                        className="mt-2 w-full rounded-2xl border border-white/15 bg-black/25 px-4 py-3 text-sm outline-none"
                        value={editorForm.currency}
                        onChange={(event) => setEditorForm((previous) => ({ ...previous, currency: event.target.value }))}
                      >
                        <option value="BRL">BRL</option>
                        <option value="USD">USD</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/45">Estado</p>
                  <label className="mt-4 flex items-center gap-2 text-sm text-white/75">
                    <input
                      type="checkbox"
                      checked={editorForm.is_active}
                      onChange={(event) => setEditorForm((previous) => ({ ...previous, is_active: event.target.checked }))}
                    />
                    Produto ativo
                  </label>
                  <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/65">
                    <p>
                      <span className="text-white/40">Id:</span> {selectedProduct.id}
                    </p>
                    <p>
                      <span className="text-white/40">Versão:</span> v{selectedProduct.version_no}
                    </p>
                    <p>
                      <span className="text-white/40">Atualizado:</span> {formatDateTimeSP(selectedProduct.updated_at)}
                    </p>
                    <p>
                      <span className="text-white/40">Criado:</span> {formatDateTimeSP(selectedProduct.created_at)}
                    </p>
                  </div>
                  <button
                    className="mt-4 w-full rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                    type="submit"
                    disabled={isSaving}
                  >
                    {isSaving ? "Salvando..." : "Salvar alterações"}
                  </button>
                </div>
              </form>
            ) : (
              <div className="mt-5">
                <EmptyState
                  title="Selecione um produto"
                  description="Use o painel à esquerda para carregar um produto e liberar a edição ou exclusão."
                />
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
