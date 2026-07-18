"use client";

import { useState } from "react";

export function SearchBar({
  onSearch,
  disabled,
}: {
  onSearch: (query: string) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");

  return (
    <form
      className="mx-auto flex max-w-xl flex-col gap-2 sm:flex-row"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = query.trim();
        if (trimmed) onSearch(trimmed);
      }}
    >
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search products (e.g. Sony WH-1000XM5)"
        disabled={disabled}
        className="flex-1 rounded-lg border-2 border-border bg-surface px-4 py-3 text-text outline-none transition-colors placeholder:text-muted focus:border-accent disabled:opacity-60"
        autoComplete="off"
        autoFocus
      />
      <button
        type="submit"
        disabled={disabled || !query.trim()}
        className="rounded-lg bg-accent px-6 py-3 font-semibold text-black transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        Search
      </button>
    </form>
  );
}
