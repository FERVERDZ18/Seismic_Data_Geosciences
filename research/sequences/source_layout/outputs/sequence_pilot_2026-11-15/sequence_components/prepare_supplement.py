"""Reshape already computed descriptors for manuscript supplement tables."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_csv(name):
    with (HERE/name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def save(name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (HERE/name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    report = json.loads((HERE/"COMPONENT_EVIDENCE.json").read_text(encoding="utf-8"))
    rows = []
    for key, summary in report["component_summaries"].items():
        method, regime, source = key.split("_", 2)
        row = {"method": method, "regime": regime, "source": source,
               "n_fields": 1 if method == "GK" else 20,
               "aggregation": "deterministic" if method == "GK" else "mean_min_max_of_per_field_statistics"}
        for statistic, value in summary.items():
            row.update({f"{statistic}_{suffix}": number for suffix, number in
                        (value.items() if method == "NN" else [("mean", value), ("min", value), ("max", value)])})
        rows.append(row)
    save("supplement_S1_components.csv", rows)
    rows = []
    for method, result in report["partition_concordance"].items():
        for comparison, outcome in result["comparisons"].items():
            row = {"method": method, "comparison": comparison,
                   "n_same_pairs": result["n_same_candidate_pairs"],
                   "n_fields": 1 if method == "GK" else 20}
            for statistic in ["ARI", "role_agreement"]:
                value = outcome[statistic]
                row.update({f"{statistic}_{suffix}": number for suffix, number in
                    (value.items() if method == "NN" else [("mean", value), ("min", value), ("max", value)])})
            rows.append(row)
    save("supplement_S2_partition_concordance.csv", rows)
    high_metadata = {int(row["pair_index_in_original_2989"]): row for row in
                     load_csv("high_magnitude_candidate_pairs.csv")}
    rows = []
    for row in load_csv("high_magnitude_components_by_field.csv"):
        source = row["case"].split("_", 1)[1]
        metadata = high_metadata[int(row["pair_index"])]
        rows.append({"audit_kind": "all_candidate_pairs_M_ge_6_in_either_source",
                     **row, "source": source,
                     **{key: metadata[key] for key in metadata if key != "pair_index_in_original_2989"}})
    trace = report["deterministic_GK_trace"]
    for row in load_csv("GK_trace_members.csv"):
        for regime in ["B", "C"]:
            is_member = row[f"member_of_chosen_{regime}_component"] == "True"
            outcome = trace["regimes"][regime]
            rows.append({"audit_kind": "deterministic_GK_trace_member", "method": "GK",
                "case": f"{regime}_ssn", "source": "ssn", "record_id": row["record_id"],
                "ssn_time_utc": row["time_utc"], "ssn_magnitude": row["magnitude"],
                "ssn_magnitude_type": row["magnitude_type"],
                "role": outcome["role"] if row["record_id"] == trace["chosen_record"]["record_id"] else "associated" if is_member else "absent_from_C_cohort",
                "original_group": outcome["original_group"] if is_member else "",
                "component_size": outcome["component_size"] if is_member else "",
                "observed_duration_days": outcome["observed_duration_days"] if is_member else "",
                "member_of_chosen_component": is_member,
                "present_in_C_cohort": row["present_in_C_cohort"],
                "removed_from_B_context": row["removed_from_B_context"]})
    save("supplement_S3_trace_and_large_pairs.csv", rows)
    receipt = {"source_report_sha256": hashlib.sha256((HERE/"COMPONENT_EVIDENCE.json").read_bytes()).hexdigest(),
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "outputs": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted(HERE.glob("supplement_S*.csv"))}}
    (HERE/"SUPPLEMENT_RECEIPT.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
