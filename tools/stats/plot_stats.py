import asyncio
import json
import os

# noinspection PyPackageRequirements
import matplotlib

# noinspection PyPackageRequirements
import matplotlib.font_manager as font_manager

# noinspection PyPackageRequirements
import matplotlib.pyplot as plt

# noinspection PyPackageRequirements
import numpy as np

import src.lookup as lookup
import src.verifier as verifier

DISP_ACT_PER_SEC = False
SHOW_LAST_N = 40000
AVG_ENTRIES = 20

KEYS = [
    "period",
    "actor_found",
    "page_fetched",
    "page_fetch_failed",
    "page_fetch_temporary_error",
    "actor_fetch_temporary_error",
    "schedule_random",
    "schedule_random_from_domain",
    "waiting_reachable",
    "page_refetched",
    "page_updated",
    "new_uri_found",
    "queue_size",
    "actor_signed",
    "peak_memory",
    "long_fetch",
]
RATE_KEYS = ["period", "page_fetched", "actor_found"]

font = "CMU Serif"
if os.name == "nt":
    font_path = "C:\\Python310\\Lib\\site-packages\\matplotlib\\mpl-data\\fonts\\ttf\\cmuSerif.ttf"
    font_manager.fontManager.addfont(font_path)
    prop = font_manager.FontProperties(fname=font_path)
    font = prop.get_name()

font = {"family": font, "size": 18}
matplotlib.rc("font", **font)
matplotlib.rc("mathtext", fontset="cm")


async def prepare_data(stats):
    cumulative = {k: [0] for k in KEYS}
    last = {k: [] for k in KEYS}
    aver = {k: [0] for k in KEYS}
    real = {k: [0] for k in KEYS}
    rates = {rk: {k: [0] for k in KEYS} for rk in RATE_KEYS}

    for d in stats:
        data = json.loads(d["json"])
        if data.get("period", 0) > 15:
            print("warning", d["id"], data)
        for k in KEYS:
            new_val = data.get(k, 0)
            cumulative[k].append(cumulative[k][-1] + new_val)
            last[k].append(new_val)
            real[k].append(new_val)
            if len(last[k]) > AVG_ENTRIES:
                last[k].pop(0)
            aver[k].append(sum(last[k]) / len(last[k]))
            for rk in RATE_KEYS:
                if len(last[k]) > 3 and sum(last[rk]) > 0:
                    rates[rk][k].append(sum(last[k]) / sum(last[rk]))
                else:
                    rates[rk][k].append(0)
    cumulative = {a: np.asarray(b) for a, b in cumulative.items()}
    aver = {a: np.asarray(b) for a, b in aver.items()}
    real = {a: np.asarray(b) for a, b in real.items()}
    rates = {a: {c: np.asarray(d) for c, d in b.items()} for a, b in rates.items()}
    return cumulative, aver, rates, real


def plot(
    xdata,
    ydata,
    x_name,
    y_names,
    legend,
    out_name="plot.png",
    same_23y=False,
    same_13y=False,
    same_12y=False,
    legend_loc="upper right",
    figsize=(10, 7),
    hlines=(),
    show_last_n=SHOW_LAST_N,
    ymax=None,
):
    xdata = xdata[-show_last_n:]
    ydata = [d[-show_last_n:] for d in ydata]

    fig, ax1 = plt.subplots(figsize=figsize)
    (l1,) = ax1.plot(xdata, ydata[0], color="blue", label="ratio")
    ax1.set_ylabel(y_names[0], color="black" if same_12y or len(ydata) == 1 else "blue")
    ax1.set_ylim(bottom=0)
    if ymax:
        ax1.set_ylim(top=ymax)
    plots = [l1]
    axis = [ax1]
    if len(ydata) > 1:
        ax2 = ax1 if same_12y else ax1.twinx()
        (l2,) = ax2.plot(xdata, ydata[1], color="red", label="rate")
        plots.append(l2)
        axis.append(ax2)
        if not same_12y:
            ax2.set_ylabel(y_names[1], color="red")
            ax2.set_ylim(bottom=0)
        if len(ydata) > 2:
            ax3 = ax2 if same_23y else ax1 if same_13y else ax1.twinx()
            (l3,) = ax3.plot(xdata, ydata[2], color="green", label="ratio")
            plots.append(l3)
            axis.append(ax3)
            if not same_23y and not same_13y:
                # ax3.set_ylabel(ynames[2], color="green")
                ax3.get_yaxis().set_visible(False)
                ax3.set_ylim(bottom=0)
    plt.legend(
        plots,
        legend,
        loc=legend_loc,
    )
    for axn, y, col in hlines:
        axis[axn].axhline(y=y, color=col, linewidth=2)
    ax1.set_xlabel(x_name)
    plt.tight_layout()
    plt.savefig("out/" + out_name, dpi=300)
    plt.show()


async def get_lookup_data(file):
    database = lookup.Database()
    await database.setup(file)
    stats = await database.stats.get_all()
    await database.close()
    return await prepare_data(stats)


async def get_verifier_data(file):
    database = verifier.Database()
    await database.setup(file)
    v_stats = await database.get_all_stats()
    await database.close()
    return await prepare_data(v_stats)


async def plot_active_fetched(file):
    cumulative, aver, rates, real = await get_lookup_data(file)
    plot(
        cumulative["period"] / 1000,
        [
            rates["period"]["page_fetched"],
            aver["waiting_reachable"],
            aver["waiting_reachable"] * 24,
        ],
        "time, * 1000 s",
        ["pages/s", "domains"],
        ["page fetching rate", "active domains", "active domains (scaled)"],
        "waitingvsfetched.png",
        same_23y=True,
    )


async def plot_actors_per_user(file):
    cumulative, aver, rates, real = await get_lookup_data(file)
    plot(
        cumulative["actor_found"] / 1000,
        [
            rates["actor_found"]["new_uri_found"]
            - 1,  # minus outbox of a user -- low priority
            rates["actor_found"]["page_fetched"],
            cumulative["page_fetched"] / cumulative["actor_found"],
            # aver["waiting_reachable"]
        ],
        "actors found, * 1000",
        ["units / actor"],
        [
            "new URIs added to queue / new actors found",
            "pages crawled / new actors found",
            "total pages crawled / total actors found",
        ],
        "actorsperuser.png",
        legend_loc="lower right",
        hlines=[(1, 1, "darkorange"), (1, 3, "darkorange"), (1, 5, "darkorange")],
        same_12y=True,
        same_23y=True,
    )


async def plot_page_refetch(file):
    cumulative, aver, rates, real = await get_lookup_data(file)
    plot(
        cumulative["period"],
        [
            rates["period"]["page_fetched"],
            rates["period"]["page_refetched"],
            rates["period"]["page_updated"],
            # aver["waiting_reachable"]
        ],
        "time, s",
        ["page / s"],
        [
            "a",
        ],
        "updatesperf.png",
        legend_loc="lower right",
        same_12y=True,
        same_23y=True,
    )


async def plot_verifier(file):
    with open("./out/mem-loc.log") as f:
        mem = np.asarray([0] + [int(x.split()[0]) for x in f.readlines() if x])
    v_cumulative, v_aver, v_rates, v_real = await get_verifier_data(file)

    plot(
        v_cumulative["period"][: mem.size],
        [
            v_rates["period"]["actor_signed"][: mem.size],
            mem[: v_cumulative["period"].size] / 1024 / 1024,
        ],
        "time, s",
        ["signatures/s", "Mb"],
        ["signing rate", "RAM usage"],
        "actorssigning.png",
        legend_loc="lower right",
        figsize=(9, 5),
        # show_last_n=630
    )


async def plot_verifier_compare(files, ynames, n, sn):
    period = None
    data = []
    for f in files:
        v_cumulative, v_aver, v_rates, v_real = await get_verifier_data(f)
        if period is None:
            period = v_cumulative["period"][sn:n] - v_cumulative["period"][sn]
        data.append(v_rates["period"]["actor_signed"][sn:n])
    plot(
        period,
        data,
        "time, s",
        ["signatures/s"],
        ynames,
        "signingcompare.png",
        figsize=(9, 5),
        legend_loc="lower right",
        same_12y=True,
    )


async def plot_simulation(datax, datay, datay1):
    datay = np.asarray(datay)
    datay1 = np.asarray(datay1)
    plot(
        np.asarray(datax),
        [
            (datay / (datay + datay1)),
        ],
        "probability that server is unreachable at any given time",
        [""],
        [
            "part of failed post shares that were rescued",
            "part of failed user searches that were rescued",
        ],
        "simul.png",
        legend_loc="lower right",
        ymax=1,
    )


async def main():
    # await plot_active_fetched("./out/final.db")
    # await plot_actors_per_user("./out/final.db")
    #
    # await plot_verifier("./out/ver-best.db")
    # await plot_verifier_compare(
    #     ["./out/ver-smq.db", "./out/ver-best.db", None],
    #     [
    #         "queue size = 2 * parallel requests limit, $\\textasciitilde 100$Mb RAM",
    #         "queue size = 5 * parallel requests limit, $\\textasciitilde 110$Mb RAM",
    #         "queue size = 50 * parallel requests limit, $\\textasciitilde 200$Mb RAM",
    #     ],
    #     n=67,
    #     sn=3,
    # )

    # await plot_page_refetch("./out/database.db")
    await plot_simulation(
        [0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
        [251, 938, 1958, 2845, 5596, 9487],
        [34, 94, 180, 337, 569, 750],
    )


if __name__ == "__main__":
    asyncio.run(main())
