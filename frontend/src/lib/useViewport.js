import { useEffect, useState } from "react";

// Decide qué superficie renderizar. >=1024px = la compu (sistema operativo).
// Debajo = el celular (torre de control). Un cerebro, dos caras.
const DESKTOP_MIN = 1024;

export function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    typeof window !== "undefined" ? window.innerWidth >= DESKTOP_MIN : true
  );
  useEffect(() => {
    const onResize = () => setIsDesktop(window.innerWidth >= DESKTOP_MIN);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return isDesktop;
}
