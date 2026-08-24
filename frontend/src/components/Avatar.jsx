import { useState } from "react";

// Avatar unificado (P17·E2b): la foto real si el perfil la tiene; si no — o si
// la imagen falla en cargar — iniciales con el color del usuario. Jamás una
// imagen rota en pantalla.
export default function Avatar({ persona, size = 36, className = "" }) {
  const [rota, setRota] = useState(false);
  const username = persona?.username;
  const px = { width: size, height: size };
  // Se intenta la foto siempre que haya username: el SERVER decide si existe
  // (404 → onError → iniciales). Así una sesión vieja sin el campo `foto`
  // no esconde una foto recién cargada.
  if (username && !rota) {
    return (
      <img
        src={`/api/perfil/${username}/foto`}
        alt=""
        style={px}
        onError={() => setRota(true)}
        className={`shrink-0 rounded-full object-cover ${className}`}
        draggable="false"
      />
    );
  }
  return (
    <span
      style={{ ...px, background: persona?.color || "#6e6a63", fontSize: Math.max(11, size * 0.4) }}
      className={`grid shrink-0 place-items-center rounded-full font-bold text-crema ${className}`}
    >
      {(persona?.nombre || "?")[0]}
    </span>
  );
}
