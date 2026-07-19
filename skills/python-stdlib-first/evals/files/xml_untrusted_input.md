# Eval note for untrusted XML

User will ask to parse untrusted third-party XML payloads.
Stdlib `xml.etree.ElementTree` is not a safe default for untrusted XML
(XXE / billion laughs class issues depending on parser). Prefer defusedxml
or an explicitly hardened parser path.
