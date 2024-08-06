Problem:

I want RFC7217 in "new HTML" form. The document is only available as TXT. So convert to XML (with `id2xml`) and then to HTML (with `xml2rfc --html`).

`id2xml` cannot parse all text references. Therefore it produces invalid XML not accepted by `xml2rfc`.

```
[BROERSMA] Broersma, R., "IPv6 Everywhere: Living with a Fully
              IPv6-enabled environment", Australian IPv6 Summit 2010,
              Melbourne, VIC Australia, October 2010,
              <http://www.ipv6.org.au/10ipv6summit/talks/
              Ron_Broersma.pdf>.

Failed parsing a reference.  Are all elements
   separated by commas (not periods, not just spaces)?:
```

**This branch** is a minimal adjustments hack to at least generate valid XML.

Now this works:
`curl -O https://www.rfc-editor.org/rfc/rfc7217.txt`

`python3 id2xml/run.py --doc-ipr trust200902 rfc7217.txt` (where `python3 id2xml/run.py` == `id2xml`)

(`--doc-ipr trust200902` is because otherwise xml2rfc complains about missing ipr attribute.)

`xml2rfc rfc7217.xml --html`

`xdg-open rfc7217.html`