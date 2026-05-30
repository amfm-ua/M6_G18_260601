// app.jsx — Grestel Financial Dashboard

const { useState, useMemo, useEffect, useCallback } = React;

// -----------------------------------------------------------------------------
// Navigation config
// -----------------------------------------------------------------------------
const NAV = [
  { id: "overview",     label: "Visão Geral",       group: "Síntese" },
  { id: "valuation_mc", label: "Avaliação MC",      group: "Síntese" },
  { id: "dr",           label: "DR", group: "Demonstrações Financeiras" },
  { id: "balanco",      label: "Balanço",           group: "Demonstrações Financeiras" },
  { id: "dfc",          label: "DFC",   group: "Demonstrações Financeiras" },
  { id: "vendas",       label: "Análise de Vendas", group: "Análise" },
  { id: "kpis",         label: "KPIs & Rácios",     group: "Análise" },
  { id: "fse",          label: "FSE",     group: "Análise" },
  { id: "pessoal",      label: "Gastos com Pessoal", group: "Análise" },
  { id: "rolling",        label: "Rolling Forecast 2025",   group: "Análise" },
  { id: "smart",          label: "Objetivos SMART",        group: "Análise" },
  { id: "sensibilidade",  label: "Análise de Sensibilidade", group: "Análise" },
  { id: "cenarios",       label: "Análise de Cenários",    group: "Análise" },
  { id: "producao",       label: "Orçamento de Produção",   group: "Produção" },
  { id: "hub",            label: "Hub Logístico",          group: "Projetos" },
  { id: "ecogres",        label: "ECOGRES",                group: "Análise" },
  { id: "pressupostos", label: "Pressupostos",      group: "Configuração" },
  { id: "yaml_editor", label: "Editor YAML",       group: "Configuração" },
];

// -----------------------------------------------------------------------------
// Shell
// -----------------------------------------------------------------------------
function App() {
  const [view, setView] = useState("overview");
  const [scenario, setScenario] = useState("Base");
  const [hubOn, setHubOn] = useState(false);
  const [cozeduraOn, setCozeduraOn] = useState(false);
  const [customScenarios, setCustomScenarios] = useState([]);
  const [showScenarioModal, setShowScenarioModal] = useState(false);
  // Ecogres é subsidiária — sempre consolidada
  const ecogresOn = true;

  useEffect(() => {
    API.listCustomScenarios()
      .then(list => setCustomScenarios(list))
      .catch(() => {});
  }, []);

  function handleAddCustomScenario(sc) {
    setCustomScenarios(prev => {
      const idx = prev.findIndex(s => s.name === sc.name);
      if (idx >= 0) { const next = [...prev]; next[idx] = sc; return next; }
      return [...prev, sc];
    });
    setScenario(sc.name);
    setShowScenarioModal(false);
  }

  function handleDeleteCustomScenario(name) {
    API.deleteCustomScenario(name)
      .then(() => {
        setCustomScenarios(prev => prev.filter(s => s.name !== name));
        if (scenario === name) setScenario("Base");
      })
      .catch(e => alert("Erro ao eliminar: " + e.message));
  }

  // Hub Logístico está sempre ativo quando a sua vista está selecionada
  const hubLocked = view === "hub";
  const effectiveHubOn = hubLocked || hubOn;

  // Estado assíncrono
  const [ctx, setCtx] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState({
    source: API.useMock ? "mock" : "live",
    connected: false,
    lastRun: null,
    engineVersion: null,
  });
  // Health check inicial
  useEffect(() => {
    API.health()
      .then(h => setApiStatus(s => ({
        ...s,
        connected: true,
        lastRun: h.last_engine_run,
        engineVersion: h.engine_version,
      })))
      .catch(() => setApiStatus(s => ({ ...s, connected: false })));
  }, []);

  // Fetch da projeção quando muda cenário/hub
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      API.projecao({ cenario: scenario, hub_on: effectiveHubOn, ecogres_on: ecogresOn, cozedura_on: cozeduraOn }),
      // Taxa de IRC efetiva da API (fonte de verdade única, C-1). Fallback
      // silencioso para o default offline se a chamada falhar.
      API.assumptions({ cenario: scenario, hub_on: effectiveHubOn, ecogres_on: ecogresOn, cozedura_on: cozeduraOn })
        .catch(() => ({})),
    ])
      .then(([data, assum]) => {
        if (cancelled) return;
        setCtx({
          dr: data.dr,
          bal: data.balanco,
          dfc: data.dfc,
          kpis: data.kpis,
          fse: data.fse,
          pessoal: data.pessoal,
          ircTaxaEfetiva: assum.irc_taxa_efetiva ?? GRESTEL.IRC_TAXA_EFETIVA,
          scenario: scenario, hubOn: effectiveHubOn, ecogresOn, cozeduraOn,
        });
        setLoading(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message || String(err));
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [scenario, effectiveHubOn, ecogresOn, cozeduraOn]);

  return (
    <div className="app">
      <Sidebar view={view} setView={setView} apiStatus={apiStatus} />
      <div className="main">
        <Topbar
          view={view}
          scenario={scenario}
          setScenario={setScenario}
          hubOn={effectiveHubOn}
          setHubOn={setHubOn}
          hubLocked={hubLocked}
          cozeduraOn={cozeduraOn}
          setCozeduraOn={setCozeduraOn}
          loading={loading}
          ecogresOn={ecogresOn}
          customScenarios={customScenarios}
          onAddScenario={() => setShowScenarioModal(true)}
          onDeleteScenario={handleDeleteCustomScenario}
        />
        {showScenarioModal && (
          <CustomScenarioModal
            onClose={() => setShowScenarioModal(false)}
            onSave={handleAddCustomScenario}
          />
        )}
        <div className="content">
          {view === "yaml_editor" ? (
            <YamlEditorView />
          ) : (
            <>
              {error && <ErrorBanner message={error} onRetry={() => setScenario(s => s)} />}
              {!ctx && loading && <LoadingShell view={view} />}
              {loading && ctx && <LoadingOverlay hubOn={effectiveHubOn} scenario={scenario} />}
              {ctx && (
                <>
                  {view === "overview" && <OverviewView ctx={ctx} />}
                  {view === "dr" && <DRView ctx={ctx} />}
                  {view === "balanco" && <BalancoView ctx={ctx} />}
                  {view === "dfc" && <DFCView ctx={ctx} />}
                  {view === "kpis" && <KPIView ctx={ctx} />}
                  {view === "vendas" && <VendasView ctx={ctx} />}
                  {view === "fse" && <FSEView ctx={ctx} />}
                  {view === "pessoal" && <PessoalView ctx={ctx} />}
                  {view === "rolling" && <RollingView ctx={ctx} />}
                  {view === "smart" && <SmartView ctx={ctx} />}
                  {view === "sensibilidade" && <SensibilidadeView ctx={ctx} />}
                  {view === "cenarios" && <CenariosView ctx={ctx} />}
                  {view === "producao" && <ProducaoView ctx={ctx} />}
                  {view === "hub" && <HubView ctx={ctx} />}
                  {view === "valuation_mc" && <ValuationMCView ctx={ctx} />}
                  {view === "ecogres" && <EcogresView ctx={ctx} />}
                  {view === "pressupostos" && <PressupostosView ctx={ctx} />}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading + Error
// ---------------------------------------------------------------------------
function Skeleton({ width = "100%", height = 14, style }) {
  return (
    <div
      style={{
        width, height,
        background: "linear-gradient(90deg, var(--surface-2) 0%, var(--rule) 50%, var(--surface-2) 100%)",
        backgroundSize: "200% 100%",
        animation: "sk-shimmer 1.4s ease-in-out infinite",
        ...style,
      }}
    />
  );
}

function SkeletonKPI() {
  return (
    <div className="kpi">
      <Skeleton width="55%" height={10} style={{ marginBottom: 10 }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <Skeleton width="60%" height={22} />
        <Skeleton width={80} height={28} />
      </div>
      <div style={{ marginTop: 8 }}>
        <Skeleton width="40%" height={11} />
      </div>
    </div>
  );
}

function SkeletonPanel({ chartHeight = 280 }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <Skeleton width={220} height={14} style={{ marginBottom: 6 }} />
          <Skeleton width={140} height={11} />
        </div>
      </div>
      <div className="panel-body">
        <Skeleton width="100%" height={chartHeight} />
      </div>
    </div>
  );
}

function LoadingShell({ view }) {
  return (
    <>
      <div className="grid-kpis">
        {Array.from({ length: 6 }).map((_, i) => <SkeletonKPI key={i} />)}
      </div>
      <div className="grid-2-3">
        <SkeletonPanel chartHeight={300} />
        <SkeletonPanel chartHeight={300} />
      </div>
      <SkeletonPanel chartHeight={220} />
    </>
  );
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div
      className="panel"
      style={{
        borderColor: "var(--neg)",
        borderLeftWidth: 3,
        background: "var(--neg-soft)",
      }}
    >
      <div style={{ padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ fontWeight: 500, color: "var(--ink)", fontSize: 13 }}>Falha ao carregar dados</div>
          <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 2, fontFamily: "var(--mono)" }}>{message}</div>
        </div>
        <button className="btn-ghost" onClick={onRetry}>Tentar de novo</button>
      </div>
    </div>
  );
}

function Sidebar({ view, setView, apiStatus }) {
  const groups = {};
  for (const item of NAV) {
    (groups[item.group] ||= []).push(item);
  }
  const isMock = apiStatus.source === "mock";
  const connected = apiStatus.connected;
  const dotClass = connected
    ? (isMock ? "dot dot--mock" : "dot dot--ok")
    : "dot dot--err";
  const statusLabel = !connected ? "offline" : (isMock ? "mock" : "live");
  const lastRun = apiStatus.lastRun ? fmtIsoDate(apiStatus.lastRun) : "—";
  return (
    <aside className="sidebar">
      <div className="brand">
        <img className="brand-logo" src="assets/grestel-logo.png" alt="Grestel" />
        <div>
          <div className="brand-sub">PEF G18 M6 · v1.0</div>
        </div>
      </div>
      <nav className="nav">
        {Object.entries(groups).map(([g, items]) => (
          <div key={g} className="nav-group">
            <div className="nav-label">{g}</div>
            {items.map(it => (
              <button
                key={it.id}
                className={"nav-item " + (view === it.id ? "is-active" : "")}
                onClick={() => setView(it.id)}
              >
                {it.label}
              </button>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="foot-row">
          <span>API</span>
          <span><span className={dotClass} /> <span className="mono">{statusLabel}</span></span>
        </div>
        <div className="foot-row"><span>Engine</span><span className="mono">{apiStatus.engineVersion || "—"}</span></div>
        <div className="foot-row"><span>Atualizado em</span><span className="mono">{lastRun}</span></div>
      </div>
    </aside>
  );
}

function fmtIsoDate(iso) {
  try {
    const d = new Date(iso);
    const dd = String(d.getDate()).padStart(2, "0");
    const months = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
    const mm = months[d.getMonth()];
    const yy = String(d.getFullYear()).slice(2);
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${dd} ${mm} ${yy} · ${hh}:${mi}`;
  } catch { return "—"; }
}

function Topbar({ view, scenario, setScenario, hubOn, setHubOn, hubLocked, cozeduraOn, setCozeduraOn, loading, ecogresOn, customScenarios = [], onAddScenario, onDeleteScenario }) {
  const [exporting, setExporting] = useState(false);
  const [exportingM3, setExportingM3] = useState(false);
  const title = NAV.find(n => n.id === view)?.label || "";
  const builtinDesc = GRESTEL.SCENARIOS[scenario]?.desc;
  const customDesc = customScenarios.find(s => s.name === scenario)?.description;
  const desc = builtinDesc || customDesc || "";

  async function handleExport() {
    setExporting(true);
    try {
      await API.exportExcel({ cenario: scenario, hub_on: hubOn, ecogres_on: ecogresOn });
    } catch (e) {
      alert("Erro ao exportar: " + e.message);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportM3() {
    setExportingM3(true);
    try {
      await API.exportM3({ cenario: scenario, hub_on: hubOn, ecogres_on: ecogresOn });
    } catch (e) {
      alert("Erro ao exportar M3: " + e.message);
    } finally {
      setExportingM3(false);
    }
  }

  return (
    <header className="topbar">
      <div className="topbar-l">
        <div className="crumbs">
          <span className="crumb-muted">{NAV.find(n => n.id === view)?.group}</span>
          <span className="crumb-sep">/</span>
          <span className="crumb">{title}</span>
          {loading && <span className="loading-dot" title="A carregar..." />}
        </div>
        <div className="topbar-desc">{desc}</div>
      </div>
      <div className="topbar-r">
        <div className="chip-static" title="Subsidiária — sempre consolidada">
          <span className="dot dot--ok" /> Ecogres
        </div>
        <div className="seg">
          {Object.keys(GRESTEL.SCENARIOS).map(k => (
            <button
              key={k}
              className={"seg-btn " + (scenario === k ? "is-on" : "")}
              onClick={() => setScenario(k)}
            >{GRESTEL.SCENARIOS[k].label}</button>
          ))}
          {customScenarios.map(sc => (
            <span key={sc.name} style={{ position: "relative", display: "inline-flex" }}>
              <button
                className={"seg-btn seg-btn--custom " + (scenario === sc.name ? "is-on" : "")}
                onClick={() => setScenario(sc.name)}
                title={sc.description || sc.label}
              >{sc.label || sc.name}</button>
              <button
                className="seg-btn-del"
                onClick={e => { e.stopPropagation(); onDeleteScenario(sc.name); }}
                title={"Eliminar " + (sc.label || sc.name)}
              >×</button>
            </span>
          ))}
          <button
            className="seg-btn seg-btn--add"
            onClick={onAddScenario}
            title="Criar cenário personalizado"
          >+</button>
        </div>
        <Toggle label="Hub Logístico" on={hubOn} onChange={setHubOn} locked={hubLocked} />
        <Toggle label="Cozedura BT" on={cozeduraOn} onChange={setCozeduraOn} />
        <button className="btn-ghost" disabled style={{ opacity: 0.45, cursor: "not-allowed" }} title="Exportação não disponível" aria-label="Exportar">
          <span aria-hidden="true">⤓</span>
        </button>
      </div>
    </header>
  );
}

function Toggle({ label, on, onChange, locked }) {
  return (
    <button
      className={"toggle " + (on ? "is-on" : "") + (locked ? " is-locked" : "")}
      onClick={locked ? undefined : () => onChange(!on)}
      style={locked ? { cursor: "default", opacity: 0.9 } : undefined}
      title={locked ? "Hub Logístico ativo nesta vista" : undefined}
    >
      <span className="toggle-track"><span className="toggle-thumb" /></span>
      <span className="toggle-label">{label}</span>
    </button>
  );
}

// -----------------------------------------------------------------------------
// KPI card
// -----------------------------------------------------------------------------
function KPI({ label, value, sub, trend, spark, sparkColor, tone, hint }) {
  return (
    <div className={"kpi " + (tone ? "kpi--" + tone : "")}>
      <div className="kpi-label">{label}{hint && <span className="kpi-hint" title={hint}>·</span>}</div>
      <div className="kpi-row">
        <div className="kpi-value">{value}</div>
        {spark && <Sparkline values={spark} color={sparkColor || "var(--muted)"} width={80} height={28} />}
      </div>
      <div className="kpi-foot">
        {trend != null && <span className={"delta " + (trend >= 0 ? "delta--pos" : "delta--neg")}>{fmt.pctSigned(trend)}</span>}
        {sub && <span className="kpi-sub">{sub}</span>}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Section panel
// -----------------------------------------------------------------------------
function Panel({ title, sub, right, children, pad = true }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">{title}</div>
          {sub && <div className="panel-sub">{sub}</div>}
        </div>
        {right && <div className="panel-right">{right}</div>}
      </div>
      <div className={"panel-body " + (pad ? "" : "panel-body--flat")}>{children}</div>
    </div>
  );
}

// =============================================================================
// VIEWS
// =============================================================================

// ---- Overview ---------------------------------------------------------------
function OverviewView({ ctx }) {
  const { dr, kpis } = ctx;
  const cur = dr.find(r => r.year === 2025);
  const prev = dr.find(r => r.year === 2024);
  const k2029 = kpis.find(r => r.year === 2029);

  const compareSeries = useMemo(() => {
    const colors = { Base: "var(--ink)", Upside: "var(--pos)", Downside: "var(--accent)", Stress: "var(--neg)" };
    return Object.keys(GRESTEL.SCENARIOS).map(k => {
      const d = GRESTEL.projectDR(k, { hubOn: ctx.hubOn, ecogresOn: ctx.ecogresOn });
      return {
        labels: GRESTEL.YEARS.map(String),
        values: d.map(r => r.vn),
        color: colors[k],
        width: k === ctx.scenario ? 2.4 : 1.4,
        dash: k === ctx.scenario ? null : "3 3",
        name: k,
        label: k,
      };
    });
  }, [ctx.hubOn, ctx.ecogresOn, ctx.scenario]);

  const ebitdaSeries = [{
    labels: GRESTEL.YEARS.map(String),
    values: dr.map(r => r.ebitda),
    color: "var(--accent)",
    fill: true,
    label: "EBITDA",
  }];

  const margemSeries = [
    { labels: GRESTEL.YEARS.map(String), values: dr.map(r => r.ebitda / r.vn), color: "var(--accent)", label: "Margem EBITDA" },
    { labels: GRESTEL.YEARS.map(String), values: dr.map(r => r.rl / r.vn), color: "var(--ink)", label: "Margem Líquida" },
  ];

  return (
    <>
      <div className="grid-kpis">
        <KPI
          label="Volume de Negócios"
          value={fmt.eurC(cur.vn)}
          trend={(cur.vn - prev.vn) / prev.vn}
          sub="vs. 2024 real"
          spark={dr.map(r => r.vn)}
          sparkColor="var(--ink)"
        />
        <KPI
          label="EBITDA"
          value={fmt.eurC(cur.ebitda)}
          trend={(cur.ebitda - prev.ebitda) / prev.ebitda}
          sub={"margem " + fmt.pct(cur.ebitda / cur.vn)}
          spark={dr.map(r => r.ebitda)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="Resultado Líquido"
          value={fmt.eurC(cur.rl)}
          trend={(cur.rl - prev.rl) / prev.rl}
          sub={"margem " + fmt.pct(cur.rl / cur.vn)}
          spark={dr.map(r => r.rl)}
          sparkColor="var(--pos)"
        />
        <KPI
          label="Margem EBITDA"
          value={fmt.pct(cur.ebitda / cur.vn)}
          trend={(cur.ebitda / cur.vn) - (prev.ebitda / prev.vn)}
          sub="pontos percentuais vs 2024"
          spark={dr.map(r => r.ebitda / r.vn)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="ROE 2029"
          value={fmt.pct(k2029.roe)}
          sub={"autonomia fin. " + fmt.pct(k2029.autonomia_financeira)}
          spark={kpis.map(r => r.roe)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="Caixa 2029"
          value={fmt.eurC(ctx.bal[ctx.bal.length - 1].Caixa)}
          sub={"endivid. " + fmt.pct(k2029.endividamento)}
          spark={ctx.bal.map(r => r.Caixa)}
          sparkColor="var(--ink)"
        />
      </div>

      <div className="grid-2-3">
        <Panel
          title="Volume de Negócios · Comparação de cenários"
          sub="€ milhões · 2024 real + projeção 2025–2029"
          right={<Legend items={[
            { label: "Base", color: "var(--ink)" },
            { label: "Upside", color: "var(--pos)" },
            { label: "Downside", color: "var(--accent)" },
            { label: "Stress", color: "var(--neg)" },
          ]} />}
        >
          <LineChart series={compareSeries} height={300} />
        </Panel>
        <Panel title="EBITDA" sub={"Cenário " + ctx.scenario}>
          <LineChart series={ebitdaSeries} height={300} />
        </Panel>
      </div>

      <div className="grid-2-3">
        <Panel
          title="Margens · EBITDA vs Resultado Líquido"
          sub="evolução em % do volume de negócios"
          right={<Legend items={[{ label: "Margem EBITDA", color: "var(--accent)" }, { label: "Margem Líquida", color: "var(--ink)" }]} />}
        >
          <LineChart series={margemSeries} height={260} yFormat={(v) => fmt.pct(v, 0)} />
        </Panel>
        <Panel title="Mix de mercado · vendas 2024" sub="por geografia">
          {(() => {
            // Terracota family — burnt sienna → terracota → ocre → areia.
            const geoPalette = [
              "oklch(0.34 0.075 40)",   // Portugal — burnt sienna escuro
              "oklch(0.54 0.115 45)",   // União Europeia — terracota
              "oklch(0.68 0.105 65)",   // Estados Unidos — ocre / clay
              "oklch(0.83 0.035 75)",   // Resto do Mundo — areia
            ];
            const chanPalette = [
              "oklch(0.34 0.075 40)",
              "oklch(0.54 0.115 45)",
              "oklch(0.68 0.105 65)",
              "oklch(0.83 0.035 75)",
            ];
            // Text colors — light text on the two darker segments, dark on the lighter two.
            const chanTextColor = [
              "var(--surface)",
              "var(--surface)",
              "var(--ink)",
              "var(--ink)",
            ];
            const totalVN = prev.vn;
            const geoItems = Object.entries(GRESTEL.MERCADOS).map(([k, v], i) => ({
              label: v.label,
              value: totalVN * v.peso,
              color: geoPalette[i],
            }));
            const chanItems = Object.entries(GRESTEL.CANAIS).map(([k, v], i) => ({
              label: k.replace(/_/g, " "),
              value: v,
              amount: totalVN * v,
              color: chanPalette[i],
              textColor: chanTextColor[i],
            }));
            return (
              <>
                <div className="donut-row">
                  <Donut items={geoItems} size={172} thickness={26} />
                  <div className="legend-col">
                    {geoItems.map((it, i) => (
                      <div key={i} className="legend-row">
                        <span className="swatch" style={{ background: it.color }} />
                        <span className="legend-label">{it.label}</span>
                        <span className="legend-value mono">{fmt.pct(it.value / totalVN, 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="sub-section">
                  <div className="sub-label">Canais 2024</div>
                  <StackedBar items={chanItems} height={34} />
                  <div className="legend-h" style={{ marginTop: 8 }}>
                    {chanItems.map((it, i) => (
                      <div key={i} className="legend-h-item">
                        <span className="swatch" style={{ background: it.color }} />
                        <span>{it.label}</span>
                        <span className="mono">{fmt.pct(it.value, 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            );
          })()}
        </Panel>
      </div>

      <Panel title="Quadro-síntese · 2025–2029" sub="cenário ativo">
        <table className="ftable">
          <thead>
            <tr>
              <th></th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            <FRow label="Volume de Negócios" values={dr.map(r => r.vn)} />
            <FRow label="EBITDA" values={dr.map(r => r.ebitda)} />
            <FRow label="EBIT" values={dr.map(r => r.ebit)} />
            <FRow label="Resultado Líquido" values={dr.map(r => r.rl)} bold />
            <tr className="row-sep"><td colSpan={GRESTEL.YEARS.length + 1}></td></tr>
            <FRow label="Margem EBITDA" values={dr.map(r => r.ebitda / r.vn)} fmt={(v) => fmt.pct(v)} />
            <FRow label="Margem Líquida" values={dr.map(r => r.rl / r.vn)} fmt={(v) => fmt.pct(v)} />
          </tbody>
        </table>
      </Panel>
    </>
  );
}

function FRow({ label, values, bold, fmt: f = fmt.eur, accentStart }) {
  return (
    <tr className={bold ? "is-bold" : ""}>
      <td>{label}</td>
      {values.map((v, i) => (
        <td key={i} className="mono num" style={accentStart && i >= 6 ? { color: "var(--accent)" } : {}}>{f(v)}</td>
      ))}
    </tr>
  );
}

function Legend({ items }) {
  return (
    <div className="legend">
      {items.map((it, i) => (
        <div key={i} className="legend-row">
          <span className="swatch" style={{ background: it.color }} />
          <span className="legend-label">{it.label}</span>
        </div>
      ))}
    </div>
  );
}

function LoadingOverlay({ hubOn, scenario }) {
  return (
    <div className="loading-overlay">
      <div className="loading-overlay-card">
        <div className="loading-spinner" />
        <div className="loading-overlay-label">A calcular projeção…</div>
        <div className="loading-overlay-sub">
          {scenario} · Hub Logístico {hubOn ? "ativo" : "desativado"}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// CustomScenarioModal
// -----------------------------------------------------------------------------
const DRIVER_YEARS = [2025, 2026, 2027, 2028, 2029];

function CustomScenarioModal({ onClose, onSave }) {
  const emptyRow = () => ({ vol: "", preco: "", fse: "" });
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [rows, setRows] = useState(Object.fromEntries(DRIVER_YEARS.map(y => [y, emptyRow()])));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  function setCell(year, field, value) {
    setRows(prev => ({ ...prev, [year]: { ...prev[year], [field]: value } }));
  }

  function parsePct(v) {
    const n = parseFloat(String(v).replace(",", "."));
    return isNaN(n) ? null : n / 100;
  }

  async function handleSave() {
    const trimName = name.trim();
    if (!trimName) { setErr("O nome do cenário é obrigatório."); return; }
    if (!/^[A-Za-z0-9_\- ]+$/.test(trimName)) { setErr("Nome apenas pode conter letras, números, espaços, - e _."); return; }

    const volOverrides = {}, pvuOverrides = {}, fseOverrides = {};
    for (const y of DRIVER_YEARS) {
      const r = rows[y];
      const key = y === 2025 ? "base_2025" : String(y);
      const vol = parsePct(r.vol);
      const pvu = parsePct(r.preco);
      const fse = parsePct(r.fse);
      if (vol != null) volOverrides[key] = vol;
      if (pvu != null) pvuOverrides[key] = pvu;
      if (fse != null) fseOverrides[key] = fse;
    }

    const overrides = {};
    if (Object.keys(volOverrides).length) overrides.crescimento_volume_vendas = volOverrides;
    if (Object.keys(pvuOverrides).length) overrides.crescimento_pvu_vendas    = pvuOverrides;
    if (Object.keys(fseOverrides).length) overrides.crescimento_fse           = fseOverrides;

    setSaving(true);
    setErr(null);
    try {
      await API.createCustomScenario(trimName, { label: trimName, description: desc.trim(), overrides });
      onSave({ name: trimName, label: trimName, description: desc.trim(), overrides });
    } catch (e) {
      setErr(e.message);
      setSaving(false);
    }
  }

  const overlayStyle = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
  };
  const cardStyle = {
    background: "var(--surface)", borderRadius: 8, padding: "24px 28px",
    width: 520, maxWidth: "95vw", boxShadow: "0 8px 32px rgba(0,0,0,0.28)",
    display: "flex", flexDirection: "column", gap: 16,
  };
  const labelStyle = { fontSize: 12, color: "var(--ink-2)", marginBottom: 4, display: "block" };
  const inputStyle = {
    width: "100%", background: "var(--surface-2)", border: "1px solid var(--rule)",
    borderRadius: 4, padding: "6px 9px", fontSize: 13, color: "var(--ink)", outline: "none",
    boxSizing: "border-box",
  };
  const cellInputStyle = {
    width: 72, background: "var(--surface-2)", border: "1px solid var(--rule)",
    borderRadius: 4, padding: "4px 6px", fontSize: 12, color: "var(--ink)",
    textAlign: "right", outline: "none",
  };

  return (
    <div style={overlayStyle} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Novo cenário personalizado</div>
          <button className="btn-ghost" style={{ padding: "2px 8px" }} onClick={onClose}>×</button>
        </div>

        <div>
          <label style={labelStyle}>Nome do cenário *</label>
          <input
            style={inputStyle}
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="ex: Tarifa_Alta"
            maxLength={40}
          />
        </div>
        <div>
          <label style={labelStyle}>Descrição (opcional)</label>
          <input
            style={inputStyle}
            value={desc}
            onChange={e => setDesc(e.target.value)}
            placeholder="Breve descrição do cenário"
            maxLength={120}
          />
        </div>

        <div>
          <div style={{ fontSize: 12, color: "var(--ink-2)", marginBottom: 8 }}>
            Crescimento por ano (em %; deixar em branco = herdar do Base)
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "4px 6px", color: "var(--ink-2)", fontWeight: 500 }}>Ano</th>
                <th style={{ textAlign: "right", padding: "4px 6px", color: "var(--ink-2)", fontWeight: 500 }}>Vol %</th>
                <th style={{ textAlign: "right", padding: "4px 6px", color: "var(--ink-2)", fontWeight: 500 }}>PVU %</th>
                <th style={{ textAlign: "right", padding: "4px 6px", color: "var(--ink-2)", fontWeight: 500 }}>FSE %</th>
              </tr>
            </thead>
            <tbody>
              {DRIVER_YEARS.map(y => (
                <tr key={y} style={{ borderTop: "1px solid var(--rule)" }}>
                  <td style={{ padding: "5px 6px", fontWeight: 500 }}>{y}</td>
                  {["vol", "preco", "fse"].map(f => (
                    <td key={f} style={{ padding: "4px 6px", textAlign: "right" }}>
                      <input
                        style={cellInputStyle}
                        type="number"
                        step="0.1"
                        value={rows[y][f]}
                        onChange={e => setCell(y, f, e.target.value)}
                        placeholder="—"
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {err && <div style={{ fontSize: 12, color: "var(--neg)", padding: "6px 8px", background: "var(--neg-soft)", borderRadius: 4 }}>{err}</div>}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={onClose} disabled={saving}>Cancelar</button>
          <button
            className="btn-ghost"
            style={{ background: "var(--accent)", color: "var(--surface)", border: "none" }}
            onClick={handleSave}
            disabled={saving}
          >{saving ? "A guardar…" : "Criar cenário"}</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { App, Sidebar, Topbar, Toggle, KPI, Panel, FRow, Legend, Skeleton, SkeletonKPI, SkeletonPanel, LoadingShell, LoadingOverlay, ErrorBanner, CustomScenarioModal });
