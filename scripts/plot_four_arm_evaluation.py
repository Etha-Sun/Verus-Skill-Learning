"""Reproduce four-arm presentation figures from settled, complete evaluation matrices."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont

from summarize_success_timeout_tokens import distribution


LABELS = ['R1-A 扁平78卡', 'R1-B 整篇读取', 'R2-B 整篇读取', 'R2-C 按需读取']
COLORS = ['#8493a5', '#3c72b4', '#3c72b4', '#14887c']
FONT = '/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf'
MEASURES = ('prompt_tokens', 'completion_tokens', 'actor_seconds', 'estimated_cost_usd', 'uniform_usd')
SETUP_TEXT = """## Shared Setup: Yuechun's Recommended Baseline

**Baseline recipe: shared corrected TASK + original Executive + repaired78 short index + matched tool/library permissions.** Arm A implements this recipe directly. Arms B and C retain the same task instructions and Executive, but change the knowledge organization and reading interface as described below; the index itself is therefore not identical across A/B/C.

- **TASK and Executive:** The shared corrected TASK defines the proof-repair task and constraints. The original VeruSAGE Executive supplies the general solving instructions; the diagnostic-first Executive variant is not used. These are solving instructions, not checkpoint augmentation hints.
- **Model and harness:** DeepSeek V4 Pro (`deepseek-v4-pro`), reasoning effort `max`, Codex 0.147.0, native Responses transport. Context limit: 1,048,576 tokens; output limit: 131,072 tokens per model request, not per episode.
- **Evaluation:** The same fixed validation20 tasks, one fresh run per task per arm, a 600-second actor budget, and two concurrent workers. All runs start from the original unverified task, not a selected checkpoint. Success requires passing both Verus verification and the Lynette proof-only safety check within budget.
- **Tools and permissions:** The same proof-editing and verification tools, installed `vstd` read access, and isolation policy in every arm. Executable behavior and specifications must be preserved; verification bypasses are forbidden. Reading knowledge is optional, with no mandatory retrieval or oracle-selected cards.
- **Knowledge source:** All variants derive from the same repaired78 bank. B and C reorganize that bank rather than adding a new training source.

All arms use the same local Verus version, `0.2025.09.12.bb1f342`. Its binary hash differs from Yuechun's historical build, so these runs share a matched local environment rather than being bit-identical historical replays.

## A/B/C Variants

| Variant | Knowledge organization | What the solving agent reads |
|---|---|---|
| **A: Flat 78-card baseline** | Yuechun's repaired78 cards with the compact flat index in the main skill file. | The agent optionally selects individual cards from the index and reads their bodies. |
| **B: Grouped, whole-reference reading** | Trace2Skill-inspired offline clustering and within-group consolidation: 78 source cards become 72 rules organized into 37 references, with a compact reference index in the main skill file. | Selecting a reference returns its full content, including all rules in that reference. There is no within-reference rule-selection step. |
| **C: Grouped, selective reading + navigation revision** | The same 37 groups and 72 rule bodies as B. Adds internal navigation, revises 23 rule cues, adds relationship notes to 21 multi-rule groups, and corrects 5 shared Scope descriptions. | The 16 single-rule references return their bodies directly. The 21 multi-rule references first expose a directory; the agent may then read selected rules or request the full reference. |

The router is used offline to organize the bank; no additional routing model is called during proof solving. C is a **combined reading-interface and navigation intervention**, not a pure reading-granularity ablation.

### How References Are Organized

A reference is a **small family of related proof-repair rules**, not a training-task transcript or one indiscriminately merged card. Cards are grouped offline by the proof situation and repair mechanism (for example, quantifier instantiation, opaque-spec unfolding, or reuse of an existing lemma). Within each group, compatible redundant guidance is consolidated; distinct premises, proof directions, and exceptions remain separate rules with source-card IDs.

The main `SKILL.md` provides a compact index of the 37 families. Each reference contains shared **Scope** information followed by its rules and their applicability, actions, validation guidance, and exclusions. In C, a multi-rule reference first presents short **When/Avoid** cues and a **Relationship** note; the full rule bodies remain separately accessible.

For example, `direct-existing-lemma-bridge` contains three distinct entries: reuse a matching library lemma; derive equal views from marshalability and equal serialization; or derive equal marshalability from equal views. B exposes all three together. C lets the agent select the entry matching its current premise-to-goal direction, while retaining a full-reference fallback.

## Experimental Rounds

- **Round 1:** R1-A versus R1-B — flat cards versus grouped whole-reference reading.
- **Round 2:** R2-B versus R2-C — grouped whole-reference reading versus selective reading plus navigation revisions.
- **R1-B and R2-B have identical skill-package hashes and fixed settings.** R2-B is a fresh control run, not a new B variant or a reused R1-B result. There are three configurations across four experimental arms, each evaluated on the same 20 tasks.
"""


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(entry, round_number):
    row, usage, retrieval = entry['row'], entry['settled_usage'], entry['retrieval']
    passed = bool(row['proof_solved'] and row['safety_passed'] and row['within_budget']
                  and not row['timed_out'] and row['provider_valid'])
    complete = usage['requests'] > 0 and not any(usage.get(key, 0) for key in
        ('unmetered_requests', 'error_requests', 'unknown_cost_requests', 'incomplete_requests'))
    return dict(round=round_number, condition=entry['condition'], task_id=row['id'],
        episode=entry['episode'], passed=passed, strict_pass=passed and row['fidelity'] == 'V2_TRACE',
        timed_out=row['timed_out'], fidelity=row['fidelity'], usage_complete=complete,
        prompt_tokens=usage['prompt_tokens'], completion_tokens=usage['completion_tokens'],
        actor_seconds=row['actor_wall_seconds'], estimated_cost_usd=usage['estimated_cost_usd'],
        uniform_usd=(usage['prompt_cache_hit_tokens'] * .022 + usage['prompt_cache_miss_tokens'] * .66
                     + usage['completion_tokens'] * 1.98) / 1_000_000,
        body_reads=retrieval.get('read_calls', 0) + retrieval.get('reference_read_calls', 0),
        directory_reads=retrieval.get('reference_directory_calls', 0),
        body_bytes=retrieval.get('helper_body_content_bytes'),
        directory_bytes=retrieval.get('helper_directory_content_bytes'),
        full_fallbacks=retrieval.get('helper_full_fallback_calls'),
        selected_rule_calls=retrieval.get('helper_selected_rule_calls'))


def summarize(rows):
    return dict(episodes=len(rows), solved=sum(row['passed'] for row in rows),
        strict_solved=sum(row['strict_pass'] for row in rows),
        timeouts=sum(row['timed_out'] for row in rows),
        incomplete_usage=sum(not row['usage_complete'] for row in rows),
        body_read_episodes=sum(row['body_reads'] > 0 for row in rows),
        directory_read_episodes=sum(row['directory_reads'] > 0 for row in rows),
        totals={key: sum(row[key] for row in rows) for key in MEASURES},
        distributions={group: {key: distribution([row[key] for row in rows if predicate(row)])
            for key in MEASURES} for group, predicate in
            [('all', lambda row: True), ('success', lambda row: row['passed']),
             ('timeout', lambda row: row['timed_out'])]})


def paired(rows):
    by_task = {}
    for row in rows:
        pair = by_task.setdefault(row['task_id'], {})
        assert row['condition'] not in pair
        pair[row['condition']] = row
    assert len(by_task) == 20 and all(set(pair) == {'old', 'revised'} for pair in by_task.values())
    pairs = list(by_task.values())
    complete = [pair for pair in pairs if all(row['usage_complete'] for row in pair.values())]
    joint = [pair for pair in complete if all(row['passed'] for row in pair.values())]
    changes = {}
    for label, sample in [('complete_billing_pairs', complete), ('joint_success', joint)]:
        changes[label] = {'n': len(sample), 'metrics': {}}
        for key in MEASURES:
            old = sum(pair['old'][key] for pair in sample)
            new = sum(pair['revised'][key] for pair in sample)
            changes[label]['metrics'][key] = dict(old=old, new=new,
                percent_change=100 * (new / old - 1) if old else None)
    generator = random.Random(20261006)
    deltas = [int(pair['revised']['passed']) - int(pair['old']['passed']) for pair in pairs]
    boot = sorted(100 * sum(generator.choices(deltas, k=20)) / 20 for _ in range(10000))
    def percentile(fraction):
        position = (len(boot) - 1) * fraction
        lower = int(position)
        return boot[lower] + (boot[min(lower + 1, len(boot) - 1)] - boot[lower]) * (position - lower)
    return dict(**changes, success_delta_pp=100 * sum(deltas) / 20,
        success_delta_95ci_pp=[percentile(.025), percentile(.975)],
        wins=[key for key, pair in by_task.items() if pair['revised']['passed'] and not pair['old']['passed']],
        losses=[key for key, pair in by_task.items() if pair['old']['passed'] and not pair['revised']['passed']])


class Canvas:
    def __init__(self, width, height):
        self.image = Image.new('RGB', (width, height), '#f6f8fb')
        self.draw = ImageDraw.Draw(self.image)
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                      f'<rect width="{width}" height="{height}" fill="#f6f8fb"/>']

    def rect(self, box, fill):
        self.draw.rectangle(box, fill=fill)
        left, top, right, bottom = box
        self.parts.append(f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="{fill}"/>')

    def text(self, position, value, size=27, color='#1e293b'):
        value = str(value)
        self.draw.text(position, value, font=ImageFont.truetype(FONT, size), fill=color)
        left, top = position
        self.parts.append(f'<text x="{left}" y="{top + size}" font-family="AR PL SungtiL GB,serif" font-size="{size}" fill="{color}">{html.escape(value)}</text>')

    def save(self, root, name):
        self.image.save(root / (name + '.png'))
        self.image.save(root / (name + '.pdf'), resolution=150)
        (root / (name + '.svg')).write_text('\n'.join(self.parts + ['</svg>']))


def figures(root, arms):
    canvas = Canvas(2400, 1600)
    canvas.text((70, 40), 'Verus 证明：卡片组织与按需读取评测', 54)
    canvas.text((70, 115), '两轮独立配对实验 | 固定 validation20 | 每臂每题 1 次 | DeepSeek V4 Pro/max | 600s', 29)
    metrics = [('预算内双检查通过（题 / 20）', [arm['solved'] for arm in arms], 20, '{:.0f}'),
               ('累计输入 token（百万）', [arm['totals']['prompt_tokens']/1e6 for arm in arms], None, '{:.2f}'),
               ('累计输出 token（千）', [arm['totals']['completion_tokens']/1e3 for arm in arms], None, '{:.1f}'),
               ('累计 actor 时间（分钟）', [arm['totals']['actor_seconds']/60 for arm in arms], None, '{:.1f}'),
               ('统一费率估算成本（USD）', [arm['totals']['uniform_usd'] for arm in arms], None, '{:.3f}'),
               ('调用 reader 读取正文的任务数（/20）', [arm['body_read_episodes'] for arm in arms], 20, '{:.0f}')]
    for index, (title, values, maximum, formatting) in enumerate(metrics):
        left = 65 + (index % 2) * 1170
        top = 190 + (index // 2) * 410
        canvas.rect((left, top, left + 1110, top + 380), '#ffffff')
        canvas.text((left+30, top+22), title, 33)
        maximum = maximum or max(values) * 1.15
        for fraction in (0, .5, 1):
            coordinate = left + 310 + 660 * fraction
            canvas.rect((coordinate, top+82, coordinate+1, top+326), '#e7edf4')
            canvas.text((coordinate-10, top+335), f'{maximum*fraction:.1f}', 21, '#64748b')
        for arm_index, value in enumerate(values):
            row_top = top + 90 + arm_index * 61
            canvas.text((left+27, row_top+1), LABELS[arm_index], 25)
            length = 660 * value / maximum
            canvas.rect((left+310, row_top, left+310+length, row_top+33), COLORS[arm_index])
            suffix = '*' if arm_index == 1 and index in (1, 2, 4) and arms[1]['incomplete_usage'] else ''
            canvas.text((left+320+length, row_top-1), formatting.format(value)+suffix, 25)
    canvas.text((75, 1450), f'严格 V2 合规成功：{arms[0]["strict_solved"]} / {arms[1]["strict_solved"]} / {arms[2]["strict_solved"]} / {arms[3]["strict_solved"]}（各 /20）。* R1-B 一条账本用量不完整，成本与 token 为已知量。', 25)
    canvas.text((75, 1490), '只作同轮配对比较；C 同时包含导航修订。读取指标不含目录暴露，不等于实际采纳。费用不含构建与计分集外尝试。', 25)
    canvas.text((75, 1530), '完整计分矩阵：每臂20题，固定验证集单次开发评测。详细方法、计分口径与费用范围见 REPORT.md。', 25)
    canvas.save(root, 'evaluation_overview')
    table = Canvas(2400, 850)
    table.text((60, 35), '四组评测结果总表', 52)
    table.text((60, 108), '同一 validation20；每臂20次；R1比较组织形式，R2比较整篇读取与按需读取＋导航修订', 29)
    headers = ['实验组', '成功 /20', 'V2 /20', '输入 M', '输出 K', '时间 min', '估算 USD', '正文读取 /20']
    positions = [80, 490, 720, 960, 1190, 1440, 1710, 2000]
    table.rect((55, 182, 2345, 265), '#20334b')
    for position, header in zip(positions, headers):
        table.text((position, 205), header, 31, '#ffffff')
    for index, arm in enumerate(arms):
        top = 265 + index * 103
        table.rect((55, top, 2345, top+102), '#ffffff' if index % 2 == 0 else '#edf3f9')
        suffix = '*' if arm['incomplete_usage'] else ''
        values = [LABELS[index], f'{arm["solved"]} ({arm["solved"]*5}%)', str(arm['strict_solved']),
                  f'{arm["totals"]["prompt_tokens"]/1e6:.3f}'+suffix,
                  f'{arm["totals"]["completion_tokens"]/1e3:.3f}'+suffix,
                  f'{arm["totals"]["actor_seconds"]/60:.2f}',
                  f'{arm["totals"]["estimated_cost_usd"]:.4f}'+suffix,
                  str(arm['body_read_episodes'])]
        for position, value in zip(positions, values):
            table.text((position, top+33), value, 31)
    table.text((65, 715), '输入/输出为全部计分任务累计量；actor 时间不是并行墙钟时间。估算 USD 采用账本时段费率。', 27)
    table.text((65, 755), '* 含一条用量不完整记录，仅列已知量；资源改善请看同轮完整配对表。详细方法与费用范围见报告。', 27)
    table.save(root, 'evaluation_table')


def comparison_report(rows, names):
    groups = [[row for row in rows if row['round'] == number and row['condition'] == condition]
              for number in (1, 2) for condition in ('old', 'revised')]
    assert all(len(group) == 20 and len({row['task_id'] for row in group}) == 20 for group in groups)
    task_ids = {row['task_id'] for row in groups[0]}
    assert all({row['task_id'] for row in group} == task_ids for group in groups)
    solved = [{row['task_id'] for row in group if row['passed']} for group in groups]
    lines = ['# Four-Arm Task Outcome Comparison', '', SETUP_TEXT.strip(), '',
        'Fixed validation20 set, with one run per task per arm. Success requires passing both Verus and Lynette checks within the 600-second budget.', '',
        f'**Flat 78-card baseline (R1-A): {len(solved[0])}/20; R1-B: {len(solved[1])}/20; R2-B: {len(solved[2])}/20; R2-C: {len(solved[3])}/20.**', '',
        '## Table 1. Gains and Losses Relative to the Flat 78-Card Baseline', '',
        '| Compared with the flat baseline | Solved by both | Newly solved | Baseline successes lost |',
        '|---|---:|---:|---:|']
    labels = ['R1-B Whole-reference reading', 'R2-B Whole-reference reading', 'R2-C Selective reading']
    for label, successful in zip(labels, solved[1:]):
        lines.append(f'| {label} | {len(solved[0] & successful)} | {len(successful - solved[0])} | {len(solved[0] - successful)} |')
    lines.extend(['', '## Table 2. Tasks with Different Outcomes Across Arms', '',
        '✓ denotes success within budget; ✗ denotes an unsuccessful run. All ✗ entries below are timeouts. Task names omit shared prefixes.', '',
        '| Task | Flat 78 cards | R1-B Whole-reference | R2-B Whole-reference | R2-C Selective |',
        '|---|:---:|:---:|:---:|:---:|'])
    differences = [ident for ident in names if len({ident in successful for successful in solved}) > 1]
    for ident in differences:
        records = [next(row for row in group if row['task_id'] == ident) for group in groups]
        assert all(row['passed'] or row['timed_out'] for row in records)
        name = names[ident].split('__')[-1]
        if 'vrs_rely_condition_equivalent' in name:
            name = 'Rely condition equivalence'
        elif name == 'new':
            name = 'delegation_map::impl4::new'
        lines.append(f'| `{name}` | '+' | '.join('✓' if ident in successful else '✗' for successful in solved)+' |')
    common = len(set.intersection(*solved))
    failed = len(task_ids - set.union(*solved))
    lines.extend(['', f'Remaining tasks: **{common} were solved by all four arms, and {failed} timed out in all four arms.**', '',
        '**Takeaway:** R1-B retains every baseline success and solves one additional task. R2-B gains two and loses one; R2-C gains three and loses two. Each arm therefore solves one more task overall than the flat baseline.', '',
        '**Comparison scope:** Only R1-A and R1-B form a within-round comparison against the flat baseline; comparisons of the R2 arms with that baseline are descriptive cross-round comparisons. R1-B and R2-B use the same skill configuration. The tables do not additionally exclude successes with editing-protocol violations. Under strict V2 compliance, the success counts for R1-A, R1-B, R2-B, and R2-C are '+
        ', '.join(str(sum(row['strict_pass'] for row in group)) for group in groups)+', respectively (each out of 20).', '',
        'Resource usage, costs, paired statistics, and methodological notes are available in the [detailed statistical appendix](DETAILS.md) (Chinese). Per-task data are in [episodes.csv](episodes.csv).'])
    return '\n'.join(lines)+'\n'


def build(base, root):
    first = base / 'card-organization-evaluation-20261012-v5'
    second = base / 'selective-reference-evaluation-20261013-v2'
    assert read(second / 'status.json')['phase'] == 'complete', 'Second round is not complete'
    sources = [first / 'combined_summary.json', second / 'combined/summary.json']
    summaries = [read(path) for path in sources]
    assert not summaries[1]['failures'] and summaries[1]['bridge_drained']
    contracts = [read(folder / 'validation_contract.json') for folder in (first, second)]
    task_sources = [{item['id']: item['source_sha256'] for item in contract['items']} for contract in contracts]
    assert task_sources[0] == task_sources[1] and len(task_sources[0]) == 20
    assert contracts[0]['artifacts']['revised']['artifact_sha256'] == contracts[1]['artifacts']['old']['artifact_sha256']
    for field in ('model', 'reasoning_effort', 'timeout_seconds', 'workers', 'installed_library_conditions'):
        assert contracts[0][field] == contracts[1][field]
    rows = []
    for round_number, summary in enumerate(summaries, 1):
        assert len(summary['rows']) == 40
        for entry in summary['rows']:
            assert entry['row']['source_sha256'] == task_sources[0][entry['row']['id']]
            rows.append(normalize(entry, round_number))
    groups = [[row for row in rows if row['round'] == number and row['condition'] == condition]
              for number in (1, 2) for condition in ('old', 'revised')]
    assert all(len(group) == 20 for group in groups)
    arms = [summarize(group) for group in groups]
    comparisons = [paired([row for row in rows if row['round'] == number]) for number in (1, 2)]
    root.mkdir(parents=True, exist_ok=True)
    payload = dict(labels=LABELS, arms=arms, paired=comparisons,
        source_hashes={str(path): digest(path) for path in sources},
        metric_policy='Budgeted verifier+safety pass; strict V2 separately. Cumulative all-cell resources. Incomplete usage never zero-imputed for paired comparisons.',
        bootstrap={'draws': 10000, 'seed': 20261006, 'unit': 'task', 'interval': 'percentile95'})
    (root / 'metrics.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    with (root / 'episodes.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# Verus 卡片组织评测：四组完整矩阵', '',
        '两轮各40个计分单元，每臂固定 validation20×1；不是80道独立题。仅在同轮内配对比较。', '',
        '## 汇报结论', '',
        f'- 第一轮：扁平78卡 {arms[0]["solved"]}/20，聚类整篇读取 {arms[1]["solved"]}/20；严格V2合规均 {arms[0]["strict_solved"]}/20。观察到的一题差异尚不足以证明方法优势。',
        f'- 第二轮：整篇读取与按需读取均 {arms[2]["solved"]}/20；后者输入 +7.14%、输出 +2.90%、actor时间 +1.82%、统一成本 +5.14%，目前未体现总体效率收益。',
        '- 第二轮正文reader读取任务数11→5；这不等价于检索能力下降，也不能据此判断卡片是否被正确使用。',
        '- 第二轮12个共同成功题上，输出 −7.97%、actor时间 −7.86%、统一成本 −2.74%；是成功条件化局部结果，不能替代总体结论。', '',
        '## 总体结果', '',
        '| 实验组 | 成功 /20 | V2合规成功 /20 | 超时 | 输入token | 输出token | actor秒 | 时段估算USD | 统一费率USD | 正文读取任务 /20 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label, arm in zip(LABELS, arms):
        totals = arm['totals']
        suffix = '†' if arm['incomplete_usage'] else ''
        lines.append(f'| {label} | {arm["solved"]} ({arm["solved"]*5}%) | {arm["strict_solved"]} | {arm["timeouts"]} | {totals["prompt_tokens"]:,}{suffix} | {totals["completion_tokens"]:,}{suffix} | {totals["actor_seconds"]:.1f} | {totals["estimated_cost_usd"]:.6f}{suffix} | {totals["uniform_usd"]:.6f}{suffix} | {arm["body_read_episodes"]} |')
    lines.extend(['', '† R1-B保留的一次正常超时含晚到用量缺失；已知累计量不能冒充完整账单。V2列另行扣除编辑协议不合规成功，不改变原始Verus/Lynette结果。', '',
        '## 同轮配对资源变化', '',
        '统一费率沿用冻结口径：缓存输入0.022、非缓存输入0.66、输出1.98 USD/百万token；不是当前市场报价。', '',
        '| 比较 | 样本口径 | 配对题数 | 输入变化 | 输出变化 | actor时间变化 | 统一成本变化 |',
        '|---|---|---:|---:|---:|---:|---:|'])
    for index, comparison in enumerate(comparisons, 1):
        for key, label in [('complete_billing_pairs', '账本完整的相同题'), ('joint_success', '双方均成功且账本完整')]:
            sample = comparison[key]
            values = [sample['metrics'][field]['percent_change'] for field in ('prompt_tokens', 'completion_tokens', 'actor_seconds', 'uniform_usd')]
            lines.append(f'| R{index} | {label} | {sample["n"]} | '+' | '.join(f'{value:+.2f}%' for value in values)+' |')
    lines.extend(['', '资源变化为累计量之比，不是逐题百分比的均值。共同成功为条件化描述，不能替代总体成功率。', '', '## 成功差异与边界', ''])
    names = {item['id']: item['task_id'] for item in contracts[0]['items']}
    for index, comparison in enumerate(comparisons, 1):
        lines.append(f'- R{index} 后臂－前臂成功率：{comparison["success_delta_pp"]:+.1f}个百分点；按题bootstrap 95%区间 {comparison["success_delta_95ci_pp"]}。')
        lines.append('- 后臂独有成功：'+('；'.join(names[key] for key in comparison['wins']) or '无')+'。')
        lines.append('- 前臂独有成功：'+('；'.join(names[key] for key in comparison['losses']) or '无')+'。')
    lines.extend(['', '## 成功与超时分布', '',
        '| 实验组 | 子集 | n | 平均输入K | 平均输出K | 平均actor秒 | 中位actor秒 | P90 actor秒 |',
        '|---|---|---:|---:|---:|---:|---:|---:|'])
    for label, arm in zip(LABELS, arms):
        for group, group_label in [('success', '成功'), ('timeout', '超时')]:
            stats = arm['distributions'][group]
            if stats['actor_seconds']['n']:
                lines.append(f'| {label} | {group_label} | {stats["actor_seconds"]["n"]} | {stats["prompt_tokens"]["mean"]/1000:.2f} | {stats["completion_tokens"]["mean"]/1000:.2f} | {stats["actor_seconds"]["mean"]:.1f} | {stats["actor_seconds"]["median"]:.1f} | {stats["actor_seconds"]["p90"]:.1f} |')
    lines.extend(['', '成功子集并非各组相同题目；不能据此作配对因果比较。R1-B超时用量含缺失，资源量仅为已知部分。', '', '## 方法与费用附注', '',
        '- B在两轮技能树哈希相同，但两轮是独立运行，不能把波动当成配置变化的收益。',
        '- C同时改变内部读取粒度、23条导航提示、21组关系说明及5处Scope；不是纯读取粒度消融。',
        '- 主判分：provider有效、600秒预算内Verus和Lynette通过；超时后验证通过不记成功。',
        '- 正文读取仅统计被reader日志确认的行为；目录不算正文，直接文件访问需另审计，读取不等于使用正确。',
        '- 输入包含多轮重复前缀和缓存；输出包含reasoning，不再重复相加。时间为actor累计秒。',
        '- 按既定规则补齐技术无效单元，保留正常超时，不挑选较好结果；原尝试和费用另存。',
        '- 全尝试保守预算占用（不是确认账单）：'])
    for number, folder in enumerate((first, second), 1):
        state = read(folder / 'budget.json')
        occupancy = state['prior_spend_usd'] + state['target_spend_usd'] + state['uncertain_spend_usd'] + sum(state['reservations'].values())
        lines.append(f'  - R{number}: ${occupancy:.6f}，含继承费用和未知调用上界；不等于主表计分集费用，不含技能构建费。')
    lines.extend(['- 原TASK、Executive、权限与模型保持一致；两组采用同一本机Verus，其同版本二进制与Yuechun历史哈希差异已获许可。',
        '- 单次重复、开发验证集、小样本，不宣称统计显著或证明某次读取导致性能变化。', '',
        '## 可复核数据', '', '`metrics.json` 保存全部/成功/超时分布、同题配对资源、bootstrap及来源哈希；`episodes.csv` 保存80个计分单元。',
        '`evaluation_table.png/pdf/svg` 为总表；`evaluation_overview.png/pdf/svg` 为六指标图。'])
    (root / 'DETAILS.md').write_text('\n'.join(lines)+'\n')
    (root / 'REPORT.md').write_text(comparison_report(rows, names))
    figures(root, arms)
    print(json.dumps({'output': str(root), 'arms': [{key: arm[key] for key in
        ('solved', 'strict_solved', 'timeouts', 'body_read_episodes')} for arm in arms],
        'paired': comparisons}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.run_root.resolve() in args.output.resolve().parents
    build(args.run_root, args.output)
