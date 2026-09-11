import { Component } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { t } from "../lib/i18n";

// P29·A2 — regla general del producto: NUNCA una pantalla muda. Si una
// sección revienta en render, se muestra un estado de error honesto y
// navegable (reintentar / volver al inicio) y el detalle queda en consola
// para el diagnóstico. El boundary se resetea al cambiar de sección (la key
// la pone el shell), así un error no persigue al usuario por toda la app.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // El detalle real, visible para quien diagnostica — nunca para esconderlo.
    console.error("[seccion rota]", this.props.seccion || "?", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="rounded-[var(--radius-card)] border border-rojo/25 bg-rojo/[0.04] p-8 text-center">
        <AlertTriangle size={26} className="mx-auto text-rojo" />
        <p className="mt-3 font-display text-[1.15rem] font-bold">{t("error.seccion_titulo")}</p>
        <p className="mx-auto mt-1 max-w-md text-[0.9rem] leading-snug text-tinta-suave">
          {t("error.seccion_detalle")}
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <button onClick={() => this.setState({ error: null })}
            className="inline-flex items-center gap-1.5 rounded-full bg-tinta px-4 py-2 text-[0.85rem] font-semibold text-crema">
            <RotateCcw size={14} /> {t("error.reintentar")}
          </button>
          {this.props.onInicio && (
            <button onClick={this.props.onInicio}
              className="inline-flex items-center gap-1.5 rounded-full border border-linea px-4 py-2 text-[0.85rem] font-semibold text-tinta-suave hover:text-tinta">
              <Home size={14} /> {t("error.ir_inicio")}
            </button>
          )}
        </div>
      </div>
    );
  }
}
