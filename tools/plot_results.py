#!/usr/bin/env python3
"""Plot verified measured metrics; matplotlib is required only for publication figures."""
import argparse
import csv
from pathlib import Path


def plot(csv_path,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows=list(csv.DictReader(Path(csv_path).open()))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    colors={4:"#29539b",8:"#d9822b",16:"#208c66"}
    plt.rcParams.update({"font.size":9,"axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none"})
    for family,names in [("locality",["sequential","strided","random_s1","random_s7","random_s42"]),
                         ("working_sets",[f"repeated_w{n}" for n in [2,3,4,5,7,8,9,15,16,17,32]])]:
        fig,axes=plt.subplots(2,2,figsize=(9,6),layout="constrained")
        for col,region in enumerate(["whole","post_warmup"]):
            for n in [4,8,16]:
                selected=[next(r for r in rows if r["trace"]==name and int(r["capacity"])==n and r["region"]==region) for name in names]
                for row,field,multiplier in [(0,"hit_rate",100),(1,"average_latency",1)]:
                    axes[row,col].plot(range(len(names)),[float(r[field])*multiplier for r in selected],marker="o",markersize=4,color=colors[n],label=f"{n} entries")
            axes[0,col].set_title("Whole trace" if region=="whole" else "After first 1024 requests")
            axes[0,col].set_ylabel("TLB hit rate (%)");axes[0,col].set_ylim(-2,102)
            axes[1,col].set_ylabel("Mean first-result latency (cycles)");axes[1,col].set_ylim(-.2,13.5)
            labels=[name.split("_w")[1] for name in names] if family=="working_sets" else [n.replace("random_s","random seed ") for n in names]
            for axis in axes[:,col]:
                axis.set_xticks(range(len(names)),labels,rotation=0 if family=="working_sets" else 25,ha="center" if family=="working_sets" else "right")
                axis.grid(axis="y",alpha=.25)
            axes[1,col].set_xlabel("Repeated working set (pages)" if family=="working_sets" else "Trace")
        axes[0,0].legend(loc="best",frameon=False)
        fig.suptitle("Measured in ModelSim 2020.1 | 8192 requests | two levels | 5-cycle PTE memory",fontsize=10)
        fig.savefig(out/(family+".png"),dpi=220)
        fig.savefig(out/(family+".svg"))
        plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics",type=Path);parser.add_argument("out",type=Path)
    args=parser.parse_args();plot(args.metrics,args.out)
