from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Literal
import re

@dataclass
class Span:
    start: int
    end: int

class Cursor:
    def __init__(self, start: int): self.i = start
    def advance(self, n: int) -> Tuple[int,int]:
        s = self.i; self.i += n; return s, self.i

ListPolicy = Literal["auto", "none"]  # "auto" = respeta listas; "none" = no crea viñetas

class MarkdownToDocs:
    """
    Markdown → requests nativos Docs (headings, párrafos con inline, listas, citas, hr, tablas y code).
    list_policy:
      - "auto": procesa -/*/1. como listas (por defecto)
      - "none": no crea bullets; y quita cualquier bullet 'heredado' del párrafo
    """
    def __init__(self, initial_index: int, list_policy: ListPolicy = "auto"):
        self.idx = Cursor(initial_index)
        self.requests: List[dict] = []
        self.list_policy = list_policy

    # ---------- primitivas ----------
    def _ins(self, text: str) -> Span:
        if not text: return Span(self.idx.i, self.idx.i)
        self.requests.append({"insertText": {"endOfSegmentLocation": {}, "text": text}})
        s,e = self.idx.advance(len(text))
        return Span(s,e)

    def _pstyle(self, span: Span, named: str):
        self.requests.append({
            "updateParagraphStyle":{
                "range":{"startIndex": span.start, "endIndex": span.end},
                "paragraphStyle":{"namedStyleType": named},
                "fields":"namedStyleType"
            }
        })

    def _tstyle(self, span: Span, **styles):
        fields = ",".join([k for k,v in styles.items() if v is not None])
        if not fields: return
        self.requests.append({
            "updateTextStyle":{
                "range":{"startIndex": span.start, "endIndex": span.end},
                "textStyle": styles,
                "fields": fields
            }
        })

    def _bullets(self, span: Span, ordered: bool):
        # preset válido y rango sin el \n final (evita bullets vacíos)
        preset = "NUMBERED_DECIMAL_ALPHA_ROMAN" if ordered else "BULLET_DISC_CIRCLE_SQUARE"
        end = max(span.start + 1, span.end - 1)
        self.requests.append({
            "createParagraphBullets":{
                "range":{"startIndex": span.start, "endIndex": end},
                "bulletPreset": preset
            }
        })

    def _strip_bullets_for(self, span: Span):
        """Quita bullets del rango recién insertado (para list_policy='none')."""
        end = max(span.start + 1, span.end)
        self.requests.append({
            "deleteParagraphBullets": {"range": {"startIndex": span.start, "endIndex": end}}
        })

    def _hr(self) -> Span:
        # separador visual + devolvemos el span para poder quitar bullets
        return self._ins("\n──────────\n")

    def _codeblock(self, code: str) -> Span:
        sp = self._ins(code + "\n")
        self._tstyle(
            sp,
            weightedFontFamily={"fontFamily":"Roboto Mono"},
            backgroundColor={"color":{"rgbColor":{"red":0.95,"green":0.95,"blue":0.95}}}
        )
        return sp

    def _table(self, rows: List[List[str]]) -> Span | None:
        if not rows: return None
        r = len(rows); c = max((len(x) for x in rows), default=0)
        if r == 0 or c == 0: return None
        self.requests.append({"insertTable":{"rows": r, "columns": c, "endOfSegmentLocation": {}}})
        return self._ins("\n")

    # ---------- inline ----------
    def _insert_plain_and_style(self, text: str, style: dict | None = None) -> Span:
        if not text: return Span(self.idx.i, self.idx.i)
        sp = self._ins(text)
        if style: self._tstyle(sp, **style)
        return sp

    def _insert_inline_md(self, md: str):
        i, n = 0, len(md)
        link_pat   = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        bold_pat   = re.compile(r"\*\*([^\*]+)\*\*")
        ital_pat   = re.compile(r"(?<!\*)\*([^\*]+)\*(?!\*)")
        code_pat   = re.compile(r"`([^`]+)`")
        strike_pat = re.compile(r"~~([^~]+)~~")
        while i < n:
            candidates = []
            for kind, pat in (("link", link_pat), ("bold", bold_pat), ("ital", ital_pat), ("code", code_pat), ("strike", strike_pat)):
                m = pat.search(md, i)
                if m: candidates.append((m.start(), kind, m))
            if not candidates:
                self._insert_plain_and_style(md[i:], None); break
            candidates.sort(key=lambda x: x[0])
            start, kind, m = candidates[0]
            if start > i: self._insert_plain_and_style(md[i:start], None)
            if kind == "link":
                txt, url = m.group(1), m.group(2)
                sp = self._ins(txt); self._tstyle(sp, link={"url": url})
            elif kind == "bold":
                self._insert_plain_and_style(m.group(1), {"bold": True})
            elif kind == "ital":
                self._insert_plain_and_style(m.group(1), {"italic": True})
            elif kind == "code":
                self._insert_plain_and_style(
                    m.group(1),
                    {"weightedFontFamily":{"fontFamily":"Roboto Mono"},
                     "backgroundColor":{"color":{"rgbColor":{"red":0.95,"green":0.95,"blue":0.95}}}}
                )
            elif kind == "strike":
                self._insert_plain_and_style(m.group(1), {"strikethrough": True})
            i = m.end()

    # ---------- render principal ----------
    def render(self, md: str) -> List[dict]:
        md = (md or "").replace("\r\n","\n").strip()
        lines = md.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # headings
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1)); text = m.group(2).strip()
                sp = self._ins(text + "\n"); self._pstyle(sp, f"HEADING_{level}")
                if self.list_policy == "none": self._strip_bullets_for(sp)
                i += 1; continue

            # hr
            if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line):
                sp = self._hr()
                if self.list_policy == "none": self._strip_bullets_for(sp)
                i += 1; continue

            # code block
            if line.strip().startswith("```"):
                i += 1; block=[]
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    block.append(lines[i]); i += 1
                sp = self._codeblock("\n".join(block))
                if self.list_policy == "none": self._strip_bullets_for(sp)
                i += 1; continue

            # listas (si list_policy == "auto")
            if self.list_policy == "auto" and (re.match(r"^\s*([-\*\+])\s+", line) or re.match(r"^\s*\d+\.\s+", line)):
                start_i = i
                while i < len(lines) and (re.match(r"^\s*([-\*\+])\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                    i += 1
                block = lines[start_i:i]
                item_spans=[]
                ordered = re.match(r"^\s*\d+\.\s+", block[0]) is not None
                for li in block:
                    txt = re.sub(r"^\s*([-\*\+])\s+", "", li)
                    txt = re.sub(r"^\s*\d+\.\s+", "", txt)
                    start_before = self.idx.i
                    self._insert_inline_md(txt)
                    sp_end = self._ins("\n")
                    item_spans.append(Span(start_before, sp_end.end))
                span_all = Span(item_spans[0].start, item_spans[-1].end)
                self._bullets(span_all, ordered=ordered)
                continue

            # blockquote
            if line.strip().startswith(">"):
                quote=[]
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quote.append(lines[i].lstrip(">").strip()); i += 1
                start_before = self.idx.i
                for q in quote:
                    self._insert_inline_md(q); sp_line = self._ins("\n")
                sp = Span(start_before, self.idx.i)
                self.requests.append({
                    "updateParagraphStyle":{
                        "range":{"startIndex": sp.start, "endIndex": sp.end},
                        "paragraphStyle":{"indentStart":{"magnitude":18.0,"unit":"PT"}},
                        "fields":"indentStart"
                    }
                })
                if self.list_policy == "none": self._strip_bullets_for(sp)
                continue

            # tabla markdown
            if re.match(r"^\|.*\|\s*$", line) and i+1 < len(lines) and re.match(r"^\|\s*[-:]+\s*\|", lines[i+1]):
                tbl=[line]; i += 1
                while i < len(lines) and re.match(r"^\|.*\|\s*$", lines[i]):
                    tbl.append(lines[i]); i += 1
                rows=[]
                for j,row in enumerate(tbl):
                    if j==1: continue
                    rows.append([c.strip() for c in row.strip().strip("|").split("|")])
                sp = self._table(rows)
                if sp and self.list_policy == "none": self._strip_bullets_for(sp)
                continue

            # línea vacía → salto
            if line.strip()=="":
                sp = self._ins("\n")
                if self.list_policy == "none": self._strip_bullets_for(sp)
                i += 1; continue

            # párrafo con inline
            self._insert_inline_md(line)
            sp = self._ins("\n")
            if self.list_policy == "none": self._strip_bullets_for(sp)
            i += 1

        return self.requests
