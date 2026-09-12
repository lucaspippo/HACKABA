import { Link } from "react-router-dom";

export function qLink(section, q) {
  if (q == null || q === "") return null;
  return `/${section}?q=${encodeURIComponent(String(q))}`;
}

export function paramLink(section, key, value) {
  if (value == null || value === "") return null;
  return `/${section}?${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`;
}

export default function CellLink({ to, children, title }) {
  if (!to || children == null || children === "" || children === "—") {
    return children == null || children === "" ? "—" : children;
  }
  return (
    <Link
      to={to}
      title={title}
      onClick={(e) => e.stopPropagation()}
      className="font-medium text-hielo decoration-hielo/30 underline-offset-2 transition-colors hover:text-hielo hover:underline"
    >
      {children}
    </Link>
  );
}
