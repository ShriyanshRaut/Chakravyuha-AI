# Intelligence Report — Synthetic Demonstration Data Only

**Documents analysed:** 15  
**Entities resolved:** 90 (11 persons, 4 organisations)  
**Relationships extracted:** 120  
**Value traced across transfers:** Rs. 8,215,000

## Key individuals

**Vikram Singh — principal influencer.** Highest PageRank (0.1253) across the resolved network, with 6 direct connections. Influence is indirect: multiple crew members route contact toward this individual rather than to each other.

**Imran Sheikh — bridging intermediary.** Highest betweenness (0.5275), meaning this individual lies on the shortest path between two otherwise separate clusters. Removing this node disconnects the operational group from the financial channel.

## Detected groupings

- **Cluster 1** (6 members): Salkia gang, Bablu Mondal, Kallu Halder, Pappu Das, Sohail Ansari, Vikram Singh
- **Cluster 2** (4 members): Hind Logistics, Sunrise Exports, Amit Agarwal, Imran Sheikh

## Suspicious activity

8 patterns flagged, 3 at high severity.

- **[HIGH] Funds pass-through: Imran Sheikh** — Rs. 290,000 received and Rs. 300,000 forwarded within 3 days, retaining under 15%. Consistent with a layering conduit.
- **[HIGH] Possible structuring: Amit Agarwal to Hind Logistics** — 3 transfers totalling Rs. 1,470,000 within 7 days, each between Rs. 425,000 and the Rs. 500,000 reporting threshold.
- **[HIGH] Single point of connection: Imran Sheikh** — Betweenness centrality 0.5275 — the highest in the network. This individual sits on the shortest path between two otherwise unconnected groups; removing them disconnects the network.
- **[MEDIUM] Call burst: Vikram Singh and Rakesh Yadav** — 6 calls within 60 minutes on 14/01/2026, first at 21:35 near Bowbazar. Short-interval clustering is consistent with coordination around an event.
- **[MEDIUM] Shared identifier: 9007654321** — PHONE 9007654321 is linked to 2 individuals across sources. Shared handsets, accounts or vehicles frequently indicate an operational pool.
- **[LOW] Predominantly night-time contact: Sohail Ansari and Vikram Singh** — 6 of 6 calls fall between 22:00 and 05:00.
- **[LOW] Predominantly night-time contact: Vikram Singh and Kallu Halder** — 8 of 8 calls fall between 22:00 and 05:00.
- **[LOW] Predominantly night-time contact: Vikram Singh and Pappu Das** — 11 of 11 calls fall between 22:00 and 05:00.

## Sequence

23 dated events between 2026-01-15 and 2026-03-18. Full stream in `timeline.json`.

## Basis

Every relationship above is traceable to a sentence in a source FIR; evidence text is attached to each edge in the graph payload. Entity merges below the automatic threshold were referred for officer approval and are recorded in the review log.

_Synthetic Demonstration Data Only._