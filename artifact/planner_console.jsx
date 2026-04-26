import React, { useState, useEffect, useMemo } from "react";
import {
  Activity,
  ListChecks,
  ScrollText,
  CircleCheck,
  CircleAlert,
  ArrowUpRight,
  ArrowUp,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Check,
  RotateCcw,
} from "lucide-react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  YAxis,
  Tooltip,
} from "recharts";

// ---------------------------------------------------------------------------
// Sample dataset — embedded so the artifact renders without any upload.
// ---------------------------------------------------------------------------
const sampleForecasts = [
  {
    item_id: "HOBBIES_1_002",
    store_id: "CA_1",
    category: "HOBBIES",
    point_forecast: 119,
    lower_bound: 93,
    upper_bound: 145,
    confidence_score: 0.51,
    recent_sales: [
      121, 121, 133, 127, 123, 134, 107, 113, 110, 115, 105, 125, 117, 104,
      109, 122, 127, 139, 148, 123, 109, 98, 122, 111, 115, 113, 118, 130,
    ],
    prior_forecast: 136,
    is_exception: true,
    exception_reasons: ["Low confidence (0.51)"],
    planner_memo:
      "HOBBIES_1_002 in HOBBIES needs planner review. The item is flagged for low confidence (0.51). Investigate whether recent data is sparse or missing.",
  },
  {
    item_id: "HOUSEHOLD_1_002",
    store_id: "CA_1",
    category: "HOUSEHOLD",
    point_forecast: 32,
    lower_bound: 25,
    upper_bound: 39,
    confidence_score: 0.48,
    recent_sales: [
      31, 32, 37, 32, 35, 31, 28, 29, 30, 38, 30, 35, 29, 35, 33, 32, 32, 30,
      33, 31, 28, 28, 33, 37, 32, 32, 33, 36,
    ],
    prior_forecast: 35,
    is_exception: true,
    exception_reasons: ["Low confidence (0.48)"],
    planner_memo:
      "HOUSEHOLD_1_002 in HOUSEHOLD needs planner review. The item is flagged for low confidence (0.48). Investigate whether recent data is sparse or missing.",
  },
  {
    item_id: "HOUSEHOLD_1_005",
    store_id: "CA_1",
    category: "HOUSEHOLD",
    point_forecast: 53,
    lower_bound: 44,
    upper_bound: 62,
    confidence_score: 0.69,
    recent_sales: [
      68, 76, 44, 50, 56, 67, 45, 51, 59, 56, 50, 52, 42, 51, 51, 55, 49, 57,
      61, 54, 56, 53, 53, 47, 56, 52, 70, 66,
    ],
    prior_forecast: 32,
    is_exception: true,
    exception_reasons: ["Forecast changed 66% from prior week"],
    planner_memo:
      "HOUSEHOLD_1_005 in HOUSEHOLD needs planner review. The item is flagged for forecast changed 66% from prior week. Investigate whether recent promotions, price changes, or seasonality shifts are affecting demand.",
  },
  {
    item_id: "FOODS_1_002",
    store_id: "CA_1",
    category: "FOODS",
    point_forecast: 190,
    lower_bound: 151,
    upper_bound: 229,
    confidence_score: 0.57,
    recent_sales: [
      218, 201, 232, 201, 210, 183, 192, 173, 214, 162, 209, 185, 218, 208,
      234, 208, 152, 188, 162, 178, 226, 205, 173, 166, 191, 161, 174, 197,
    ],
    prior_forecast: 194,
    is_exception: true,
    exception_reasons: ["Low confidence (0.57)"],
    planner_memo:
      "FOODS_1_002 in FOODS needs planner review. The item is flagged for low confidence (0.57). Investigate whether recent data is sparse or missing.",
  },
  {
    item_id: "HOUSEHOLD_1_006",
    store_id: "CA_1",
    category: "HOUSEHOLD",
    point_forecast: 198,
    lower_bound: 172,
    upper_bound: 224,
    confidence_score: 0.86,
    recent_sales: [
      217, 277, 191, 130, 253, 182, 202, 243, 144, 155, 144, 171, 213, 216,
      207, 150, 119, 200, 182, 214, 222, 203, 224, 206, 216, 174, 192, 205,
    ],
    prior_forecast: 138,
    is_exception: true,
    exception_reasons: ["Forecast changed 43% from prior week"],
    planner_memo:
      "HOUSEHOLD_1_006 in HOUSEHOLD needs planner review. The item is flagged for forecast changed 43% from prior week. Investigate whether recent promotions, price changes, or seasonality shifts are affecting demand.",
  },
];

// ---------------------------------------------------------------------------
// Constants & helpers
// ---------------------------------------------------------------------------
const ACTION_META = {
  Accept: { tone: "emerald", icon: CircleCheck, verb: "Accepted" },
  Override: { tone: "amber", icon: CircleAlert, verb: "Overridden" },
  Escalate: { tone: "rose", icon: ArrowUp, verb: "Escalated" },
};

const TONE = {
  emerald: {
    pill: "bg-emerald-50 text-emerald-700 border-emerald-200",
    btn: "bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white border-emerald-700",
    dot: "bg-emerald-500",
  },
  amber: {
    pill: "bg-amber-50 text-amber-800 border-amber-200",
    btn: "bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white border-amber-700",
    dot: "bg-amber-500",
  },
  rose: {
    pill: "bg-rose-50 text-rose-700 border-rose-200",
    btn: "bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white border-rose-700",
    dot: "bg-rose-500",
  },
  stone: {
    pill: "bg-stone-100 text-stone-700 border-stone-200",
    btn: "bg-stone-900 hover:bg-stone-800 text-white border-stone-900",
    dot: "bg-stone-500",
  },
};

const DEBRIEF_STOPWORDS = new Set(["this","that","with","from","have","been","because","about","would","could","should","there","their","than","then","when","what","which","were","they","need","needs"]);
const THEME_PRIORITY = ["promo", "promotion", "sale", "stockout", "stock"];

function fmtTimestamp(iso) {
  try {
    const d = new Date(iso);
    const date = d.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `${date} · ${time}`;
  } catch {
    return iso;
  }
}

function pctDelta(a, b) {
  if (!b) return 0;
  return ((a - b) / b) * 100;
}

function confidenceTone(c) {
  if (c >= 0.8) return "emerald";
  if (c >= 0.65) return "amber";
  return "rose";
}

function parseOverrideNumber(reason) {
  const match = reason.match(/\b(\d{1,4})\b/);
  return match ? Number(match[1]) : null;
}

function computeThemes(log) {
  const reasons = log
    .filter((entry) => entry.action === "Override" || entry.action === "Escalate")
    .map((entry) => entry.reason.trim())
    .filter(Boolean);
  if (reasons.length < 3) return { reasons, themes: [] };
  const counts = {};
  const seenAt = {};
  reasons.forEach((reason) => {
    reason
      .toLowerCase()
      .split(/\s+/)
      .forEach((token) => {
        const clean = token.replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, "");
        if (clean.length < 4 || DEBRIEF_STOPWORDS.has(clean)) return;
        if (seenAt[clean] === undefined) seenAt[clean] = Object.keys(seenAt).length;
        counts[clean] = (counts[clean] || 0) + 1;
      });
  });
  const themes = Object.entries(counts)
    .sort((a, b) => {
      const prioA = THEME_PRIORITY.includes(a[0]) ? 0 : 1;
      const prioB = THEME_PRIORITY.includes(b[0]) ? 0 : 1;
      return b[1] - a[1] || prioA - prioB || seenAt[a[0]] - seenAt[b[0]];
    })
    .slice(0, 5)
    .map(([token, count]) => ({ token, count }));
  return { reasons, themes };
}

function generateRecommendation(summary, topTheme) {
  const accepts = summary.actions.Accept.count;
  const acceptRate = summary.total ? accepts / summary.total : 0;
  const escalatedItems = summary.actions.Escalate.items.map((item) => item.item_id);
  let recommendation = "review whether current exception thresholds are surfacing the right cases";
  const questions = [];
  let escalationNote = "";

  if (summary.overrideCluster) {
    recommendation = `review feature coverage for ${summary.overrideCluster} forecasts`;
    questions.push(`What features are missing or underweighted for ${summary.overrideCluster} items?`);
  }
  if (topTheme === "promo" || topTheme === "promotion" || topTheme === "sale") {
    if (!summary.overrideCluster) recommendation = "review whether promotional signals are represented in the model";
    questions.push("How are promotions or sale events represented in the model inputs and training data?");
  } else if (topTheme === "stockout" || topTheme === "stock") {
    if (!summary.overrideCluster) recommendation = "review data quality for inventory-affected items";
    questions.push("How are stockouts and inventory anomalies filtered or encoded before forecasting?");
  } else if (!summary.overrideCluster && summary.actions.Escalate.count > 0) {
    recommendation = "schedule a focused follow-up on the escalated cases";
  } else if (!summary.overrideCluster && acceptRate >= 0.8) {
    recommendation = "consider loosening exception thresholds because planner agreement was high";
    questions.push("Are current thresholds surfacing too many low-value exception reviews?");
  } else if (!summary.overrideCluster) {
    questions.push("Which exception rule is producing the least useful planner reviews?");
  }

  if (summary.actions.Escalate.count > 0) {
    escalationNote = ` Also review escalated item(s) ${escalatedItems.join(", ")} with the supply lead.`;
  }

  const finalQuestions = questions.slice(0, 2).join(" ");
  return `Based on this session, the most useful next step is to ${recommendation}. Specifically: ${finalQuestions || "What changed between accepted and non-accepted cases, and should thresholds move next session?"}${escalationNote}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function QueueRow({ item, selected, onSelect }) {
  return (
    <button
      onClick={() => onSelect(item.item_id)}
      className={[
        "w-full text-left px-4 py-3.5 border-b border-stone-100 transition relative block",
        selected ? "bg-stone-900 text-white" : "bg-white hover:bg-stone-50",
      ].join(" ")}
    >
      {selected && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-400" />
      )}
      <div className="flex items-center justify-between mb-1.5">
        <span
          className={`pmono text-[10px] tracking-tight uppercase ${
            selected ? "text-stone-400" : "text-stone-500"
          }`}
        >
          {item.category} · {item.store_id}
        </span>
        <div
          className={`flex items-center gap-1 text-[10px] ${
            selected ? "text-amber-300" : "text-amber-600"
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          <span className="uppercase tracking-wider">Exception</span>
        </div>
      </div>
      <div
        className={`pmono text-sm font-medium ${
          selected ? "text-white" : "text-stone-900"
        }`}
      >
        {item.item_id}
      </div>
      <div
        className={`text-[12px] mt-1.5 leading-snug ${
          selected ? "text-stone-300" : "text-stone-600"
        }`}
      >
        {item.exception_reasons.join(" · ")}
      </div>
    </button>
  );
}

function ConfidenceBand({ low, point, high }) {
  // Add 30% padding on each side of the band for visual breathing room
  const pad = (high - low) * 0.3;
  const min = Math.floor(low - pad);
  const max = Math.ceil(high + pad);
  const span = max - min || 1;
  const lowPct = ((low - min) / span) * 100;
  const highPct = ((high - min) / span) * 100;
  const pointPct = ((point - min) / span) * 100;
  return (
    <div>
      <div className="relative h-10 mt-2">
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-px bg-stone-200" />
        <div
          className="absolute top-1/2 -translate-y-1/2 h-3 bg-stone-200/70 border-y border-stone-300"
          style={{ left: `${lowPct}%`, width: `${highPct - lowPct}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-5 bg-stone-700"
          style={{ left: `${lowPct}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-px h-5 bg-stone-700"
          style={{ left: `${highPct}%` }}
        />
        <div
          className="absolute top-1/2 z-10"
          style={{ left: `${pointPct}%`, transform: "translate(-50%, -50%)" }}
        >
          <div className="w-3.5 h-3.5 rounded-full bg-stone-900 ring-[3px] ring-white shadow" />
        </div>
      </div>
      <div className="relative h-5 pmono text-[11px] text-stone-500">
        <span
          className="absolute"
          style={{ left: `${lowPct}%`, transform: "translateX(-50%)" }}
        >
          {low}
        </span>
        <span
          className="absolute font-semibold text-stone-900"
          style={{ left: `${pointPct}%`, transform: "translateX(-50%)" }}
        >
          {point}
        </span>
        <span
          className="absolute"
          style={{ left: `${highPct}%`, transform: "translateX(-50%)" }}
        >
          {high}
        </span>
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-white border border-stone-200 px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500">
        {label}
      </div>
      <div className="pmono text-[26px] leading-none mt-2 text-stone-900">
        {value}
      </div>
      {sub && <div className="text-[11px] text-stone-500 mt-1.5">{sub}</div>}
    </div>
  );
}

function ConfidenceMeter({ score }) {
  const tone = confidenceTone(score);
  return (
    <div className="bg-white border border-stone-200 px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500">
        Confidence
      </div>
      <div className="pmono text-[26px] leading-none text-stone-900 mt-2">
        {score.toFixed(2)}
      </div>
      <div className="mt-3 h-1.5 bg-stone-100 overflow-hidden">
        <div
          className={`h-full ${TONE[tone].dot}`}
          style={{ width: `${Math.max(score * 100, 4)}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-stone-400 pmono mt-1">
        <span>0.00</span>
        <span>1.00</span>
      </div>
    </div>
  );
}

function PriorDeltaCard({ current, prior }) {
  const delta = pctDelta(current, prior);
  const dir = delta > 1 ? "up" : delta < -1 ? "down" : "flat";
  const Icon = dir === "up" ? TrendingUp : dir === "down" ? TrendingDown : Minus;
  const heavy = Math.abs(delta) > 25;
  return (
    <div className="bg-white border border-stone-200 px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500">
        Prior Forecast
      </div>
      <div className="pmono text-[26px] leading-none text-stone-900 mt-2">
        {prior}
      </div>
      <div
        className={`flex items-center gap-1 text-[11px] mt-1.5 ${
          heavy ? "text-amber-700" : "text-stone-500"
        }`}
      >
        <Icon className="w-3 h-3" />
        <span className="pmono">
          {delta > 0 ? "+" : ""}
          {delta.toFixed(0)}%
        </span>
        <span>vs current</span>
      </div>
    </div>
  );
}

function Sparkline({ data }) {
  const series = data.map((v, i) => ({ day: i + 1, sales: v }));
  const min = Math.min(...data);
  const max = Math.max(...data);
  const avg = data.reduce((a, b) => a + b, 0) / data.length;
  const span = max - min || 1;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <div className="text-[11px] uppercase tracking-[0.15em] pmono text-stone-500">
          Recent Sales · 28 days
        </div>
        <div className="pmono text-[11px] text-stone-500">
          avg <span className="text-stone-900">{avg.toFixed(0)}</span> · min{" "}
          {min} · max {max}
        </div>
      </div>
      <div className="h-24 bg-stone-50 border border-stone-200 px-2 py-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={series}
            margin={{ top: 4, bottom: 4, left: 0, right: 0 }}
          >
            <YAxis hide domain={[min - span * 0.2, max + span * 0.2]} />
            <Tooltip
              cursor={{ stroke: "#a8a29e", strokeWidth: 1, strokeDasharray: "2 2" }}
              contentStyle={{
                background: "#0c0a09",
                border: "none",
                borderRadius: 0,
                color: "#fafaf9",
                fontSize: 11,
                fontFamily: "'IBM Plex Mono', monospace",
                padding: "4px 8px",
              }}
              formatter={(v) => [`${v} units`, ""]}
              labelFormatter={(l) => `Day ${l}`}
              itemStyle={{ color: "#fafaf9" }}
            />
            <Line
              type="monotone"
              dataKey="sales"
              stroke="#0c0a09"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function StatusBadge({ decision }) {
  const meta = ACTION_META[decision.action];
  if (!meta) return null;
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium border ${
        TONE[meta.tone].pill
      }`}
    >
      <Icon className="w-3 h-3" />
      {meta.verb}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Views
// ---------------------------------------------------------------------------
function ReviewQueueView({
  queue,
  selected,
  decisions,
  onSelect,
  reason,
  setReason,
  overrideOk,
  commit,
  savingAction,
  totalItems,
  decidedCount,
  onReset,
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] min-h-[calc(100vh-3.5rem)]">
      {/* Left queue panel */}
      <aside className="bg-white border-r border-stone-200 flex flex-col">
        <div className="px-4 py-3 border-b border-stone-200 flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-stone-500 pmono">
              Exception Queue
            </div>
            <div className="text-sm font-semibold mt-0.5">
              {queue.length === 0
                ? "All clear"
                : `${queue.length} item${queue.length === 1 ? "" : "s"} remaining`}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] pmono text-stone-500 uppercase tracking-wider">
              Progress
            </div>
            <div className="pmono text-sm">
              {decidedCount}/{totalItems}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {queue.length === 0 ? (
            <div className="p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-emerald-50 border border-emerald-200 grid place-items-center">
                <Check className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="text-sm font-medium text-stone-900">
                All exception items reviewed
              </div>
              <div className="text-xs text-stone-500 mt-1">
                Open the audit log to review your decisions.
              </div>
            </div>
          ) : (
            queue.map((item) => (
              <QueueRow
                key={item.item_id}
                item={item}
                selected={selected?.item_id === item.item_id}
                onSelect={onSelect}
              />
            ))
          )}
        </div>

        <div className="px-4 py-2.5 border-t border-stone-200 flex items-center justify-between">
          <span className="text-[10px] pmono text-stone-500 uppercase tracking-wider">
            Source · sample dataset
          </span>
          <button
            onClick={onReset}
            className="text-[10px] pmono text-stone-500 hover:text-stone-900 uppercase tracking-wider flex items-center gap-1 transition"
            title="Clear all saved decisions and reload the queue"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        </div>
      </aside>

      {/* Right detail panel */}
      <main className="overflow-y-auto">
        {selected ? (
          <DetailPanel
            item={selected}
            decision={decisions[selected.item_id]}
            reason={reason}
            setReason={setReason}
            overrideOk={overrideOk}
            commit={commit}
            savingAction={savingAction}
          />
        ) : (
          <CompletionPanel
            decidedCount={decidedCount}
            totalItems={totalItems}
          />
        )}
      </main>
    </div>
  );
}

function DetailPanel({
  item,
  decision,
  reason,
  setReason,
  overrideOk,
  commit,
  savingAction,
}) {
  return (
    <div className="max-w-[1100px] mx-auto px-8 py-7">
      {/* Item header */}
      <div className="flex items-start justify-between gap-6 pb-5 border-b border-stone-200">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] uppercase tracking-[0.18em] pmono text-stone-500">
              Exception ID
            </span>
            {decision && <StatusBadge decision={decision} />}
          </div>
          <h1 className="pmono text-2xl font-medium text-stone-900 truncate">
            {item.item_id}
          </h1>
          <div className="flex items-center gap-3 mt-2 text-[12px]">
            <span className="px-2 py-0.5 bg-stone-100 border border-stone-200 pmono text-stone-700 uppercase tracking-wider">
              {item.category}
            </span>
            <span className="text-stone-500 pmono">Store {item.store_id}</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1.5 shrink-0">
          <AlertTriangle className="w-3.5 h-3.5" />
          Flagged for review
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
        <MetricCard
          label="Point Forecast"
          value={item.point_forecast}
          sub="units · next week"
        />
        <PriorDeltaCard
          current={item.point_forecast}
          prior={item.prior_forecast}
        />
        <ConfidenceMeter score={item.confidence_score} />
        <MetricCard
          label="Range (Low–High)"
          value={`${item.lower_bound}–${item.upper_bound}`}
          sub={`±${item.upper_bound - item.lower_bound} band`}
        />
      </div>

      {/* Confidence band visualization */}
      <section className="mt-7">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] uppercase tracking-[0.15em] pmono text-stone-500">
            Forecast Confidence Range
          </h3>
          <span className="text-[11px] text-stone-500 pmono">
            {item.lower_bound}–{item.upper_bound} (point: {item.point_forecast})
          </span>
        </div>
        <div className="bg-white border border-stone-200 px-5 py-4">
          <ConfidenceBand
            low={item.lower_bound}
            point={item.point_forecast}
            high={item.upper_bound}
          />
        </div>
      </section>

      {/* Sparkline */}
      <section className="mt-6">
        <Sparkline data={item.recent_sales} />
      </section>

      {/* Reasons + Memo */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        <section>
          <h3 className="text-[11px] uppercase tracking-[0.15em] pmono text-stone-500 mb-2">
            Exception Reasons
          </h3>
          <div className="bg-white border border-stone-200 px-4 py-3">
            <ul className="space-y-1.5">
              {item.exception_reasons.map((r, i) => (
                <li key={i} className="flex gap-2.5 text-sm items-start">
                  <span className="mt-2 w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                  <span className="text-stone-800">{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section>
          <h3 className="text-[11px] uppercase tracking-[0.15em] pmono text-stone-500 mb-2">
            Planner Memo
          </h3>
          <div className="bg-amber-50/60 border-l-4 border-amber-400 border-y border-r border-stone-200 px-4 py-3 text-[13px] leading-relaxed text-stone-800">
            {item.planner_memo}
          </div>
        </section>
      </div>

      {/* Decision controls */}
      <section className="mt-7 pt-6 border-t border-stone-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] uppercase tracking-[0.15em] pmono text-stone-500">
            Decision
          </h3>
          <span className="text-[11px] text-stone-500">
            Override requires reason ≥ 10 chars · Escalate optional · Accept ignores
          </span>
        </div>

        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          placeholder="Reason for override or escalation (optional for Escalate, required ≥10 chars for Override)…"
          className="w-full bg-white border border-stone-300 focus:border-stone-900 focus:ring-0 outline-none px-4 py-3 text-sm leading-relaxed resize-none placeholder:text-stone-400"
        />

        <div className="flex items-center justify-between mt-2 mb-4">
          <div className="text-[11px] pmono text-stone-500">
            <span
              className={
                reason.trim().length >= 10
                  ? "text-emerald-700"
                  : reason.trim().length > 0
                  ? "text-amber-700"
                  : ""
              }
            >
              {reason.trim().length}
            </span>
            /10 chars
            {reason.trim().length > 0 && reason.trim().length < 10 && (
              <span className="text-amber-700 ml-2">
                · {10 - reason.trim().length} more for override
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <button
            onClick={() => commit("Accept")}
            disabled={savingAction !== null}
            className={`px-4 py-2.5 text-sm font-medium border transition flex items-center justify-center gap-2 ${TONE.emerald.btn} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <CircleCheck className="w-4 h-4" />
            Accept Forecast
          </button>
          <button
            onClick={() => commit("Override")}
            disabled={!overrideOk || savingAction !== null}
            className={`px-4 py-2.5 text-sm font-medium border transition flex items-center justify-center gap-2 ${TONE.amber.btn} disabled:opacity-40 disabled:cursor-not-allowed`}
            title={
              !overrideOk
                ? "Enter at least 10 characters in the reason field"
                : "Save override decision with the reason above"
            }
          >
            <CircleAlert className="w-4 h-4" />
            Override
          </button>
          <button
            onClick={() => commit("Escalate")}
            disabled={savingAction !== null}
            className={`px-4 py-2.5 text-sm font-medium border transition flex items-center justify-center gap-2 ${TONE.rose.btn} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <ArrowUpRight className="w-4 h-4" />
            Escalate
          </button>
        </div>
      </section>
    </div>
  );
}

function CompletionPanel({ decidedCount, totalItems }) {
  return (
    <div className="h-full grid place-items-center px-8 py-12">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-5 bg-emerald-50 border border-emerald-200 grid place-items-center">
          <Check className="w-7 h-7 text-emerald-600" strokeWidth={2.5} />
        </div>
        <h2 className="text-xl font-semibold text-stone-900">Queue cleared</h2>
        <p className="text-sm text-stone-600 mt-2 leading-relaxed">
          Every flagged exception has been reviewed. {decidedCount} of {totalItems}{" "}
          items decided this session.
        </p>
        <div className="mt-5 text-[11px] uppercase tracking-[0.18em] pmono text-stone-500">
          Open the audit log to review your trail
        </div>
      </div>
    </div>
  );
}

function AuditLogView({ log }) {
  if (log.length === 0) {
    return (
      <div className="px-6 py-16">
        <div className="max-w-md mx-auto text-center">
          <div className="w-12 h-12 mx-auto mb-4 bg-stone-100 border border-stone-200 grid place-items-center">
            <ScrollText className="w-5 h-5 text-stone-400" />
          </div>
          <div className="text-sm font-medium text-stone-900">
            No decisions logged yet
          </div>
          <div className="text-xs text-stone-500 mt-1">
            Decisions on exception items will appear here in reverse chronological order.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6">
      <div className="max-w-[1200px] mx-auto">
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] pmono text-stone-500">
              Audit Trail
            </div>
            <h2 className="text-lg font-semibold mt-0.5">
              {log.length} decision{log.length === 1 ? "" : "s"} recorded
            </h2>
          </div>
          <div className="text-[11px] pmono text-stone-500">Most recent first</div>
        </div>

        <div className="bg-white border border-stone-200 overflow-hidden">
          <div className="grid grid-cols-[200px_220px_140px_1fr] text-[10px] uppercase tracking-[0.15em] pmono text-stone-500 px-4 py-2.5 bg-stone-50 border-b border-stone-200">
            <span>Timestamp</span>
            <span>Item ID</span>
            <span>Action</span>
            <span>Reason</span>
          </div>
          <ul>
            {log.map((entry, idx) => {
              const meta = ACTION_META[entry.action];
              const Icon = meta?.icon ?? CircleCheck;
              const tone = meta?.tone ?? "stone";
              return (
                <li
                  key={`${entry.timestamp}-${entry.item_id}-${idx}`}
                  className="grid grid-cols-[200px_220px_140px_1fr] px-4 py-3 text-[13px] border-b border-stone-100 last:border-b-0 hover:bg-stone-50/60 items-center"
                >
                  <span className="pmono text-[12px] text-stone-700">
                    {fmtTimestamp(entry.timestamp)}
                  </span>
                  <span className="pmono text-[12px] text-stone-900">
                    {entry.item_id}
                  </span>
                  <span>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-medium border ${TONE[tone].pill}`}
                    >
                      <Icon className="w-3 h-3" />
                      {entry.action}
                    </span>
                  </span>
                  <span className="text-stone-700 leading-snug">
                    {entry.reason && entry.reason.trim().length > 0 ? (
                      entry.reason
                    ) : (
                      <span className="text-stone-400">—</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

function SessionDebriefView({ log, forecasts, onReset }) {
  const summary = useMemo(() => {
    const lookup = Object.fromEntries(forecasts.map((item) => [item.item_id, item]));
    const actions = {
      Accept: { count: 0, items: [], categories: {} },
      Override: { count: 0, items: [], categories: {} },
      Escalate: { count: 0, items: [], categories: {} },
    };
    let originalTotal = 0;
    let adjustedTotal = 0;
    let quantOverrides = 0;
    let qualitativeOverrides = 0;

    log.forEach((entry) => {
      const item = lookup[entry.item_id];
      if (!item || !actions[entry.action]) return;
      actions[entry.action].count += 1;
      actions[entry.action].items.push(item);
      actions[entry.action].categories[item.category] =
        (actions[entry.action].categories[item.category] || 0) + 1;
      originalTotal += item.point_forecast * 7;
      if (entry.action === "Override") {
        const revised = parseOverrideNumber(entry.reason || "");
        if (revised !== null) {
          adjustedTotal += revised * 7;
          quantOverrides += 1;
        } else {
          adjustedTotal += item.point_forecast * 7;
          qualitativeOverrides += 1;
        }
      } else {
        adjustedTotal += item.point_forecast * 7;
      }
    });

    const overrideCats = actions.Override.categories;
    let overrideCluster = null;
    let overrideClusterShare = 0;
    Object.entries(overrideCats).forEach(([category, count]) => {
      const share = actions.Override.count ? count / actions.Override.count : 0;
      if (share >= 0.6 && share > overrideClusterShare) {
        overrideCluster = category;
        overrideClusterShare = share;
      }
    });

    let insight = "Decision mix was balanced — use the audit log to inspect the most informative cases.";
    if (overrideCluster) {
      insight = `Overrides cluster in ${overrideCluster} — investigate whether this category needs its own model treatment`;
    } else if (actions.Override.count / Math.max(log.length, 1) >= 0.5) {
      insight = "You disagreed with the model on most cases — this suggests systematic under-trust or a model gap";
    } else if (actions.Escalate.count > 0) {
      insight = `${actions.Escalate.count} case(s) were escalated — these are the highest-priority follow-ups`;
    } else if (actions.Accept.count / Math.max(log.length, 1) >= 0.8) {
      insight = "Strong agreement with the model — consider whether exception thresholds are too sensitive";
    }

    return {
      total: log.length,
      actions,
      originalTotal,
      adjustedTotal,
      delta: adjustedTotal - originalTotal,
      deltaPct: originalTotal ? ((adjustedTotal - originalTotal) / originalTotal) * 100 : 0,
      quantOverrides,
      qualitativeOverrides,
      overrideCluster,
      insight,
    };
  }, [log, forecasts]);

  const { reasons, themes } = useMemo(() => computeThemes(log), [log]);
  const recommendation = generateRecommendation(summary, themes[0]?.token);

  return (
    <div className="px-6 py-6">
      <div className="max-w-[1200px] mx-auto">
        <div className="mb-5">
          <div className="text-[11px] uppercase tracking-[0.18em] pmono text-stone-500">
            Session Debrief
          </div>
          <h2 className="text-lg font-semibold mt-0.5">Review what the planner taught the workflow</h2>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <section className="bg-white border border-stone-200 p-4">
            <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500 pmono mb-3">Decision Pattern Summary</div>
            <div className="h-3 bg-stone-100 overflow-hidden flex mb-4">
              {["Accept", "Override", "Escalate"].map((action) => (
                <div
                  key={action}
                  className={action === "Accept" ? "bg-stone-400" : action === "Override" ? "bg-amber-500" : "bg-stone-700"}
                  style={{ width: `${summary.total ? (summary.actions[action].count / summary.total) * 100 : 0}%` }}
                />
              ))}
            </div>
            <div className="space-y-2 text-sm text-stone-700">
              {["Accept", "Override", "Escalate"].map((action) => {
                const cats = Object.entries(summary.actions[action].categories)
                  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                  .map(([category, count]) => `${category} × ${count}`)
                  .join(", ");
                return (
                  <div key={action}>
                    <span className="pmono text-stone-900">{action}</span> × {summary.actions[action].count}
                    <span className="text-stone-500"> — {cats || "none"}</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 border-t border-stone-200 pt-3 text-sm text-stone-800">{summary.insight}</div>
          </section>

          <section className="bg-white border border-stone-200 p-4">
            <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500 pmono mb-3">Business Impact</div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <MetricCard label="Original Weekly Total" value={summary.originalTotal} sub="point_forecast × 7" />
              <MetricCard label="Adjusted Weekly Total" value={summary.adjustedTotal} sub="override numbers applied" />
              <MetricCard
                label="Delta"
                value={`${summary.delta > 0 ? "+" : ""}${summary.delta}`}
                sub={`${summary.deltaPct > 0 ? "+" : ""}${summary.deltaPct.toFixed(1)}%`}
              />
            </div>
            <div className="mt-4 text-sm text-stone-700">
              {summary.quantOverrides} of {summary.actions.Override.count} overrides included a quantitative revision.{" "}
              {summary.qualitativeOverrides} overrides were qualitative.
            </div>
          </section>

          <section className="bg-white border border-stone-200 p-4">
            <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500 pmono mb-3">Reason Themes</div>
            {reasons.length < 3 ? (
              <div className="text-sm text-stone-500">Not enough reasons to surface themes</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {themes.map((theme) => (
                  <span
                    key={theme.token}
                    className="inline-flex items-center gap-2 px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200 text-sm"
                  >
                    <span>{theme.token}</span>
                    <span className="pmono text-[11px]">{theme.count}</span>
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="bg-white border border-stone-200 p-4">
            <div className="text-[10px] uppercase tracking-[0.15em] text-stone-500 pmono mb-3">Recommended Next Conversation</div>
            <div className="text-sm leading-relaxed text-stone-800">{recommendation}</div>
            <button
              onClick={onReset}
              className={`mt-4 px-4 py-2.5 text-sm font-medium border transition inline-flex items-center gap-2 ${TONE.stone.btn}`}
            >
              <RotateCcw className="w-4 h-4" />
              Start next session
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------
export default function PlannerConsole() {
  const [tab, setTab] = useState("queue");
  const [decisions, setDecisions] = useState({});
  const [auditLog, setAuditLog] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [reason, setReason] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [savingAction, setSavingAction] = useState(null);

  // Hydrate from window.storage on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      // Audit log
      try {
        const log = await window.storage.get("audit_log");
        if (!cancelled && log?.value) {
          const parsed = JSON.parse(log.value);
          if (Array.isArray(parsed)) setAuditLog(parsed);
        }
      } catch (e) {
        // Key absent — first run. Default empty array stays.
      }

      // Per-item decisions
      const decs = {};
      for (const item of sampleForecasts) {
        try {
          const d = await window.storage.get(`decisions:${item.item_id}`);
          if (d?.value) {
            decs[item.item_id] = JSON.parse(d.value);
          }
        } catch (e) {
          // No decision saved for this item yet.
        }
      }
      if (!cancelled) {
        setDecisions(decs);
        setHydrated(true);
      }
    }
    if (typeof window !== "undefined" && window.storage) {
      load().catch(() => setHydrated(true));
    } else {
      setHydrated(true);
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const exceptionItems = useMemo(() => sampleForecasts.filter((item) => item.is_exception), []);

  // Derived: items still in the queue
  const queue = useMemo(
    () =>
      exceptionItems.filter(
        (i) => i.is_exception && !decisions[i.item_id]
      ),
    [decisions, exceptionItems]
  );

  // Auto-select the first undecided item, or clear when none remain
  useEffect(() => {
    if (!hydrated) return;
    if (queue.length === 0) {
      if (selectedId !== null) setSelectedId(null);
      return;
    }
    if (!selectedId || !queue.find((i) => i.item_id === selectedId)) {
      setSelectedId(queue[0].item_id);
      setReason("");
    }
  }, [queue, selectedId, hydrated]);

  const selected = sampleForecasts.find((i) => i.item_id === selectedId);
  const overrideOk = reason.trim().length >= 10;

  async function commit(action) {
    if (!selectedId) return;
    if (action === "Override" && !overrideOk) return;
    setSavingAction(action);

    const ts = new Date().toISOString();
    const finalReason = action === "Accept" ? "" : reason.trim();
    const decision = {
      item_id: selectedId,
      action,
      reason: finalReason,
      timestamp: ts,
    };
    const newAudit = [decision, ...auditLog];

    // Optimistic local update
    setDecisions((prev) => ({ ...prev, [selectedId]: decision }));
    setAuditLog(newAudit);
    setReason("");

    // Persist
    if (typeof window !== "undefined" && window.storage) {
      try {
        await window.storage.set(
          `decisions:${selectedId}`,
          JSON.stringify(decision)
        );
        await window.storage.set("audit_log", JSON.stringify(newAudit));
      } catch (e) {
        console.error("Persistence failed:", e);
      }
    }
    setSavingAction(null);
  }

  async function handleReset() {
    if (typeof window !== "undefined" && window.storage) {
      for (const item of sampleForecasts) {
        try {
          await window.storage.delete(`decisions:${item.item_id}`);
        } catch (e) {
          // Key may not exist, that's fine
        }
      }
      try {
        await window.storage.delete("audit_log");
      } catch (e) {
        // ignore
      }
    }
    setDecisions({});
    setAuditLog([]);
    setReason("");
    setSelectedId(null);
    setTab("queue");
  }

  const totalItems = exceptionItems.length;
  const decidedCount = exceptionItems.filter((item) => decisions[item.item_id]).length;
  const pendingCount = queue.length;
  const debriefUnlocked = decidedCount === totalItems && totalItems > 0;

  return (
    <div
      className="min-h-screen bg-stone-50 text-stone-900"
      style={{
        fontFamily: "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        .pmono { font-family: 'IBM Plex Mono', ui-monospace, monospace; font-feature-settings: "tnum"; }
        textarea:focus { box-shadow: 0 0 0 3px rgba(12, 10, 9, 0.06); }
      `}</style>

      {/* Top bar */}
      <header className="bg-white border-b border-stone-200 sticky top-0 z-20">
        <div className="px-6 h-14 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 bg-stone-900 grid place-items-center">
              <Activity className="w-4 h-4 text-amber-300" strokeWidth={2.5} />
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold tracking-tight leading-tight">
                Planner Review Console
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-stone-500 leading-tight pmono">
                Demand Forecast · Exception Workflow
              </div>
            </div>
          </div>

          <nav className="flex items-center bg-stone-100 p-0.5 text-[13px] border border-stone-200/70">
            <button
              onClick={() => setTab("queue")}
              className={`px-4 py-1.5 transition flex items-center gap-2 ${
                tab === "queue"
                  ? "bg-white shadow-sm text-stone-900 font-medium"
                  : "text-stone-600 hover:text-stone-900"
              }`}
            >
              <ListChecks className="w-3.5 h-3.5" />
              Review Queue
              {pendingCount > 0 && (
                <span className="pmono text-[10px] bg-stone-900 text-white px-1.5 py-px tabular-nums">
                  {pendingCount}
                </span>
              )}
            </button>
            <button
              onClick={() => debriefUnlocked && setTab("debrief")}
              aria-disabled={!debriefUnlocked}
              title={debriefUnlocked ? "Review session patterns and business impact" : "Decide all queued items to unlock"}
              className={`px-4 py-1.5 transition flex items-center gap-2 ${
                tab === "debrief"
                  ? "bg-white shadow-sm text-stone-900 font-medium"
                  : debriefUnlocked
                  ? "text-stone-600 hover:text-stone-900"
                  : "text-stone-400 cursor-not-allowed"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              Session Debrief
              {debriefUnlocked && <span className="w-2 h-2 rounded-full bg-amber-500" />}
            </button>
            <button
              onClick={() => setTab("audit")}
              className={`px-4 py-1.5 transition flex items-center gap-2 ${
                tab === "audit"
                  ? "bg-white shadow-sm text-stone-900 font-medium"
                  : "text-stone-600 hover:text-stone-900"
              }`}
            >
              <ScrollText className="w-3.5 h-3.5" />
              Audit Log
              {auditLog.length > 0 && (
                <span className="pmono text-[10px] text-stone-500 tabular-nums">
                  {auditLog.length}
                </span>
              )}
            </button>
          </nav>

          <div className="text-[11px] pmono text-stone-500 hidden md:flex items-center gap-3">
            <span>
              <span className="text-stone-900">{decidedCount}</span> /{" "}
              {totalItems} decided
            </span>
            <span className="w-px h-4 bg-stone-200" />
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              {pendingCount} pending
            </span>
          </div>
        </div>
      </header>

      {/* Body */}
      {tab === "queue" ? (
        <ReviewQueueView
          queue={queue}
          selected={selected}
          decisions={decisions}
          onSelect={setSelectedId}
          reason={reason}
          setReason={setReason}
          overrideOk={overrideOk}
          commit={commit}
          savingAction={savingAction}
          totalItems={totalItems}
          decidedCount={decidedCount}
          onReset={handleReset}
        />
      ) : tab === "debrief" ? (
        <SessionDebriefView
          log={auditLog}
          forecasts={exceptionItems}
          onReset={handleReset}
        />
      ) : (
        <AuditLogView log={auditLog} />
      )}
    </div>
  );
}
