import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

const PAGE = 50;
const FILTER_KEYS = ["proveedor", "deposito", "ubicacion", "tipo", "po_number", "sin_po", "proximos"];

function readFilters(params) {
  const out = {};
  for (const k of FILTER_KEYS) {
    const v = params.get(k);
    if (v) out[k] = v;
  }
  return out;
}

export function usePagedList(fetcher, extraDeps = []) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [facets, setFacets] = useState({});
  const [q, setQ] = useState(() => searchParams.get("q") || "");
  const [qDebounced, setQDebounced] = useState(() => searchParams.get("q") || "");
  const [sort, setSort] = useState({ campo: null, dir: 1 });
  const [source, setSource] = useState(() => searchParams.get("source") || "all");
  const [dateFrom, setDateFrom] = useState(() => searchParams.get("date_from") || "");
  const [dateTo, setDateTo] = useState(() => searchParams.get("date_to") || "");
  const [filters, setFilters] = useState(() => readFilters(searchParams));
  const [reloadKey, setReloadKey] = useState(0);
  const offsetRef = useRef(0);
  const loadingMoreRef = useRef(false);
  const skipUrl = useRef(true);

  useEffect(() => {
    const id = setTimeout(() => setQDebounced(q), 220);
    return () => clearTimeout(id);
  }, [q]);

  useEffect(() => {
    const incoming = searchParams.get("q") || "";
    if (incoming !== q && incoming !== qDebounced) setQ(incoming);
    const nextFrom = searchParams.get("date_from") || "";
    const nextTo = searchParams.get("date_to") || "";
    if (nextFrom !== dateFrom) setDateFrom(nextFrom);
    if (nextTo !== dateTo) setDateTo(nextTo);
    const nextSource = searchParams.get("source") || "all";
    if (nextSource !== source) setSource(nextSource);
    const nextFilters = readFilters(searchParams);
    if (JSON.stringify(nextFilters) !== JSON.stringify(filters)) setFilters(nextFilters);
    // Arrival from a deeplink (same section, new search) should win over local typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const query = useCallback(() => {
    const params = {
      q: qDebounced, offset: 0, limit: PAGE,
      source: source === "all" ? "" : source,
      ...filters,
    };
    if (sort.campo) {
      params.sort = sort.campo;
      params.dir = sort.dir === 1 ? "asc" : "desc";
    }
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [qDebounced, sort, source, dateFrom, dateTo, filters]);

  useEffect(() => {
    if (skipUrl.current) {
      skipUrl.current = false;
      return;
    }
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const apply = (k, v) => {
        if (v) next.set(k, String(v));
        else next.delete(k);
      };
      apply("q", qDebounced);
      apply("date_from", dateFrom);
      apply("date_to", dateTo);
      apply("source", source === "all" ? "" : source);
      for (const k of FILTER_KEYS) apply(k, filters[k]);
      if (next.toString() === prev.toString()) return prev;
      return next;
    }, { replace: true });
  }, [qDebounced, dateFrom, dateTo, source, filters, setSearchParams]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = query();
    fetcher(params).then((d) => {
      if (!alive) return;
      setItems(d.items || []);
      setTotal(d.total || 0);
      setHasMore(!!d.has_more);
      if (d.facets) setFacets(d.facets);
      offsetRef.current = (d.items || []).length;
      setError(null);
    }).catch((e) => { if (alive) setError(e); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
    // extraDeps lets a page pass filtro / err without forking the hook.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, query, reloadKey, ...extraDeps]);

  const loadMore = useCallback(() => {
    if (loadingMoreRef.current || !hasMore) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    const params = { ...query(), offset: offsetRef.current };
    fetcher(params).then((d) => {
      const batch = d.items || [];
      setItems((prev) => [...prev, ...batch]);
      setHasMore(!!d.has_more);
      offsetRef.current += batch.length;
    }).catch(() => {})
      .finally(() => {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      });
  }, [fetcher, hasMore, query]);

  const reload = () => setReloadKey((k) => k + 1);

  const toggleSort = (campo) => {
    setSort((o) => (o.campo === campo ? { campo, dir: -o.dir } : { campo, dir: 1 }));
  };

  const setFilter = (key, value) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (value == null || value === "" || value === false) delete next[key];
      else next[key] = value === true ? "1" : String(value);
      return next;
    });
  };

  const setDateRange = (from, to) => {
    setDateFrom(from || "");
    setDateTo(to || "");
  };

  const clearFilters = () => {
    setQ("");
    setSource("all");
    setDateFrom("");
    setDateTo("");
    setFilters({});
  };

  const hasActiveFilters = !!(q || dateFrom || dateTo || (source && source !== "all") || Object.keys(filters).length);

  return {
    items, total, hasMore, loading, loadingMore, error, facets,
    q, setQ, sort, toggleSort, source, setSource,
    dateFrom, setDateFrom, dateTo, setDateTo, setDateRange,
    filters, setFilter, clearFilters, hasActiveFilters,
    loadMore, reload, query,
  };
}

export function useQuerySeed(key = "q") {
  const [params] = useSearchParams();
  return params.get(key) || "";
}
