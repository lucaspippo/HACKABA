// La esfera de Ángela: la identidad visual del agente. CSS puro, sin libs.
// Estados (solo eventos reales del producto):
//   idle       — quieta, respiración casi imperceptible
//   pensando   — pulso suave mientras espera respuesta del modelo
//   ejecutando — brillo interno girando mientras corre una acción aprobada
//   esperando  — halo naranja pulsante: hay una propuesta que espera tu OK
// `pulse` queda como alias de "pensando" para los call-sites históricos.
export default function AngelaMark({ size = 40, pulse = false, estado }) {
  const st = estado || (pulse ? "pensando" : "idle");
  return (
    <span
      className={`esfera esfera--${st} relative inline-block shrink-0 rounded-full`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {st === "ejecutando" && <span className="esfera-giro absolute inset-0 rounded-full" />}
    </span>
  );
}
