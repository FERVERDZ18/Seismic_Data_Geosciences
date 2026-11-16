#!/usr/bin/env python3
"""Run unmodified, commit-pinned GEM catalogue merging on a shared pilot CSV.

This adapter only translates records and exports GEM's actual merged origins.
It does not reproduce or replace GEM's association algorithm. Source snapshots,
licence, dependency lock and receipts live in the private pilot output folder.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
import warnings

GEM_COMMIT = "d13e63bebedcc6788e0ec88e8632957b749d3b60"
DEFAULT_ENV = Path("outputs/ssn_usgs_pilot_2026-11-15/gem_env")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, columns, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def pick(row, *keys):
    return next((row[k].strip() for k in keys if row.get(k, "").strip()), "")


def number(value, optional=False):
    if not value and optional:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric field")
    return result


def parse_time(row):
    value = pick(row, "time_utc", "time", "datetime_utc")
    if value:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("time must include an explicit UTC offset")
        return stamp.astimezone(dt.timezone.utc)
    # This alternate schema is explicit UTC by the adapter input contract.
    second = float(row["second"])
    return dt.datetime(*(int(row[k]) for k in
                         ("year", "month", "day", "hour", "minute")),
                       tzinfo=dt.timezone.utc) + dt.timedelta(seconds=second)


def read_records(path):
    records, rejected, seen = [], [], set()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for index, row in enumerate(csv.DictReader(stream), 2):
            rid = pick(row, "record_id", "recordID")
            source = pick(row, "source", "Agency", "agency").upper()
            event_id = pick(row, "event_id", "eventID")
            if not rid:
                raise ValueError(f"line {index}: record_id is required; no invented IDs")
            if rid in seen:
                raise ValueError(f"line {index}: duplicate record_id {rid}")
            seen.add(rid)
            try:
                stamp = parse_time(row)
                lat = number(pick(row, "latitude"))
                lon = number(pick(row, "longitude"))
                magnitude = number(pick(row, "magnitude", "mag", "value"))
                depth = number(pick(row, "depth_km", "depth"), optional=True)
                if not source or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError("invalid source or coordinates")
                if stamp.year <= 1000 or magnitude <= 1.0:
                    raise ValueError("outside GEM threshold matrix domain (year>1000, M>1)")
                fraction = re.search(r"\.(\d+)", pick(row, "time_utc", "time", "datetime_utc"))
                submicrosecond = bool(fraction and len(fraction[1]) > 6
                                      and any(c != "0" for c in fraction[1][6:]))
                records.append(dict(record_id=rid, source=source, event_id=event_id,
                                    time=stamp, latitude=lat, longitude=lon,
                                    depth_km=depth, magnitude=magnitude,
                                    submicrosecond_precision_lost=submicrosecond,
                                    magnitude_type=pick(row, "magnitude_type",
                                                        "magnitudeType", "magType")))
            except (KeyError, ValueError, OverflowError) as error:
                rejected.append(dict(record_id=rid, line=index, reason=str(error)))
    return records, rejected


def import_gem(env):
    """Import downloaded official bytes without editing them or global packages."""
    source = env / "official_source"
    provenance = json.loads((env / "source_provenance.json").read_text(encoding="utf-8-sig"))
    if provenance["commit"] != GEM_COMMIT:
        raise ValueError("unexpected GEM source commit")
    for item in provenance["files"]:
        if sha256(source / item["path"]) != item["sha256"]:
            raise ValueError(f"official source changed: {item['path']}")
    os.environ.setdefault("MPLCONFIGDIR", str((env / "mpl_cache").resolve()))
    os.environ.setdefault("OQ_DATADIR", str((env / "oq_data").resolve()))
    sys.path.insert(0, str(source.resolve()))
    from openquake.cat.isf_catalogue import (ISFCatalogue, Event, Origin,
                                             Location, Magnitude)
    from openquake.hazardlib.geo.geodetic import geodetic_distance
    return ISFCatalogue, Event, Origin, Location, Magnitude, geodetic_distance


def make_catalogue(records, source, api):
    Catalogue, Event, Origin, Location, Magnitude, _ = api
    events = []
    for row in records:
        if row["source"] != source:
            continue
        rid, stamp = row["record_id"], row["time"]
        location = Location(rid, row["longitude"], row["latitude"], row["depth_km"])
        origin = Origin(rid, stamp.date(), stamp.time().replace(tzinfo=None),
                        location, source, is_prime=True)
        # GEM's documented unknown scale UK is retained only inside its class.
        # Original missing type remains missing in the input CSV and provenance.
        magnitude = Magnitude(rid, rid, row["magnitude"], source,
                              scale=row["magnitude_type"] or None)
        event = Event(rid, [origin], [magnitude])
        event.assign_magnitudes_to_origins()
        events.append(event)
    if not events:
        raise ValueError(f"empty source {source}")
    return Catalogue(source, f"Pilot {source}; raw reported magnitude", events)


def run(args):
    start = time.perf_counter()
    env, out = args.gem_env.resolve(), args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records, rejected = [], []
    for input_path in args.input:
        file_records, file_rejected = read_records(input_path)
        records.extend(file_records)
        rejected.extend(file_rejected)
    if len({row["record_id"] for row in records}) != len(records):
        raise ValueError("record_id repeated across input files")
    other = sorted({row["source"] for row in records} -
                   {args.host_source, args.guest_source})
    if other:
        raise ValueError(f"unexpected input sources {other}")
    api = import_gem(env)
    host = make_catalogue(records, args.host_source, api)
    guest = make_catalogue(records, args.guest_source, api)
    host_count, guest_count = len(host.events), len(guest.events)
    original_host_ids = {event.id for event in host.events}
    record_map = {row["record_id"]: row for row in records}
    premerge = time.perf_counter()
    host._create_spatial_index()
    with (out / "gem_stdout_stderr.log").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log), \
                warnings.catch_warnings():
            warnings.simplefilter("always")
            common, doubts = host.add_external_idf_formatted_catalogue(
                guest, ll_deltas=float(args.distance_km),
                delta_t=float(args.time_seconds), use_kms=True, use_ids=False,
                buff_ll=0.0, buff_t=dt.timedelta(seconds=0),
                logfle=str(out / "gem_official_merge.log") if args.official_log else False)
    merging_seconds = time.perf_counter() - premerge
    pairs, members = [], []
    for event in host.events:
        for origin in event.origins:
            members.append(dict(gem_event_id=event.id, record_id=origin.id,
                                source=origin.author, is_prime=bool(origin.is_prime)))
        # Every association below comes from the actual GEM merged-origin object.
        # The adapter never applies its own space/time matching decision.
        a = [o for o in event.origins if o.author == "SSN"]
        b = [o for o in event.origins if o.author == "USGS"]
        for ssn in a:
            for usgs in b:
                sr, ur = record_map[ssn.id], record_map[usgs.id]
                distance = float(api[-1](sr["longitude"], sr["latitude"],
                                         ur["longitude"], ur["latitude"]))
                pairs.append(dict(ssn_record_id=ssn.id, usgs_record_id=usgs.id,
                                  time_delta_seconds=abs((sr["time"] - ur["time"]).total_seconds()),
                                  gem_distance_km=distance))
    pairs.sort(key=lambda row: (row["ssn_record_id"], row["usgs_record_id"]))
    write_csv(out / "pairs.csv", ["ssn_record_id", "usgs_record_id",
                                 "time_delta_seconds", "gem_distance_km"], pairs)
    write_json(out / "pairs.json", pairs)
    write_csv(out / "memberships.csv", ["gem_event_id", "record_id", "source",
                                       "is_prime"], members)
    write_csv(out / "excluded.csv", ["record_id", "line", "reason"], rejected)
    grouped_guest = {p["usgs_record_id"] if args.guest_source == "USGS"
                     else p["ssn_record_id"] for p in pairs}
    decisions = [dict(record_id=row["record_id"],
                      decision="associated_by_GEM" if row["record_id"] in grouped_guest
                      else "retained_as_new_by_GEM")
                 for row in records if row["source"] == args.guest_source]
    write_csv(out / "guest_decisions.csv", ["record_id", "decision"], decisions)
    if len(common) != len(pairs):
        raise ValueError("GEM common indexes and exported associations differ")
    if len(members) != host_count + guest_count:
        raise ValueError("input origins were lost or repeated in GEM output")
    summary = dict(
        status="executed_official_GEM", utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        gem_commit=GEM_COMMIT,
        inputs=[dict(path=str(p.resolve()), sha256=sha256(p)) for p in args.input],
        adapter_sha256=sha256(__file__), host_source=args.host_source,
        guest_source=args.guest_source, host_input=host_count, guest_input=guest_count,
        excluded=len(rejected), associated_pairs=len(pairs), retained_groups=len(host.events),
        new_guest_events=len(host.events) - len(original_host_ids),
        time_seconds=args.time_seconds, distance_km=args.distance_km,
        official_api="ISFCatalogue._create_spatial_index; add_external_idf_formatted_catalogue",
        official_module_path=str(sys.modules["openquake.cat.isf_catalogue"].__file__),
        use_kms=True, use_ids=False, buff_ll=0, buff_t_seconds=0,
        threshold_semantics="strict time_delta < time_seconds AND GEM geodetic_distance < distance_km",
        ordering="input CSV order preserved within each source; host=SSN by default",
        candidate_semantics="first eligible Rtree candidate; not globally optimal; same magnitude agency cannot be added twice",
        prefilter="GEM uses a fixed +/-2 degree bounding box before geodetic distance",
        uncertainty="no independent physical-event truth; associations are algorithm output, not accuracy",
        magnitude="reported values retained; no conversion or magnitude difference matching; missing type becomes GEM UK internally",
        time_mapping="GEM datetime supports microseconds; raw input CSV retained without changes",
        records_with_nonzero_submicroseconds=sum(r["submicrosecond_precision_lost"] for r in records),
        doubts=doubts, python=sys.version, platform=platform.platform(),
        engine_version=importlib.metadata.version("openquake.engine"),
        merging_seconds=merging_seconds, total_seconds=time.perf_counter() - start)
    write_json(out / "run.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "host_input", "guest_input",
                                             "associated_pairs", "retained_groups",
                                             "total_seconds")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--gem-env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--host-source", default="SSN")
    parser.add_argument("--guest-source", default="USGS")
    parser.add_argument("--time-seconds", type=float, default=30)
    parser.add_argument("--distance-km", type=float, default=50)
    parser.add_argument("--official-log", action="store_true")
    args = parser.parse_args()
    if args.time_seconds <= 0 or not 0 < args.distance_km <= 100:
        parser.error("require positive time and 0<distance<=100km for this Mexican pilot")
    try:
        run(args)
    except Exception as error:
        args.outdir.mkdir(parents=True, exist_ok=True)
        write_json(args.outdir / "failure.json", dict(
            status="failed", error=repr(error), gem_commit=GEM_COMMIT,
            utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        raise


if __name__ == "__main__":
    main()
