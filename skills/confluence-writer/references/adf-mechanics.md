# ADF Mechanics Reference

Read this file when you need to build or edit Confluence pages programmatically.
For simple pages, the HTML workflow below is almost always faster than raw ADF.

---

## The HTML-first workflow (recommended for most pages)

Rovo Dev uses an HTML format as the intermediate layer between content and ADF.
This is significantly faster than writing raw ADF JSON.

1. **Write content as HTML** using the documented patterns below.
2. **Save to a local `.html` file.**
3. **Create or update the page** using `create_confluence_page(content="/path/to/file.html")` or `update_confluence_page`.

For updates to existing pages:
1. `get_confluence_page(page_url=..., output_file="page.html")`. fetches the page as editable HTML
2. Edit the local `.html` file using `find_and_replace_code`, `open_files`, etc.
3. `update_confluence_page(page_url=..., content="page.html", version_message="...")`

---

## HTML component patterns

### Panels
```html
<div class="panel-info"><p>Info text</p></div>
<div class="panel-note"><p>Note text</p></div>
<div class="panel-warning"><p>Warning text</p></div>
<div class="panel-success"><p>Success text</p></div>
<div class="panel-error"><p>Error text</p></div>
<div class="panel-custom" data-icon=":emoji:" data-color="#hex"><p>text</p></div>
```

### Status lozenges
```html
<span class="status" data-color="green">GA</span>
<span class="status" data-color="blue">In Progress</span>
<span class="status" data-color="yellow">At Risk</span>
<span class="status" data-color="red">Blocked</span>
<span class="status" data-color="neutral">Label</span>
```

### Layout sections
```html
<section class="layout-two-equal">
  <div class="column"><p>Left content</p></div>
  <div class="column"><p>Right content</p></div>
</section>
```
Available layout classes: `layout-two-equal`, `layout-two-left-sidebar`, `layout-two-right-sidebar`, `layout-three-equal`, `layout-three-with-sidebars`

### Tables
```html
<table>
  <thead><tr><th>Header</th><th>Header</th></tr></thead>
  <tbody><tr><td>Cell</td><td>Cell</td></tr></tbody>
</table>
```

### Expands
```html
<!-- Top-level expand -->
<details><summary>Expand title</summary><p>Content</p></details>
```

### Task lists
```html
<ul class="task-list">
  <li class="task-item"><input type="checkbox"> Todo item</li>
  <li class="task-item"><input type="checkbox" checked> Done item</li>
</ul>
```

### Inline elements
```html
<span class="emoji" data-shortname=":rocket:">🚀</span>
<time datetime="2025-03-15">March 15, 2025</time>
<a href="URL" data-card-appearance="inline">Smart link</a>
<div class="block-card" data-url="URL"><a href="URL">Block card</a></div>
```

### Mermaid diagrams
```html
<pre><code class="language-mermaid">flowchart LR
    A[Start] --> B{Decision}
    B -- Yes --> C[Action]
    B -- No --> D[End]
</code></pre>
```

---

## Building ADF programmatically (advanced)

For complex pages. review tables with many rows, dashboards, packing slips ...
write a Python script that generates the ADF JSON directly. More reliable than
hand-editing large HTML files when the structure is highly repetitive.

**Core node patterns:**

```python
# Text with marks
{"type": "text", "text": "Bold text", "marks": [{"type": "strong"}]}

# Paragraph (attrs: {} required)
{"type": "paragraph", "attrs": {}, "content": [text_nodes]}

# Heading
{"type": "heading", "attrs": {"level": 2}, "content": [text_nodes]}

# Status lozenge
{"type": "status", "attrs": {"text": "GA", "color": "green", "style": "bold"}}

# Panel
{"type": "panel", "attrs": {"panelType": "note"}, "content": [block_nodes]}

# Layout section
{"type": "layoutSection", "attrs": {}, "content": [
    {"type": "layoutColumn", "attrs": {"width": 50}, "content": [block_nodes]},
    {"type": "layoutColumn", "attrs": {"width": 50}, "content": [block_nodes]}
]}

# Inline card (smart link)
{"type": "inlineCard", "attrs": {"url": "https://..."}}

# nestedExpand (inside table cells only; never use expand inside cells)
{"type": "nestedExpand", "attrs": {"title": "Details"}, "content": [block_nodes]}

# expand (top level only)
{"type": "expand", "attrs": {"title": "More info"}, "content": [block_nodes]}

# Date
{"type": "date", "attrs": {"timestamp": "1743033600000"}}

# Emoji
{"type": "emoji", "attrs": {"shortName": ":white_check_mark:", "text": ":white_check_mark:"}}

# Table with numbered rows and full width
{"type": "table", "attrs": {
    "displayMode": "default",
    "isNumberColumnEnabled": True,
    "layout": "center",
    "width": 1800
}, "content": [table_rows]}

# Table header cell with explicit colwidth (always set this)
{"type": "tableHeader", "attrs": {"colspan": 1, "rowspan": 1, "colwidth": [316]}, "content": [block_nodes]}

# Table cell with explicit colwidth
{"type": "tableCell", "attrs": {"colspan": 1, "rowspan": 1, "colwidth": [200]}, "content": [block_nodes]}

# Document root (version: 1 required)
{"type": "doc", "version": 1, "content": [...]}
```

**Common mistakes:**
- Missing `attrs: {}` on paragraphs. API will reject them
- Forgetting `colwidth` on table cells. columns auto-size unpredictably
- Using `expand` inside table cells. use `nestedExpand` instead
- Putting block nodes inside inline contexts (or vice versa)
- Omitting `version: 1` on the doc root
