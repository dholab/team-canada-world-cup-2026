-- Give the unnumbered figure labels the house accent in the PDF.
--
-- Quarto numbers Figures 1-3 and house-preamble.tex styles their "Figure N."
-- label terracotta via \captionsetup{labelfont=...}. The Central Figure and the
-- online supplemental figure are not Quarto-numbered: their label is part of
-- the caption text, so there is no label for LaTeX to style.
--
-- scripts/fetch_prose.py wraps those labels in a [.fig-number] span. HTML keeps
-- the class and the theme colours it; LaTeX silently drops span classes, so
-- this filter turns the span into \fignumber{...}, defined in the preamble.
function Span(el)
  if el.classes:includes("fig-number") and FORMAT:match("latex") then
    -- Build the replacement by inserting each inline in order. Using
    -- table.unpack inside a list constructor would keep only the first element,
    -- which silently truncated "Central Figure:" to "Central".
    local out = { pandoc.RawInline("latex", "\\fignumber{") }
    for _, inline in ipairs(el.content) do
      table.insert(out, inline)
    end
    table.insert(out, pandoc.RawInline("latex", "}"))
    return out
  end
end
