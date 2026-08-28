import { useCallback, useEffect, useRef, useState } from "react";

const PAGE = 50;

export function usePagedList(fetcher, extraDeps = []) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [sort, setSort] = useState({ campo: null, dir: 1 });
  const [source, setSource] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const offsetRef = useRef(0);
  const loadingMoreRef = useRef(false);

  useEffect(() => {
    const id = setTimeout(() => setQDebounced(q), 220);
    return () => clearTimeout(id);
  }, [q]);

  const query = useCallback(() => {
    const params = {
      q: qDebounced, offset: 0, limit: PAGE,
      source: source === "all" ? "" : source,
    };
    if (sort.campo) {
      params.sort = sort.campo;
      params.dir = sort.dir === 1 ? "asc" : "desc";
    }
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [qDebounced, sort, source, dateFrom, dateTo]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const params = query();
    fetcher(params).then((d) => {
      if (!alive) return;
      setItems(d.items || []);
      setTotal(d.total || 0);
      setHasMore(!!d.has_more);
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

  return {
    items, total, hasMore, loading, loadingMore, error,
    q, setQ, sort, toggleSort, source, setSource,
    dateFrom, setDateFrom, dateTo, setDateTo,
    loadMore, reload, query,
  };
}
