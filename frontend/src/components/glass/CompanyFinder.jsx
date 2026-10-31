import React, { useId, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { COMPANIES } from "../../data/companies";
import { TID } from "../../testIds";

/**
 * Accessible company search combobox (glass restyle, 2026-10).
 *
 * role="combobox" + a role="listbox" popup, arrow-key navigation, Enter to
 * commit, Escape to close. A live (verified) company commits by navigating
 * to /company/:id. A non-live company ("Microsoft SWE") is shown in the
 * list but disabled, labelled "Rolling out next", and never navigates --
 * same convention as ChooseCompanySection.jsx's tile grid. No-match state
 * shows a plain "No company matches ..." row instead of an empty popup.
 *
 * `onPreview(company | null)` fires on highlight (hover/arrow move) so a
 * caller (the hero) can live-restyle itself as the visitor browses, before
 * any selection is committed -- selection/commit is a separate, explicit
 * step (Enter or click), never a side effect of typing or highlighting.
 */
export default function CompanyFinder({
  placeholder = "Which company are you preparing for?",
  onPreview,
  onCommit,
  className = "",
  inputClassName = "",
  autoFocus = false,
}) {
  const navigate = useNavigate();
  const inputId = useId();
  const listboxId = useId();
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef(null);

  const matches = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return COMPANIES;
    return COMPANIES.filter((c) => c.name.toLowerCase().includes(q));
  }, [value]);

  function closeList() {
    setOpen(false);
    setActiveIndex(-1);
  }

  function commit(company) {
    if (!company || !company.live) return;
    setValue("");
    closeList();
    onCommit?.(company);
    navigate(`/company/${company.id}`);
  }

  function highlight(index) {
    setActiveIndex(index);
    const c = matches[index];
    onPreview?.(c && c.live ? c : c || null);
  }

  function onKeyDown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) { setOpen(true); return; }
      highlight(Math.min(activeIndex + 1, matches.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) { setOpen(true); return; }
      highlight(Math.max(activeIndex - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (open && activeIndex >= 0 && matches[activeIndex]) {
        commit(matches[activeIndex]);
      }
    } else if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        closeList();
      } else {
        setValue("");
      }
    }
  }

  const activeOption = activeIndex >= 0 ? matches[activeIndex] : null;

  return (
    <div className={`gl-finder ${className}`}>
      <input
        ref={inputRef}
        id={inputId}
        data-testid={TID.companySearchInput}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeOption ? `${listboxId}-${activeOption.id}` : undefined}
        className={`gl-srch ${inputClassName}`}
        placeholder={placeholder}
        value={value}
        autoFocus={autoFocus}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setValue(e.target.value);
          setOpen(true);
          setActiveIndex(-1);
          onPreview?.(null);
        }}
        onKeyDown={onKeyDown}
        onBlur={() => {
          // Let a click on an option register before closing.
          window.setTimeout(() => closeList(), 120);
        }}
        aria-label="Search company"
      />
      {open && (
        <ul
          id={listboxId}
          data-testid={TID.companySearchListbox}
          role="listbox"
          className="gl-finder-list"
          aria-label="Companies"
        >
          {matches.length === 0 && (
            <li className="gl-finder-empty" role="presentation">
              No company matches &ldquo;{value}&rdquo;.
            </li>
          )}
          {matches.map((c, i) => {
            const active = i === activeIndex;
            return (
              <li
                key={c.id}
                id={`${listboxId}-${c.id}`}
                data-testid={TID.companySearchOption(c.id)}
                role="option"
                aria-selected={active}
                aria-disabled={!c.live}
                className={`gl-finder-opt${active ? " on" : ""}${!c.live ? " off" : ""}`}
                onMouseEnter={() => highlight(i)}
                onMouseDown={(e) => {
                  // mousedown (not click) fires before the input's onBlur.
                  e.preventDefault();
                  if (c.live) commit(c);
                }}
              >
                <span>{c.name}</span>
                {!c.live && <em>Rolling out next</em>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
