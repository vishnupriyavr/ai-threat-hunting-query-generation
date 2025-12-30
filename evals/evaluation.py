"""Evaluation framework for Agentic Threat Hunting

This module provides utilities to compute evaluation metrics from
the assignment outputs (`assignment/hypotheses_outcomes.json`) and
to produce a markdown report compatible with `EVALUATION_REPORT.md`.

Usage:
  python evaluation.py --outcomes assignment/hypotheses_outcomes.json \
	  --hypotheses assignment/hypotheses.json --out report.md

The script computes:
  - Per-hypothesis result counts and simple success/flag heuristics
  - Aggregate metrics: Query Success Rate, Tool Call Accuracy (heuristic),
	Trajectory Efficiency (if available), Schema Faithfulness, Avg. Latency (if available)

The framework is intentionally heuristic-driven so it can run on the
available assignment outputs. For richer metrics (latency, reasoning loops,
tool-call correctness) provide a detailed `results.json` with per-hypothesis fields.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple


CANONICAL_CLOUDTRAIL_FIELDS = set(
	[
		"eventID",
		"eventTime",
		"eventName",
		"eventSource",
		"awsRegion",
		"sourceIPAddress",
		"userAgent",
		"errorCode",
		"errorMessage",
		"userIdentityuserName",
		"userIdentityarn",
		"requestParametersinstanceType",
	]
)


def load_json(path: str) -> Any:
	with open(path, 'r') as f:
		return json.load(f)


def parse_outcomes(outcomes: List[Dict]) -> Dict[str, Dict[str, Any]]:
	"""Parse the assignment/hypotheses_outcomes.json structure.

	The outcomes file is a list of objects where each object maps a hypothesis id
	to a dict of columns mapping event records. This function flattens that to
	a mapping from hypothesis id -> outcome dict.
	"""
	results = {}
	for item in outcomes:
		if not isinstance(item, dict):
			continue
		for hid, data in item.items():
			results[str(hid)] = data
	return results


def summarize_hypothesis(hid: str, data: Dict[str, Any], hypothesis_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	"""Compute a per-hypothesis summary based on outcome aggregations.

	Heuristics applied:
	  - result_count: inferred from the largest value-len among fields
	  - success: True if result_count > 0
	  - event_names: top eventName values if present
	  - schema_faithfulness: fraction of reported fields that are canonical
	  - hallucination_rate: fraction of fields not in canonical set
	"""
	cols = list(data.keys())
	# estimate result counts: pick a representative field (eventID|eventTime|eventName)
	representative = None
	for candidate in ['eventID', 'eventTime', 'eventName', 'sourceIPAddress']:
		if candidate in data:
			representative = candidate
			break
	if representative is None and cols:
		representative = cols[0]

	result_count = 0
	if representative and representative in data and isinstance(data[representative], dict):
		result_count = len(data[representative])

	event_names = []
	if 'eventName' in data and isinstance(data['eventName'], dict):
		# collect unique event names
		event_names = list(set(data['eventName'].values()))

	# schema faithfulness: fraction of columns in canonical list
	reported_fields = set(cols)
	canonical = reported_fields & CANONICAL_CLOUDTRAIL_FIELDS
	if reported_fields:
		schema_faithfulness = len(canonical) / len(reported_fields)
		hallucination_rate = 1 - schema_faithfulness
	else:
		schema_faithfulness = 0.0
		hallucination_rate = 1.0

	# Tool call accuracy (heuristic): check event names against expected mapping
	expected = None
	if hypothesis_meta:
		expected = hypothesis_meta.get('expected_event')

	tool_call_ok = None
	if expected and event_names:
		# if any expected event appears in outcome event_names mark as correct
		tool_call_ok = any(expected.lower() in en.lower() for en in event_names)

	# collect extras
	summary = {
		'hypothesis_id': hid,
		'hypothesis_name': hypothesis_meta.get('name') if hypothesis_meta else None,
		'result_count': result_count,
		'success': result_count > 0,
		'event_names': event_names,
		'schema_faithfulness': round(schema_faithfulness * 100, 2),  # percent
		'hallucination_rate': round(hallucination_rate * 100, 2),
		'tool_call_ok': tool_call_ok,
	}
	return summary


def compute_aggregates(per_hypo: List[Dict[str, Any]]) -> Dict[str, Any]:
	"""Compute overall metrics used in EVALUATION_REPORT.md"""
	n = len(per_hypo)
	if n == 0:
		return {}

	q_success = sum(1 for h in per_hypo if h.get('success')) / n
	# tool call accuracy: average of tool_call_ok where present; fallback to 0.0
	tool_vals = [1.0 if h.get('tool_call_ok') else 0.0 for h in per_hypo if h.get('tool_call_ok') is not None]
	tool_accuracy = (sum(tool_vals) / len(tool_vals)) if tool_vals else None

	# Trajectory efficiency / avg latency not available in outcomes; leave None
	avg_latency = None
	traj_eff = None

	# Schema faithfulness: average percent
	sf_vals = [h.get('schema_faithfulness', 0.0) for h in per_hypo]
	schema_faithfulness = sum(sf_vals) / len(sf_vals)

	# Avg result count
	avg_result_count = sum(h.get('result_count', 0) for h in per_hypo) / n

	aggregates = {
		'query_success_rate': round(q_success * 100, 2),
		'tool_call_accuracy': round(tool_accuracy, 2) if tool_accuracy is not None else None,
		'trajectory_efficiency': traj_eff,
		'schema_faithfulness': round(schema_faithfulness, 2),
		'avg_latency': avg_latency,
		'avg_result_count': round(avg_result_count, 2),
	}
	return aggregates


def generate_markdown_report(aggregates: Dict[str, Any], per_hypo: List[Dict[str, Any]], out_path: Optional[str] = None) -> str:
	"""Render a markdown string for the evaluation report.

	If `out_path` is provided, writes the markdown to the file.
	"""
	lines = []
	lines.append('## Overall Metrics and Scores')
	lines.append('')
	lines.append('| Metric Category | Metric Name | Score / Value | Definition |')
	lines.append('|---|---|---|---|')
	lines.append(f"| Accuracy | Query Success Rate | {aggregates.get('query_success_rate', 'N/A')}% | Proportion of hypotheses that returned non-empty results. |")
	tca = aggregates.get('tool_call_accuracy', 'N/A')
	if isinstance(tca, float):
		tca_str = f"{tca}"
	else:
		tca_str = 'N/A'
	lines.append(f"| Precision | Tool Call Accuracy | {tca_str} | Heuristic: whether the expected event name appeared in outcomes. |")
	te = aggregates.get('trajectory_efficiency', 'N/A')
	lines.append(f"| Reasoning | Trajectory Efficiency | {te} | Average reasoning loops (if available). |")
	lines.append(f"| Groundedness | Schema Faithfulness | {aggregates.get('schema_faithfulness', 'N/A')}% | Percentage of reported fields that match canonical CloudTrail fields. |")
	lines.append(f"| Efficiency | Avg. Latency | {aggregates.get('avg_latency', 'N/A')} | Average time from hypothesis input to final query (if available). |")
	lines.append('')
	lines.append('## Per-Hypothesis Breakdown')
	lines.append('')
	lines.append('| ID | Hypothesis Name | Status | Schema Faithfulness (%) | Result Count | Tool Call OK |')
	lines.append('|---|---|---|---:|---:|---:|')
	for h in per_hypo:
		status = 'Success' if h.get('success') else 'No Results'
		lines.append(f"| {h.get('hypothesis_id')} | {h.get('hypothesis_name') or ''} | {status} | {h.get('schema_faithfulness')} | {h.get('result_count')} | {h.get('tool_call_ok')} |")

	md = '\n'.join(lines)
	if out_path:
		with open(out_path, 'w') as f:
			f.write(md)
	return md


def save_evaluation_results(per_hypo: List[Dict[str, Any]], meta_map: Dict[str, Any], out_path: str = 'evaluation_results.json') -> None:
	"""Save per-hypothesis evaluation results to a JSON file.

	The format mirrors the hypotheses_outcomes.json style (a list of objects keyed
	by hypothesis id) but contains an `evaluation` object for each hypothesis.
	"""
	out_list = []
	for h in per_hypo:
		hid = str(h.get('hypothesis_id'))
		meta = meta_map.get(hid, {})
		entry = {
			hid: {
				'meta': meta,
				'evaluation': {
					'success': h.get('success'),
					'result_count': h.get('result_count'),
					'schema_faithfulness_pct': h.get('schema_faithfulness'),
					'hallucination_rate_pct': h.get('hallucination_rate'),
					'tool_call_ok': h.get('tool_call_ok'),
					'event_names': h.get('event_names'),
				}
			}
		}
		out_list.append(entry)

	with open(out_path, 'w') as f:
		json.dump(out_list, f, indent=2)

	print(f"Wrote evaluation results to {out_path}")


def save_final_outcomes(parsed_outcomes: Dict[str, Any], out_path: str = 'final_hypotheses_outcomes.json') -> None:
	"""Save parsed outcomes back to the hypotheses_outcomes.json style (list of single-key objects).

	This mirrors the input format so downstream tools (or the crew) can consume the final output.
	"""
	out_list = []
	# Keep a stable order by sorting numeric ids when possible
	try:
		keys = sorted(parsed_outcomes.keys(), key=lambda k: int(k))
	except Exception:
		keys = list(parsed_outcomes.keys())

	for k in keys:
		out_list.append({k: parsed_outcomes[k]})

	with open(out_path, 'w') as f:
		json.dump(out_list, f, indent=2)

	print(f"Wrote final outcomes in hypotheses_outcomes.json format to {out_path}")


def rows_to_column_mapping(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
	"""Convert a list of row dicts into a column->(id->value) mapping.

	If a row contains 'eventID', we use that as the record key; otherwise
	we assign incremental string keys starting at '0'.
	"""
	cols: Dict[str, Dict[str, Any]] = {}
	for idx, row in enumerate(rows):
		record_key = None
		if 'eventID' in row and row['eventID'] is not None:
			record_key = str(row['eventID'])
		else:
			record_key = str(idx)
		for k, v in row.items():
			if k not in cols:
				cols[k] = {}
			cols[k][record_key] = v
	return cols


def export_agent_outputs_to_hypotheses_outcomes(agent_outputs: Any, out_path: str = 'final_hypotheses_outcomes.json') -> None:
	"""Export agent run outputs into the hypotheses_outcomes.json structure.

	Expected `agent_outputs` format (two supported options):
	  1) Dict[str, List[Dict]]: mapping hypothesis_id -> list of row dicts
	  2) List[ { 'hypothesis_id': id, 'rows': [ {...}, ... ] }, ... ]

	The function normalizes either format and writes a list of single-key objects
	where each key is the hypothesis id and the value is a dict mapping column
	names to maps of record_id -> value (same as `hypotheses_outcomes.json`).
	"""
	normalized: Dict[str, List[Dict[str, Any]]] = {}

	# normalize input formats
	if isinstance(agent_outputs, dict):
		# assume mapping hypothesis_id -> rows
		for k, v in agent_outputs.items():
			normalized[str(k)] = list(v)
	elif isinstance(agent_outputs, list):
		for item in agent_outputs:
			if isinstance(item, dict) and 'hypothesis_id' in item and 'rows' in item:
				normalized[str(item['hypothesis_id'])] = list(item['rows'])
			else:
				raise ValueError('Unsupported list item format in agent_outputs')
	else:
		raise ValueError('Unsupported agent_outputs format')

	out_list = []
	for hid, rows in normalized.items():
		cols = rows_to_column_mapping(rows)
		out_list.append({hid: cols})

	with open(out_path, 'w') as f:
		json.dump(out_list, f, indent=2, default=str)

	print(f"Exported agent outputs to {out_path} in hypotheses_outcomes.json format")


def add_or_update_outcome_metadata(hypothesis_id: str, metadata: Dict[str, Any], outcomes_path: str = 'assignment/hypotheses_outcomes.json') -> None:
	"""Add or update metadata object for a hypothesis in the outcomes file.

	The outcomes file format is a list of single-key objects: [{"1": { ... }}, {"2": { ... }}].
	This function will add a `meta` key under the hypothesis' dict and merge provided
	metadata into it. If the hypothesis id does not exist, it will append a new entry.
	"""
	try:
		with open(outcomes_path, 'r') as f:
			data = json.load(f)
	except FileNotFoundError:
		data = []

	found = False
	for item in data:
		if isinstance(item, dict) and str(hypothesis_id) in item:
			hdata = item[str(hypothesis_id)]
			meta = hdata.get('meta', {})
			meta.update(metadata)
			hdata['meta'] = meta
			found = True
			break

	if not found:
		# create a minimal entry with meta only
		data.append({str(hypothesis_id): {'meta': metadata}})

	with open(outcomes_path, 'w') as f:
		json.dump(data, f, indent=2, default=str)

	print(f"Updated outcomes file at {outcomes_path} with meta for hypothesis {hypothesis_id}")


def persist_confidence(hypothesis_id: str, score: float, explanation: str, outcomes_path: str = 'assignment/hypotheses_outcomes.json') -> None:
	"""Convenience wrapper to persist a confidence score and explanation for a hypothesis."""
	add_or_update_outcome_metadata(str(hypothesis_id), {'confidence': float(score), 'confidence_explanation': explanation}, outcomes_path=outcomes_path)


def add_or_update_outcome_rows(hypothesis_id: str, rows: List[Dict[str, Any]], outcomes_path: str = 'assignment/hypotheses_outcomes.json') -> None:
	"""Add or update the outcome rows (converted to columns mapping) for a hypothesis.

	This will replace any existing column mapping for the hypothesis with the provided rows mapping.
	"""
	cols = rows_to_column_mapping(rows)
	try:
		with open(outcomes_path, 'r') as f:
			data = json.load(f)
	except FileNotFoundError:
		data = []

	found = False
	for item in data:
		if isinstance(item, dict) and str(hypothesis_id) in item:
			# merge existing meta if present, but replace the columns mapping
			meta = item[str(hypothesis_id)].get('meta')
			item[str(hypothesis_id)] = cols
			if meta is not None:
				item[str(hypothesis_id)]['meta'] = meta
			found = True
			break

	if not found:
		data.append({str(hypothesis_id): cols})

	with open(outcomes_path, 'w') as f:
		json.dump(data, f, indent=2, default=str)

	print(f"Updated outcomes file at {outcomes_path} with rows for hypothesis {hypothesis_id}")


def export_agent_outputs_to_files(agent_outputs: Any, out_dir: str = 'final_hypotheses_outcomes') -> None:
	"""Export each hypothesis' outputs into a separate JSON file in out_dir.

	Files are named `<hypothesis_id>.json` and contain a single object keyed by the hypothesis id
	with the columns mapping (same as `hypotheses_outcomes.json` element format).
	"""
	import os
	os.makedirs(out_dir, exist_ok=True)

	# Normalize same as before
	normalized: Dict[str, List[Dict[str, Any]]] = {}
	if isinstance(agent_outputs, dict):
		normalized = {str(k): list(v) for k, v in agent_outputs.items()}
	elif isinstance(agent_outputs, list):
		for item in agent_outputs:
			if isinstance(item, dict) and 'hypothesis_id' in item and 'rows' in item:
				normalized[str(item['hypothesis_id'])] = list(item['rows'])
			else:
				raise ValueError('Unsupported list item format in agent_outputs')
	else:
		raise ValueError('Unsupported agent_outputs format')

	for hid, rows in normalized.items():
		cols = rows_to_column_mapping(rows)
		out_path = os.path.join(out_dir, f"{hid}.json")
		with open(out_path, 'w') as f:
			json.dump([{hid: cols}], f, indent=2, default=str)
		print(f"Wrote per-hypothesis file: {out_path}")


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument('--outcomes', default='assignment/hypotheses_outcomes.json')
	parser.add_argument('--hypotheses', default='assignment/hypotheses.json')
	parser.add_argument('--out', default='EVALUATION_REPORT_generated.md')
	parser.add_argument('--eval_out', default='evaluation_results.json', help='Save per-hypothesis evaluation results (JSON)')
	parser.add_argument('--final_out', default=None, help='Write final outcomes in hypotheses_outcomes.json format')
	parser.add_argument('--agent_inputs', default=None, help='Path to agent run outputs (JSON) to export to hypotheses_outcomes format')
	parser.add_argument('--export_out', default='final_hypotheses_outcomes.json', help='Output path when exporting agent outputs')
	parser.add_argument('--export_dir', default=None, help='If provided, export each hypothesis to a separate JSON file in this directory')
	args = parser.parse_args(argv)

	outcomes_raw = load_json(args.outcomes)
	hypotheses_meta_list = load_json(args.hypotheses)
	# build meta mapping
	meta_map = {str(h.get('id')): h for h in hypotheses_meta_list}

	parsed = parse_outcomes(outcomes_raw)
	per_hypo = []
	for hid, data in parsed.items():
		meta = meta_map.get(str(hid), {})
		# enrich meta with expected events for heuristic checking
		if meta.get('id') == '5':
			meta['expected_event'] = 'GetCallerIdentity'
		if meta.get('id') == '1':
			meta['expected_event'] = 'ConsoleLogin'
		if meta.get('id') == '4':
			meta['expected_event'] = 'AccessDenied'
		summary = summarize_hypothesis(hid, data, hypothesis_meta=meta)
		per_hypo.append(summary)

	aggregates = compute_aggregates(per_hypo)
	md = generate_markdown_report(aggregates, per_hypo, out_path=args.out)
	print(f"Wrote evaluation report to {args.out}")

	# Save machine-readable evaluation results (per hypothesis)
	save_evaluation_results(per_hypo, meta_map, out_path=args.eval_out)
	# Optionally write the final outcomes in the same format as hypotheses_outcomes.json
	if args.final_out:
		save_final_outcomes(parsed, out_path=args.final_out)

	# Export agent run outputs (if provided) to hypotheses_outcomes.json format
	if args.agent_inputs:
		agent_data = load_json(args.agent_inputs)
		export_agent_outputs_to_hypotheses_outcomes(agent_data, out_path=args.export_out)
		if args.export_dir:
			export_agent_outputs_to_files(agent_data, out_dir=args.export_dir)
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
