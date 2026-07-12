import Link from "next/link";

function buildHref(basePath: string, params: Record<string, string | undefined>, page: number) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  if (page > 1) search.set("page", String(page));
  const qs = search.toString();
  return qs ? `${basePath}?${qs}` : basePath;
}

export default function Pagination({
  basePath,
  page,
  totalPages,
  extraParams = {},
}: {
  basePath: string;
  page: number;
  totalPages: number;
  extraParams?: Record<string, string | undefined>;
}) {
  if (totalPages <= 1) return null;

  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  return (
    <div className="pagination">
      {hasPrev ? (
        <Link href={buildHref(basePath, extraParams, page - 1)}>Previous</Link>
      ) : (
        <span className="disabled">Previous</span>
      )}
      <span>
        Page {page} of {totalPages}
      </span>
      {hasNext ? (
        <Link href={buildHref(basePath, extraParams, page + 1)}>Next</Link>
      ) : (
        <span className="disabled">Next</span>
      )}
    </div>
  );
}
