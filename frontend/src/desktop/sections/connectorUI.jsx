import { ChevronDown, Loader2 } from "lucide-react";

// Marcas reales, inline (sin assets externos — mismo criterio que el resto
// de la app): un conector reconocible de un vistazo pesa más para la
// confianza/adopción que un ícono genérico. CSV/BCRA/MCP no tienen una marca
// propia que valga la pena reproducir; Odoo y WhatsApp sí.
export function LogoWhatsApp({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="#25D366" aria-hidden="true">
      <path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-2-1.2 7.4 7.4 0 0 1-1.4-1.7c-.1-.2 0-.4.1-.5l.4-.5a1.7 1.7 0 0 0 .3-.4.5.5 0 0 0 0-.4c0-.1-.6-1.4-.8-1.9s-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 2.9 2.9 0 0 0-.9 2.2 5 5 0 0 0 1 2.7 11.4 11.4 0 0 0 4.4 3.9 14.8 14.8 0 0 0 1.5.5 3.6 3.6 0 0 0 1.6.1 2.7 2.7 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .2-1.2c-.1-.1-.2-.2-.4-.3Z" />
    </svg>
  );
}

export function LogoOdoo({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="#714B67" />
      <path fillRule="evenodd" clipRule="evenodd"
        d="M12 6.4a5.6 5.6 0 1 0 0 11.2 5.6 5.6 0 0 0 0-11.2Zm0 2.5a3.1 3.1 0 1 1 0 6.2 3.1 3.1 0 0 1 0-6.2Z"
        fill="#fff" />
    </svg>
  );
}

// Shared visual language for every connector panel (Odoo, WhatsApp, and
// whatever comes next): one card shell, one status-pill vocabulary, one
// field style, one button hierarchy, one sync/ingest action row. Before this,
// each connector hand-rolled its own header/button/pill markup and quietly
// drifted (e.g. borrowing Ángela's exclusive blue for a plain "Conectar"
// button — index.css's own comment reserves that hue for the agent).
// Primary actions use `tinta`, matching every other primary button in the
// app (Login, Caja, GestionEquipo…); `violeta` stays reserved for a
// connector that IS Ángela at work (the WhatsApp bot's icon badge), never a
// plain form submit.

// --- status pill --------------------------------------------------------

const PILL_VARIANTS = {
  activo: { dot: "bg-salvia", text: "text-salvia", ring: "ring-salvia/20" },
  pendiente: { dot: "bg-tinta-suave", text: "text-tinta-suave", ring: "ring-linea" },
  proximamente: { dot: "bg-tinta-suave/50", text: "text-tinta-suave", ring: "ring-linea" },
  pausado: { dot: "bg-oro", text: "text-oro-tinta", ring: "ring-oro/20" },
};

export function ConnectorStatusPill({ variant = "pendiente", children }) {
  const s = PILL_VARIANTS[variant] || PILL_VARIANTS.pendiente;
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full bg-crema px-2.5 py-1 text-[0.74rem] font-semibold ring-1 ${s.ring} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {children}
    </span>
  );
}

// --- card shell: icon badge + title + subtitle + status + optional toggle ---

export function ConnectorCard({
  icon: Icon, logo: Logo, tone = "neutral", title, subtitle, status,
  expanded, onToggle, children, footer,
}) {
  const badgeTone =
    tone === "agent" ? "bg-violeta/10 text-violeta"
    : tone === "active" ? "bg-salvia/12 text-salvia"
    : "bg-papel-hondo text-tinta-suave";
  const interactive = typeof onToggle === "function";
  const Wrapper = interactive ? "button" : "div";

  return (
    <div className="rounded-[var(--radius-card)] border border-linea bg-crema sombra-papel">
      <Wrapper
        type={interactive ? "button" : undefined}
        onClick={onToggle}
        aria-expanded={interactive ? !!expanded : undefined}
        className={`flex w-full items-center gap-3 p-4 text-left ${interactive ? "cursor-pointer" : ""}`}
      >
        {/* Una marca real (Logo) trae su propio color — vive en un chip neutro
            con un hairline, no en el badge tonal que usan los íconos genéricos. */}
        {Logo ? (
          <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-full ring-1 ring-linea">
            <Logo size={22} />
          </span>
        ) : (
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${badgeTone}`}>
            <Icon size={18} />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-display text-[1.02rem] font-bold leading-tight text-tinta">{title}</span>
            {status}
          </span>
          {subtitle && <span className="mt-0.5 block truncate text-[0.82rem] text-tinta-suave">{subtitle}</span>}
        </span>
        {interactive && (
          <ChevronDown size={17} className={`shrink-0 text-tinta-suave transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
        )}
      </Wrapper>
      {(expanded || !interactive) && children && (
        <div className="space-y-3.5 border-t border-linea px-4 pb-4 pt-3.5">{children}</div>
      )}
      {footer}
    </div>
  );
}

// --- form field -----------------------------------------------------------

export function ConnectorField({ label, hint, type = "text", value, onChange, placeholder, required = true }) {
  return (
    <label className="block text-[0.8rem]">
      <span className="mb-1 block font-semibold text-tinta">{label}</span>
      <input required={required} type={type} value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-linea bg-papel px-3 py-2 text-[0.85rem]
                   text-tinta outline-none transition-colors focus:border-tinta/40" />
      {hint && <span className="mt-1 block text-[0.74rem] leading-snug text-tinta-suave">{hint}</span>}
    </label>
  );
}

// --- buttons ----------------------------------------------------------------

const BUTTON_VARIANTS = {
  primary: "border border-tinta bg-tinta text-crema disabled:opacity-40",
  secondary: "border border-linea bg-crema text-tinta hover:border-tinta/40 disabled:opacity-40",
  ghost: "border border-transparent text-tinta-suave hover:text-tinta disabled:opacity-40",
  danger: "border border-transparent text-tinta-suave hover:text-rojo-hondo disabled:opacity-40",
};

export function ConnectorButton({ variant = "primary", icon: Icon, loading, children, className = "", ...props }) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[0.8rem]
                  font-semibold transition-colors active:scale-[0.99] ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : Icon ? <Icon size={14} /> : null}
      {children}
    </button>
  );
}

// --- the recurring "traer X" / "ingestar X" action row (9× in Odoo) ---------

export function ConnectorSyncAction({
  onFetch, onIngest, fetching, ingesting,
  fetchLabel, fetchingLabel, ingestLabel, ingestingLabel,
  error, errorIngest, children,
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <ConnectorButton variant="secondary" onClick={onFetch} loading={fetching}>
          {fetching ? fetchingLabel : fetchLabel}
        </ConnectorButton>
        {onIngest && (
          <ConnectorButton variant="primary" onClick={onIngest} loading={ingesting}>
            {ingesting ? ingestingLabel : ingestLabel}
          </ConnectorButton>
        )}
      </div>
      {error && <p className="text-[0.8rem] text-rojo-hondo">{error}</p>}
      {errorIngest && <p className="text-[0.8rem] text-rojo-hondo">{errorIngest}</p>}
      {children}
    </div>
  );
}

// --- empty state for preview lists ------------------------------------------

export function ConnectorEmptyState({ icon: Icon, children }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-linea px-4 py-7 text-center">
      {Icon && <Icon size={20} className="text-tinta-suave/60" />}
      <p className="max-w-xs text-[0.82rem] leading-snug text-tinta-suave">{children}</p>
    </div>
  );
}
