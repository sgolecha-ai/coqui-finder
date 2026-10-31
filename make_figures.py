"""Turn results/*.json into figures/*.png and results/summary.md (gate check)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Reference palette (light mode): categorical slots 1-3, text and surface tokens.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
NOISE = [("quiet", "Quiet night (40 dB)", S1), ("typical", "Typical (50 dB)", S2),
         ("loud", "Loud chorus / rain (60 dB)", S3)]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 10.5, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "lines.linewidth": 2, "lines.markersize": 6,
})


def load(name):
    with open(f"results/{name}.json") as f:
        return json.load(f)


def target_line(ax, y, text):
    ax.axhline(y, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(ax.get_xlim()[1], y, f" {text}", va="center", ha="left", fontsize=9, color=INK2)


def circ_err(a, b):
    return abs((a - b + 180) % 360 - 180)


def fig_bearing(e1, summary):
    dists = sorted({r["dist"] for r in e1})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for key, label, col in NOISE:
        p90_call, p90_frog, det = [], [], []
        for d in dists:
            rows = [r for r in e1 if r["dist"] == d and r["noise"] == key]
            ce = [e for r in rows for e in r["call_errors"]]
            fe = [circ_err(r["frog_bearing"], r["az"]) if r["frog_bearing"] is not None else 180 for r in rows]
            p90_call.append(np.percentile(ce, 90) if ce else np.nan)
            p90_frog.append(np.percentile(fe, 90))
            det.append(100 * np.mean([min(r["n_near"], 5) / 5 for r in rows]))
        axes[0].plot(dists, p90_frog, "-o", color=col, label=label, zorder=3)
        axes[0].plot(dists, p90_call, ":", color=col, lw=1.5, zorder=2)
        axes[1].plot(dists, det, "-o", color=col, label=label, zorder=3)
        summary[key] = {"dist": dists, "p90_frog": p90_frog, "p90_call": p90_call, "det": det}
    ax = axes[0]
    ax.set_ylim(0, 60)
    ax.set_xlim(0, 31)
    target_line(ax, 15, "±15° target")
    ax.annotate("loud: off scale\nbeyond 20 m", xy=(21.5, 59), xytext=(24, 44), fontsize=9,
                color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.set_xlabel("Distance to frog (m)")
    ax.set_ylabel("Bearing error, 90th percentile (°)")
    ax.set_title("Bearing stays within ±15° to 15 m, except in a loud chorus")
    ax.text(0.5, 57, "solid = per frog (5 calls)   dotted = single call", fontsize=9, color=INK2)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.93), fontsize=9)
    ax = axes[1]
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 31)
    target_line(ax, 95, "95% target")
    ax.set_xlabel("Distance to frog (m)")
    ax.set_ylabel("Calls detected with correct bearing (%)")
    ax.set_title("Calls are detected out to 30 m on quiet nights")
    fig.tight_layout()
    fig.savefig("figures/fig1_bearing_and_detection.png", dpi=150)
    plt.close(fig)


def fig_two_frogs(e2, summary):
    seps = sorted({r["sep"] for r in e2})
    rate = [100 * np.mean([r["success"] for r in e2 if r["sep"] == s]) for s in seps]
    summary["two_frogs"] = dict(zip(seps, rate))
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    x = np.arange(len(seps))
    ax.bar(x, rate, width=0.6, color=S1, zorder=3)
    for xi, r in zip(x, rate):
        ax.text(xi, r + 2, f"{r:.0f}%", ha="center", fontsize=9, color=INK2)
    ax.set_xticks(x, [f"{s}°" for s in seps])
    ax.set_ylim(0, 110)
    ax.set_xlabel("Angle between the two frogs")
    ax.set_ylabel("Both frogs found, no extras (%)")
    ax.set_title("Two frogs separate reliably from about 30° apart")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig("figures/fig2_two_frog_resolution.png", dpi=150)
    plt.close(fig)


def fig_counting(e3, summary):
    ns = sorted({r["n_true"] for r in e3})
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    lim = max(ns) + 1
    ax.plot([0, lim], [0, lim], color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(lim - 0.2, lim - 0.6, "perfect", ha="right", fontsize=9, color=INK2)
    g = np.array([r["n_groups"] for r in e3])
    f = np.array([r["n_found"] for r in e3])
    t = np.array([r["n_true"] for r in e3])
    rng = np.random.default_rng(0)
    ax.scatter(t + rng.uniform(-0.15, 0.15, len(t)), f, s=28, color=S2, alpha=0.55,
               edgecolor=SURFACE, lw=0.8, label="vs. all frogs present", zorder=2)
    ax.scatter(g + rng.uniform(-0.15, 0.15, len(g)), f, s=28, color=S1, alpha=0.8,
               edgecolor=SURFACE, lw=0.8, label="vs. frogs ≥20° apart (resolvable)", zorder=3)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("True number (frogs present, or resolvable groups)")
    ax.set_ylabel("Frogs the device reports")
    ax.set_title("Count tracks resolvable frogs up to ~6; dense choruses undercount")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig("figures/fig3_counting.png", dpi=150)
    plt.close(fig)
    rows = []
    for n in ns:
        r = [x for x in e3 if x["n_true"] == n]
        rows.append({
            "n_true": n,
            "mean_found": np.mean([x["n_found"] for x in r]),
            "mean_groups": np.mean([x["n_groups"] for x in r]),
            "exact_vs_groups": 100 * np.mean([x["n_found"] == x["n_groups"] for x in r]),
            "within1_vs_groups": 100 * np.mean([abs(x["n_found"] - x["n_groups"]) <= 1 for x in r]),
            "recall": 100 * np.mean([x["n_matched"] / n for x in r]),
            "false_per_scene": np.mean([x["n_false"] for x in r]),
        })
    summary["counting"] = rows


def fig_range(e1, summary):
    from coqui_sim.pipeline import estimate_distance, range_class
    rows = [r for r in e1 if r["noise"] == "typical" and r["frog_level"] is not None]
    true_d = np.array([r["dist"] for r in rows])
    est_d = np.array([estimate_distance(r["frog_level"]) for r in rows])
    classes = ["near", "medium", "far"]
    cm = np.zeros((3, 3))
    for td, ed in zip(true_d, est_d):
        cm[classes.index(range_class(td)), classes.index(range_class(ed))] += 1
    cm_pct = 100 * cm / cm.sum(axis=1, keepdims=True)
    acc = 100 * np.trace(cm) / cm.sum()
    summary["range"] = {"accuracy": acc, "confusion_pct": cm_pct.tolist()}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    ds = sorted(set(true_d))
    med = [np.median(est_d[true_d == d]) for d in ds]
    lo = [np.percentile(est_d[true_d == d], 10) for d in ds]
    hi = [np.percentile(est_d[true_d == d], 90) for d in ds]
    ax.plot([0, 32], [0, 32], color=INK2, lw=1, ls=(0, (4, 3)))
    ax.errorbar(ds, med, yerr=[np.subtract(med, lo), np.subtract(hi, med)], fmt="o", color=S1,
                ecolor=S1, elinewidth=1.5, capsize=3, ms=6, zorder=3)
    for y in (5, 15):
        ax.axhspan(y - 0.05, y + 0.05, color=INK2)
    ax.text(31, 2.2, "near", ha="right", fontsize=9, color=INK2)
    ax.text(31, 9.5, "medium", ha="right", fontsize=9, color=INK2)
    ax.text(31, 17, "far", ha="right", fontsize=9, color=INK2)
    ax.set_xlim(0, 32)
    ax.set_ylim(0, 45)
    ax.set_xlabel("True distance (m)")
    ax.set_ylabel("Distance estimated from loudness (m)")
    ax.set_title("Loudness gives a rough range (median, 10–90% band)")
    ax = axes[1]
    ax.imshow(cm_pct, cmap="Blues", vmin=0, vmax=100)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cm_pct[i, j]:.0f}%", ha="center", va="center",
                    color=SURFACE if cm_pct[i, j] > 55 else INK, fontsize=11)
    ax.set_xticks(range(3), classes)
    ax.set_yticks(range(3), classes)
    ax.set_xlabel("Device says")
    ax.set_ylabel("Truth")
    ax.grid(False)
    ax.set_title(f"Range class correct {acc:.0f}% of the time")
    fig.tight_layout()
    fig.savefig("figures/fig4_range_classes.png", dpi=150)
    plt.close(fig)


def fig_foliage(e4, summary):
    gains = sorted({r["refl_gain"] for r in e4})
    p90 = [np.percentile([r["frog_error"] for r in e4 if r["refl_gain"] == g and r["frog_error"] is not None], 90)
           for g in gains]
    summary["foliage"] = dict(zip(gains, p90))
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    x = np.arange(len(gains))
    ax.bar(x, p90, width=0.55, color=S1, zorder=3)
    for xi, v in zip(x, p90):
        ax.text(xi, v + 0.6, f"{v:.1f}°", ha="center", fontsize=9, color=INK2)
    ax.set_xticks(x, ["none", "light", "moderate", "strong"])
    ax.set_ylim(0, max(20, max(p90) + 5))
    ax.set_xlim(-0.6, len(gains) - 0.4)
    target_line(ax, 15, "±15°")
    ax.set_xlabel("Echoes from leaves and trunks near the frog")
    ax.set_ylabel("Bearing error at 10 m, p90 (°)")
    ax.set_title("Foliage echoes cost a few degrees, not the bearing")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig("figures/fig5_foliage.png", dpi=150)
    plt.close(fig)


def write_summary(s):
    def at(key, d):
        i = s[key]["dist"].index(d)
        return s[key]["p90_frog"][i], s[key]["p90_call"][i], s[key]["det"][i]

    tf, tc, td = at("typical", 15)
    lines = ["# Simulation results: XVF3800 for the Coqui Finder", "",
             "## Gate 1 check (typical night, frog at 15 m)", "",
             "| Target | Result | Pass |", "| --- | --- | --- |",
             f"| Bearing within ±15° (90% of frogs, 5 calls) | {tf:.1f}° | {'yes' if tf <= 15 else 'no'} |",
             f"| Bearing within ±15° (90% of single calls) | {tc:.1f}° | {'yes' if tc <= 15 else 'no'} |",
             f"| Detect ≥95% of calls | {td:.0f}% | {'yes' if td >= 95 else 'no'} |", "",
             "## Bearing error (p90, per frog) by distance", "",
             "| Distance (m) | " + " | ".join(k for k, _, _ in NOISE) + " |",
             "| --- | " + " | ".join("---" for _ in NOISE) + " |"]
    for i, d in enumerate(s["quiet"]["dist"]):
        lines.append(f"| {d} | " + " | ".join(f"{s[k]['p90_frog'][i]:.1f}°" for k, _, _ in NOISE) + " |")
    lines += ["", "## Two frogs: success by separation", "",
              "| Separation | " + " | ".join(f"{k}°" for k in s["two_frogs"]) + " |",
              "| --- | " + " | ".join("---" for _ in s["two_frogs"]) + " |",
              "| Both found, no extras | " + " | ".join(f"{v:.0f}%" for v in s["two_frogs"].values()) + " |",
              "", "## Counting (25 s listen, frogs 2–20 m, typical night)", "",
              "| Frogs present | Resolvable groups (mean) | Reported (mean) | Exact vs groups | Within ±1 | Real frogs pointed to | False frogs per listen |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in s["counting"]:
        lines.append(f"| {r['n_true']} | {r['mean_groups']:.1f} | {r['mean_found']:.1f} | {r['exact_vs_groups']:.0f}% | "
                     f"{r['within1_vs_groups']:.0f}% | {r['recall']:.0f}% | {r['false_per_scene']:.2f} |")
    cm = np.array(s["range"]["confusion_pct"])
    lines += ["", f"## Range class from loudness: {s['range']['accuracy']:.0f}% correct", "",
              "| Truth \\ Device | near | medium | far |", "| --- | --- | --- | --- |"]
    for name, row in zip(["near", "medium", "far"], cm):
        lines.append(f"| {name} | " + " | ".join(f"{v:.0f}%" for v in row) + " |")
    lines += ["", "## Foliage echoes (frog at 10 m, p90 per-frog error)", "",
              "| Echo strength | " + " | ".join(str(k) for k in s["foliage"]) + " |",
              "| --- | " + " | ".join("---" for _ in s["foliage"]) + " |",
              "| Error | " + " | ".join(f"{v:.1f}°" for v in s["foliage"].values()) + " |"]
    with open("results/summary.md", "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs("figures", exist_ok=True)
    s = {}
    e1 = load("e1_single_frog")
    fig_bearing(e1, s)
    fig_two_frogs(load("e2_two_frogs"), s)
    fig_counting(load("e3_counting"), s)
    fig_range(e1, s)
    fig_foliage(load("e4_foliage"), s)
    write_summary(s)
    print(open("results/summary.md").read())


if __name__ == "__main__":
    main()
