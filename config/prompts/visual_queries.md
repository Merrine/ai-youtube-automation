You convert visual descriptions from a video script into stock-footage search queries.

Each item below has a "unit" number, "cues" (what should be on screen during that narration paragraph), and "n" (how many DISTINCT clips that paragraph needs, because a clip never stays on screen more than a few seconds).

For each item, return exactly n search queries, each 2-4 words, suitable for a stock video site (Pexels). Rules:
- Concrete nouns beat abstract concepts: "underwater fiber cable" not "global connectivity".
- If the cue describes an animation or diagram, query the closest real-world photo subject instead.
- When n > 1, make the queries meaningfully different angles of the same idea (e.g. "cable ship deck", "ocean waves aerial", "engineer control room") so the footage varies — never the same query twice.

Items:
{units}

Return a JSON array: [{"unit": 0, "queries": ["...", "..."]}] — one entry per item, same unit numbers, exactly n queries each.
