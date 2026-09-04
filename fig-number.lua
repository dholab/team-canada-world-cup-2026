-- Raise or colour the spans that scripts/fetch_prose.py emits, for LaTeX.
--
-- Pandoc calls a single Span handler, so BOTH span classes are handled here:
-- defining two `function Span` blocks in one filter silently replaces the first
-- with the second.
--
-- [.fig-number]  Quarto numbers Figures 1-4 and house-preamble.tex colours their
--                "Figure N." label terracotta via \captionsetup{labelfont=...}.
--                The supplementary figure is not Quarto-numbered: its label is
--                part of the caption text, so there is no label for LaTeX to
--                style, and this turns the span into \fignumber{...} instead.
--                HTML keeps the class and theme-house.scss colours it.
--
-- [.supmarker]   The equal-contribution marker ("&2") after the last two author
--                names. The affiliation digits use Unicode "¹"/"²", which both
--                formats raise on their own, but there is no superscript
--                ampersand to match. Raw "<sup>" rendered on the site while
--                LaTeX dropped the tags and printed a literal "&2" in the
--                preprint PDF, so it is a span and becomes
--                \textsuperscript{...} here.
local WRAPPERS = {
  ["fig-number"] = "\\fignumber{",
  ["supmarker"] = "\\textsuperscript{",
}

function Span(el)
  if not FORMAT:match("latex") then
    return nil
  end
  for class, open in pairs(WRAPPERS) do
    if el.classes:includes(class) then
      -- Build the replacement by inserting each inline in order. Using
      -- table.unpack inside a list constructor would keep only the first
      -- element, which silently truncated "Central Figure:" to "Central".
      local out = { pandoc.RawInline("latex", open) }
      for _, inline in ipairs(el.content) do
        table.insert(out, inline)
      end
      table.insert(out, pandoc.RawInline("latex", "}"))
      return out
    end
  end
end
