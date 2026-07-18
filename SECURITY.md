# Security

## Model

acikpoz is a local, offline tool: it makes no network calls and has no code path
that writes to your data. It reads a PDF you point it at and emits structured
records — nothing more. The attack surface that remains:

- **It parses PDFs you provide.** A malformed, encrypted or hostile PDF is a
  parsing-robustness concern, not a code-execution one: acikpoz never executes
  anything from the file, and it wraps pdfplumber/pdfminer errors into a single
  clear failure (`ValueError`) rather than crashing. Keep the parsing
  dependencies (`pdfplumber`, `pdfminer.six`) current.
- **The MCP server reads the `pdf_path` an agent gives it,** and only reads it —
  it parses that file and returns records. Point it at data you control, and run
  it where you would run any local file tool.

A parsed price is only ever a finite number the catalog printed in the price
column; the parser never coerces text, borrows a neighbour's figure, invents a
price, or returns `inf`/`nan`.

## Reporting

Report vulnerabilities through GitHub's private security advisories on this
repository (Security → Report a vulnerability). I'll acknowledge within a few days.
