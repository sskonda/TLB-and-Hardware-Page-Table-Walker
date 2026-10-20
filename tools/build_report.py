#!/usr/bin/env python3
"""Build the double-column course paper from verified measured tables."""
import argparse
import csv
import json
from pathlib import Path


def build(evidence, plots, output):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import BaseDocTemplate, Frame, FrameBreak, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Table, TableStyle
    metrics=list(csv.DictReader((evidence/'performance/metrics.csv').open()))
    experiment=json.loads((evidence/'performance/experiments.json').read_text())
    regression=json.loads((evidence/'validation/regression.json').read_text())
    if not experiment['passed'] or not regression['passed'] or regression.get('scope')!='full' or len(metrics)!=144:
        raise ValueError('Verified full measured matrix required')
    def metric(trace,n,region='whole'):
        return next(row for row in metrics if row['trace']==trace and int(row['capacity'])==n and row['region']==region)
    output.parent.mkdir(parents=True,exist_ok=True)
    body=ParagraphStyle('body',fontName='Times-Roman',fontSize=9.3,leading=11.3,alignment=TA_JUSTIFY,spaceAfter=6)
    heading=ParagraphStyle('heading',parent=body,fontName='Times-Bold',fontSize=10.2,leading=12,spaceBefore=6,spaceAfter=5,alignment=TA_CENTER)
    caption=ParagraphStyle('caption',parent=body,fontSize=8.3,leading=10,alignment=TA_CENTER)
    title=ParagraphStyle('title',parent=body,fontSize=19,leading=22,alignment=TA_CENTER,spaceAfter=7)
    author=ParagraphStyle('author',parent=caption,fontSize=10,leading=12)
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=9.8)
    width=525.6; x=43.2; col=(width-18)/2
    def frame(name,px,py,pw,ph):return Frame(px,py,pw,ph,id=name,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    def footer(canvas,doc):
        canvas.setFont('Times-Roman',8)
        canvas.drawString(x,24,'EEL 5764 | ModelSim simulation study | 20 October 2026')
        canvas.drawRightString(x+width,24,str(doc.page))
    first=[frame('title',x,630,width,120),frame('left',x,44,col,572),frame('right',x+col+18,44,col,572)]
    figure=[frame('figure',x,394,width,356),frame('left',x,44,col,332),frame('right',x+col+18,44,col,332)]
    tabular=[frame('table',x,393,width,357),frame('left',x,44,col,331),frame('right',x+col+18,44,col,331)]
    doc=BaseDocTemplate(str(output),pagesize=(612,792),leftMargin=x,rightMargin=x,topMargin=42,bottomMargin=44,
                        title='Design and Evaluation of a TLB and Hardware Page Table Walker',author='Sanat Konda, Emerson Schmidt, Emilie Doan')
    doc.addPageTemplates([PageTemplate(id='first',frames=first,onPage=footer),PageTemplate(id='figure',frames=figure,onPage=footer),PageTemplate(id='tabular',frames=tabular,onPage=footer)])
    story=[]
    def p(text,style=body):story.append(Paragraph(text,style))
    def h(text):p(text,heading)
    def table(rows,widths,font=8.4):
        t=Table(rows,colWidths=widths,hAlign='CENTER')
        t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Times-Roman'),('FONTSIZE',(0,0),(-1,-1),font),
            ('LEADING',(0,0),(-1,-1),10),('FONTNAME',(0,0),(-1,0),'Times-Bold'),
            ('LINEABOVE',(0,0),(-1,0),.6,colors.black),('LINEBELOW',(0,0),(-1,0),.4,colors.black),
            ('LINEBELOW',(0,-1),(-1,-1),.6,colors.black),('LEFTPADDING',(0,0),(-1,-1),3),
            ('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        story.append(t)
    p('Design and Evaluation of a TLB and<br/>Hardware Page Table Walker',title)
    p('Sanat Konda, Emerson Schmidt, Emilie Doan',author)
    p('Computer Architecture, University of Florida<br/>SystemVerilog implementation and controlled simulation',caption)
    story.append(FrameBreak())
    p('<b>Abstract</b>—A standalone virtual-memory translator combines a fully associative TLB, tree pseudo-LRU and a two-level memory-backed page-table walker. The explicitly adopted, restricted Sv32-derived profile uses 32-bit virtual and 34-bit physical byte addresses. Immediate combinational hits preserve the page offset. ModelSim 2020.1 regressions exercise 4, 8 and 16 entries; independent event replay checks translations, replacement, cancellation and metrics. Across 48 fixed-input performance runs, sequential traffic achieves 98.4375% hits at all capacities; random 64-page traffic reaches about 6.2%, 12.4% and 25.3%. These are translation-subsystem simulation results, without CPU or FPGA performance claims.')
    h('I. Scope and adopted architecture')
    p('The project proposal specifies the associative TLB, immediate hits, simplified multi-level walker, three capacities and identical locality traces. It leaves address geometry, handshakes and faults open. The architecture specification and requirements-to-tests matrix preceded RTL. The adopted choices below were explicitly approved; they are not inferred course requirements or a claim of full RISC-V compliance [1].')
    table([['Property','Adopted specification'],['VA / PA / page','32 / 34 bits / 4 KiB'],['Levels / indices','L1, L0 / 10 + 10 bits'],['PTE / byte order','32 bits / little endian'],['Root byte address','0x1000'],['Permissions','Fixed user load/store/fetch'],['A/D behavior','Fault when required bit is clear'],['Outstanding work','One active translation'],['Memory transport','Tagged ready/valid read-only']],[88,col-88],8)
    p('All 20 VPN bits compare in parallel. Allocation selects the lowest invalid entry, then the PLRU victim. The N−1-bit tree points toward victim subtrees and updates away from an accepted hit or successful refill. Page offsets are unchanged. A redundant refill updates the existing VPN; multiple matches are verification failures.')
    p('A two-process walker latches accepted VA, access, root and cookie. Each physical PTE address uses the returned table PPN and the next VA index. No direct translation shortcut exists. Reset/flush clears all entries and the tree, cancels unfinished work and drains tagged late responses. Cookies must remain unique while old responses can arrive.')
    story.append(FrameBreak())
    h('II. Verification and timing definitions')
    p('Race-free stimulus changes on falling edges. A passive monitor samples rising-edge handshakes before register updates and inspects state after 1 ps. Independent byte-image translation and a leaf-set PLRU oracle do not use DUT victim or translation decisions as expected results. Procedural checks and explicit coverage retain compatibility with ModelSim Starter; no SVA, UVM, DPI or vendor IP is required. Circuit and testbench structure follow Stitt’s explanations [2].')
    p('For accepted edge a, first-result edge f and consumption edge c, first latency is f−a and consumption latency is c−a. Translation stalls count a ≤ e &lt; f in the requester. Eligibility queueing and response backpressure c−f are separate. A hit may accept and consume on one edge, giving zero sampled latency. A two-level miss with PTE latency L has first latency 2L+3; with L=5, 13 cycles is both the timing expectation and the observed fixed-run value.')
    p('The committed correctness matrix passed 27 positive configurations: three exhaustive PLRU, three standalone TLB, three zero-sample and 18 directed/random translation runs. Translation stress uses seeds 1, 7 and 42 at each capacity with fixed and separately variable memory latency. It accounts for 22,986 accepted requests, 22,572 completions and 414 deliberate cancellations. The translation/empty runs executed 21,055,093 procedural checks.')
    p('Standalone PLRU checks all 32,904 legal tree states and all 525,344 state/leaf updates across capacities. Directed tests cover every entry and victim, invalid-first allocation, high bits, offsets and table boundaries, every supported fault/access combination, backpressure, held/consecutive traffic, duplicate detection, full occupancy, all-entry flush, and reset/flush at nine walk/result phases. All 16 entries are populated before the high-entry flush checks.')
    p('Nineteen deliberate checker/tool failures exit nonzero for their designated reasons. Sixty malformed, truncated, duplicated or inconsistent log mutations are rejected. Logs include observed PTE presentation/acceptance/response, decode, refill/eviction, PLRU, first result, consumption and cancellations. Hash/schema/order checks and independent replay reconcile the counters. Finite regressions and coverage do not prove correctness.')
    p('Superpage success, privilege modes, ASIDs, virtualization, CPU/OS integration and walker-cache optimizations are excluded. Unsupported upper-level leaves fault. FPGA validation, synthesis measurements and course video/submission actions are not reported.')
    story += [NextPageTemplate('figure'),PageBreak()]
    story.append(Image(str(plots/'locality.png'),width=width-30,height=(width-30)*2/3))
    p('Fig. 1. Measured locality comparisons. Every point uses 8192 accepted loads; right panels exclude the first 1024 requests while retaining warmed state. Lines connect categorical trace cases, not a continuous sweep.',caption)
    story.append(FrameBreak())
    h('III. Controlled experiment')
    p('Sixteen traces were generated and SHA-256 hashed once, then identical bytes were replayed at all three capacities. The root, complete sparse little-endian PTE image, five-cycle PTE latency, 10 ns clock, request policy and region boundaries were fixed. Each case resets independently and drains completely. Performance traffic is fault-free, uncanceled and always ready to consume; correctness and variable-latency stress are separate.')
    p('Sequential loads advance by 64 bytes across 128 pages. The strided trace advances five pages modulo 64, with rotating within-page offsets. Random traces use a deterministic xorshift32 generator, 64 pages and independent byte offsets for seeds 1, 7 and 42. Repeated traces cycle working sets 2/3/4/5/7/8/9/15/16/17/32 pages. No trace or seed was selected after observing results.')
    p('The fixed mapping uses VA base 0x80000000, final table at physical 0x2000 and page-p data PPN 0x200000+((73p+19) mod 256). Table and data frames are separate. Nonidentity mappings, high physical bits and offsets make silent address truncation or bypass errors observable.')
    story.append(FrameBreak())
    h('IV. Locality results')
    p('Sequential traffic incurs exactly 128 walks and 8064 hits at every capacity. Each page supplies 64 accesses before advancing, so extra cached pages provide no benefit. Its mean first-result latency is 0.203125 cycles. The post-prefix hit rate remains 98.4375%; this stream continues to encounter new pages, so the chosen prefix does not eliminate compulsory misses.')
    p('The five-page stride visits all 64 pages before reuse because 5 and 64 are coprime. Every capacity misses on all 8192 accesses: mean latency is 13 cycles and translation stalls total 106,496 cycles. Capacity alone does not help a cyclic working set much larger than the TLB.')
    p('Random hit rates for seeds 1/7/42 are 6.262/6.323/6.177% at four entries and 25.159/25.171/25.476% at sixteen. Corresponding sixteen-entry means are 9.729/9.728/9.688 cycles. Per-seed rows are retained; these three deterministic samples do not establish a population confidence interval. Their behavior is consistent with approximately N/64 occupancy probability, but the measured bytes and replacement outcomes remain the evidence.')
    p('For every performance run, accepted=completed, hits+misses=accepted, walks=misses and summed first latency=translation stalls=13×misses. This reconciliation includes all 393,216 measured requests. Percentage latency reductions are relative to the four-entry baseline; a zero baseline is undefined and stored as null.')
    story.append(PageBreak())
    story.append(Image(str(plots/'working_sets.png'),width=width-30,height=(width-30)*2/3))
    p('Fig. 2. Measured cyclic working-set behavior. Explicit page counts label the sampled cases. Whole-run cold misses remain visible in the raw table; after the prefix, fitting working sets have zero misses.',caption)
    story.append(FrameBreak())
    h('V. Capacity and replacement')
    p('When W≤N, the repeated trace incurs W initial walks and then hits. Whole-run hit rates therefore approach, but do not equal, 100%; all fitting sets have 100% post-prefix hits. For W=4 the mean is 0.00634765625 cycles at every capacity. For W=16 it is 0.025390625 cycles at sixteen entries, compared with 13 at four and eight.')
    p('At W=5, four entries see one hit and 8191 misses, whereas eight and sixteen entries incur only five cold misses. At W=9, eight entries retain eight transient hits over the whole trace, while sixteen incurs nine cold misses. At W=17, sixteen entries see 62 transient hits and 8130 misses. Those finite PLRU warmup effects are preserved, not rounded into a universal all-miss rule.')
    p('Tree PLRU approximates recency and is not a stack replacement policy. This chosen matrix does not demonstrate a capacity regression, but it cannot establish that increasing capacity always improves hit rate on arbitrary traces. The exhaustive standalone oracle tests direction and update behavior independently of locality outcomes.')
    story.append(FrameBreak())
    h('VI. Evidence and limits')
    p('The repository preserves complete observed JSONL, CSV event projections, readable transaction listings, per-transaction summaries, raw counters, input bytes, transcripts and WLF. Large streams are losslessly compressed. A schema/order validator rejects orphan returns, missing decode/refill/state events, duplicate IDs, truncation and inconsistent accounting. A second tool reconstructs wrapper transitions and conflict coverage directly from the observed events.')
    p('Genuine ModelSim Wave-window screenshots and a Transcript-window capture document the cold walk/refill, immediate hit, full-capacity eviction, final-level fault, 16-entry flush, mid-walk reset/flush recovery and successful completion. Native PostScript exports are preserved separately. Captions identify WLF/log hashes, tested source, seed, transactions, signal radices, cursor and replay command. Screenshots aid inspection; logs establish the checked behavior.')
    p('These measurements describe a deterministic standalone requester and abstract memory responder. They do not predict CPU CPI/IPC, real DRAM behavior, FPGA clock rate, area or power. The immediate-hit combinational path was simulated, not physically timed. Optional Zybo Z7-20 validation was not performed. The source review records complete reachable history inventories and selected semantic depth, without claiming upstream defect reproduction or exhaustive code certification [3–6].')
    story += [NextPageTemplate('tabular'),PageBreak()]
    h('TABLE I. MEASURED WHOLE-TRACE RESULTS')
    p('Each cell is hit rate (%) / average first-result latency (cycles). All runs have 8192 accepted and completed requests. Walk and stall counts, cold-prefix and post-prefix regions, per-seed provenance and baseline deltas are in evidence/performance/metrics.csv.',caption)
    names=['sequential','strided','random_s1','random_s7','random_s42']+[f'repeated_w{n}' for n in [2,3,4,5,7,8,9,15,16,17,32]]
    rows=[['Trace','4 entries','8 entries','16 entries']]
    for name in names:
        rows.append([name.replace('_',' ')]+[f"{100*float(metric(name,n)['hit_rate']):.4f} / {float(metric(name,n)['average_latency']):.6f}" for n in [4,8,16]])
    table(rows,[105,(width-105)/3,(width-105)/3,(width-105)/3],8.5)
    story.append(FrameBreak())
    h('VII. Reproduction and provenance')
    p('The core correctness source is '+regression['source_commit']+'. The experiment source is '+experiment['source_commit']+'. Core RTL, benches, input generator and log-checker hashes match between them; the later revision adds experiment automation. Tool/version/options, commands, working-tree state, input hashes and source-file hashes are recorded per run. No later report/evidence commit is presented as the tested RTL revision.',small)
    p('The standard-library launcher creates clean libraries, compiles in dependency order, elaborates all capacities, enforces simulation and wall-clock watchdogs, and requires both bench completion and the Tcl sentinel. Compilation, elaboration, coverage, checker and unexpected-exit failures propagate nonzero. A full passing regression is a prerequisite to the performance matrix.',small)
    p('From the repository root: <font name="Courier" size="7">python3 sim/reproduce.py --out runs/reproduction --screenshots</font>. Add <font name="Courier" size="7">--config /private/path/modelsim.json</font> for platform-specific command arrays. Matplotlib is required only for publication plots; ReportLab is required only to rebuild this paper. Core verification requires neither. Archive verification: <font name="Courier" size="7">python3 tools/evidence.py --verify evidence</font>. See README.md and docs/evidence.md for replay and clean-checkout status.',small)
    p('Course proposal, guidelines, lectures and textbook sources were read from private local files. They remain read-only and unpublished; their hashes and review scope are documented. Team names above are those on the proposal, without asserting individual implementation contributions.',small)
    story.append(FrameBreak())
    h('References')
    refs=[
        '[1] RISC-V International, Privileged Architecture, supervisor chapter, version 20260120. docs.riscv.org/reference/isa/v20260120/priv/supervisor.html.',
        '[2] G. Stitt, SystemVerilog tutorial: combinational, sequential, FSM/FSMD, gotchas, RAM and testbenches. github.com/ARC-Lab-UF/sv-tutorial, revision 212f285.',
        '[3] BSC, MMU RTL and complete reachable history. github.com/bsc-loca/mmu, default tip 0f4727a; selected semantic review documented separately.',
        '[4] OpenHW Foundation, CVA5 MMU RTL/history. github.com/openhwfoundation/cva5, default tip 2acf79f; Apache-2.0.',
        '[5] Naminar, tlb-v RTL/history. github.com/Naminar/tlb-v, default tip aa62aea; MIT.',
        '[6] T. Barr, A. Cox and S. Rixner, “Translation Caching: Skip, Don’t Walk (the Page Table),” ISCA, 2010. Radix-walk background; optimizations excluded.',
        '[7] J. Hennessy and D. Patterson, Computer Architecture: A Quantitative Approach, 6th ed., Section 2.4 and Appendix B.4. Supplied course copy; not redistributed.'
    ]
    for ref in refs:p(ref,small)
    doc.build(story)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path);parser.add_argument('plots',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();build(args.evidence,args.plots,args.out)
