import { useEffect, useState } from "react";
import { MessageCircle, Copy, Check, ChevronDown, MessagesSquare } from "lucide-react";
import AngelaSays from "../../components/AngelaSays";
import Cargando from "../../components/Cargando";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";
import { ConnectorCard, ConnectorStatusPill, ConnectorField, ConnectorButton, ConnectorEmptyState } from "./connectorUI";

// El canal de WhatsApp de VENTAS: el tenant conecta su propio número de
// WhatsApp Business (Meta Cloud API) para que sus clientes pidan catálogo,
// armen un pedido o pidan un presupuesto por chat, con Ángela atendiendo del
// otro lado. Ver core/whatsapp_channel.py y backend/whatsapp_bot.py. Distinto
// del WhatsApp interno de empleados (ese no tiene configuración: ya anda con
// el teléfono cargado en el perfil de cada uno). Mismo lenguaje visual que
// el panel de Odoo en Conectores.jsx (ver connectorUI.jsx) — son la misma
// familia de pantalla, aunque este canal ES Ángela y no un caño de datos.
export default function WhatsAppBot() {
  const t = useT();
  const [cfg, setCfg] = useState(null); // null=cargando, false=error
  const [form, setForm] = useState({
    phone_number_id: "", access_token: "", app_secret: "", greeting_message: "", enabled: true,
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [conversaciones, setConversaciones] = useState(null);
  const [abierta, setAbierta] = useState(null);
  const [mensajes, setMensajes] = useState(null);

  const cargar = () => api.whatsappBotConfig().then(setCfg).catch(() => setCfg(false));
  useEffect(() => { cargar(); }, []);

  useEffect(() => {
    if (cfg?.conectado) {
      api.whatsappBotConversaciones().then((r) => setConversaciones(r.conversaciones)).catch(() => setConversaciones([]));
    }
  }, [cfg?.conectado]);

  const conectar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await api.whatsappBotConfigGuardar(form);
      setForm({ phone_number_id: "", access_token: "", app_secret: "", greeting_message: "", enabled: true });
      await cargar();
    } catch (err) {
      setError(err.status === 400 ? t("whatsapp_bot.error_guardar") : t("whatsapp_bot.error_generico"));
    } finally {
      setGuardando(false);
    }
  };

  const desconectar = async () => {
    try { await api.whatsappBotConfigBorrar(); } catch { /* best-effort */ }
    await cargar();
    setConversaciones(null);
  };

  const webhookUrl = `${window.location.origin}/api/webhooks/whatsapp`;
  const copiarWebhook = () => {
    navigator.clipboard?.writeText(webhookUrl).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    });
  };

  const verConversacion = async (id) => {
    if (abierta === id) { setAbierta(null); return; }
    setAbierta(id);
    setMensajes(null);
    try {
      const r = await api.whatsappBotMensajes(id);
      setMensajes(r.mensajes);
    } catch {
      setMensajes([]);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">{t("whatsapp_bot.titulo")}</h1>
        <p className="mt-1 text-[0.9rem] text-tinta-suave">{t("whatsapp_bot.subtitulo")}</p>
      </header>

      <AngelaSays>{t("whatsapp_bot.angela")}</AngelaSays>

      {cfg === null && <Cargando />}
      {cfg === false && <p className="text-[0.9rem] text-rojo-hondo">{t("whatsapp_bot.error_generico")}</p>}

      {cfg && (
        <ConnectorCard
          icon={MessageCircle}
          tone={cfg.conectado && cfg.enabled ? "active" : "agent"}
          title={t("whatsapp_bot.canal_nombre")}
          subtitle={cfg.conectado
            ? t(cfg.business_name ? "whatsapp_bot.conectado_como_empresa" : "whatsapp_bot.conectado_como", {
                numero: cfg.display_phone_number || cfg.phone_number_id, empresa: cfg.business_name,
              })
            : t("whatsapp_bot.no_conectado")}
          status={cfg.conectado && (
            <ConnectorStatusPill variant={cfg.enabled ? "activo" : "pausado"}>
              {t(cfg.enabled ? "whatsapp_bot.estado_activo" : "whatsapp_bot.estado_pausado")}
            </ConnectorStatusPill>
          )}
        >
          {cfg.conectado ? (
            <>
              <div>
                <p className="text-[0.78rem] font-semibold uppercase tracking-[0.08em] text-tinta-suave">
                  {t("whatsapp_bot.saludo_actual")}
                </p>
                <p className="mt-1.5 rounded-xl bg-papel-hondo/40 p-3 text-[0.85rem] leading-snug text-tinta">
                  {cfg.greeting_message || t("whatsapp_bot.sin_saludo")}
                </p>
              </div>
              <div className="border-t border-linea pt-3.5">
                <ConnectorButton variant="danger" onClick={desconectar}>{t("whatsapp_bot.desconectar")}</ConnectorButton>
              </div>
            </>
          ) : (
            <>
              <ol className="space-y-3">
                <li className="rounded-xl bg-papel-hondo/40 p-3">
                  <p className="text-[0.85rem] font-semibold text-tinta">{t("whatsapp_bot.paso_webhook_titulo")}</p>
                  <p className="mt-0.5 text-[0.82rem] leading-snug text-tinta-suave">{t("whatsapp_bot.paso_webhook_desc")}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="min-w-0 flex-1 truncate rounded-lg border border-linea bg-papel px-2.5 py-1.5 text-[0.78rem] text-tinta">
                      {webhookUrl}
                    </code>
                    <button type="button" onClick={copiarWebhook} aria-label={t("whatsapp_bot.copiar_webhook")}
                      className="shrink-0 rounded-lg border border-linea p-1.5 text-tinta-suave transition-colors hover:border-tinta/40 hover:text-tinta">
                      {copiado ? <Check size={14} className="text-salvia" /> : <Copy size={14} />}
                    </button>
                  </div>
                </li>
                <li className="rounded-xl bg-papel-hondo/40 p-3">
                  <p className="text-[0.85rem] font-semibold text-tinta">{t("whatsapp_bot.paso_credenciales_titulo")}</p>
                  <p className="mt-0.5 text-[0.82rem] leading-snug text-tinta-suave">{t("whatsapp_bot.paso_credenciales_desc")}</p>
                  <form onSubmit={conectar} className="mt-3 space-y-3">
                    <ConnectorField label={t("whatsapp_bot.campo_phone_number_id")} value={form.phone_number_id}
                      hint={t("whatsapp_bot.campo_phone_number_id_hint")}
                      onChange={(v) => setForm((f) => ({ ...f, phone_number_id: v }))} />
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ConnectorField label={t("whatsapp_bot.campo_access_token")} type="password" value={form.access_token}
                        onChange={(v) => setForm((f) => ({ ...f, access_token: v }))} />
                      <ConnectorField label={t("whatsapp_bot.campo_app_secret")} type="password" value={form.app_secret}
                        onChange={(v) => setForm((f) => ({ ...f, app_secret: v }))} />
                    </div>
                    <label className="block text-[0.8rem]">
                      <span className="mb-1 block font-semibold text-tinta">{t("whatsapp_bot.campo_saludo")}</span>
                      <textarea value={form.greeting_message} rows={2}
                        placeholder={t("whatsapp_bot.campo_saludo_placeholder")}
                        onChange={(e) => setForm((f) => ({ ...f, greeting_message: e.target.value }))}
                        className="w-full rounded-xl border border-linea bg-papel px-3 py-2 text-[0.85rem]
                                   text-tinta outline-none transition-colors focus:border-tinta/40" />
                    </label>
                    {error && <p className="text-[0.8rem] text-rojo-hondo">{error}</p>}
                    <ConnectorButton type="submit" loading={guardando}>
                      {guardando ? t("whatsapp_bot.conectando") : t("whatsapp_bot.conectar")}
                    </ConnectorButton>
                  </form>
                </li>
              </ol>
            </>
          )}
          <p className="text-[0.78rem] leading-snug text-tinta-suave">{t("whatsapp_bot.nota")}</p>
        </ConnectorCard>
      )}

      {cfg?.conectado && (
        <div className="rounded-[var(--radius-card)] border border-linea bg-crema p-4 sombra-papel">
          <h2 className="font-display text-[1.02rem] font-bold text-tinta">{t("whatsapp_bot.conversaciones_titulo")}</h2>
          <p className="mt-0.5 text-[0.82rem] text-tinta-suave">{t("whatsapp_bot.conversaciones_desc")}</p>

          {conversaciones === null && <div className="mt-3"><Cargando /></div>}

          {conversaciones?.length === 0 && (
            <div className="mt-3">
              <ConnectorEmptyState icon={MessagesSquare}>{t("whatsapp_bot.conversaciones_vacio")}</ConnectorEmptyState>
            </div>
          )}

          {conversaciones?.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {conversaciones.map((c) => (
                <li key={c.id} className="overflow-hidden rounded-xl border border-linea/60 bg-papel-hondo/30">
                  <button onClick={() => verConversacion(c.id)} aria-expanded={abierta === c.id}
                    className="flex w-full items-center gap-2.5 p-2.5 text-left transition-colors hover:bg-papel-hondo/60">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-crema text-[0.78rem] font-bold text-tinta-suave">
                      {(c.customer_name || c.customer_phone || "?").slice(0, 1).toUpperCase()}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[0.85rem] font-semibold text-tinta">
                        {c.customer_name || c.customer_phone}
                      </span>
                      <span className="block truncate text-[0.76rem] text-tinta-suave">{c.customer_phone}</span>
                    </span>
                    {c.status === "necesita_atencion" && (
                      <span className="shrink-0 rounded-full bg-oro/10 px-2 py-0.5 text-[0.72rem] font-semibold text-oro-tinta">
                        {t("whatsapp_bot.necesita_atencion")}
                      </span>
                    )}
                    <ChevronDown size={15} className={`shrink-0 text-tinta-suave transition-transform duration-200 ${abierta === c.id ? "rotate-180" : ""}`} />
                  </button>
                  {abierta === c.id && (
                    <div className="space-y-1.5 border-t border-linea/60 bg-papel/60 p-2.5">
                      {mensajes === null && <Cargando />}
                      {mensajes?.map((m) => (
                        <p key={m.id} className={`max-w-[85%] rounded-xl px-3 py-1.5 text-[0.82rem] leading-snug ${
                          m.direction === "in"
                            ? "bg-crema text-tinta"
                            : "ml-auto bg-violeta/10 text-tinta"}`}>
                          {m.body}
                        </p>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
