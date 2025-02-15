import timeit
from pathlib import Path
from typing import List

from fixtures.benchmark_fixture import PgBenchRunResult
from fixtures.compare_fixtures import NeonCompare
from performance.test_perf_pgbench import utc_now_timestamp

# -----------------------------------------------------------------------
# Start of `test_compare_child_and_root_*` tests
# -----------------------------------------------------------------------

# `test_compare_child_and_root_*` tests compare the performance of a branch and its child branch(s).
# A common pattern in those tests is initializing a root branch then creating a child branch(s) from the root.
# Each test then runs a similar workload for both child branch and root branch. Each measures and reports
# some latencies/metrics during the workload for performance comparison between a branch and its ancestor.


def test_compare_child_and_root_pgbench_perf(neon_compare: NeonCompare):
    env = neon_compare.env
    pg_bin = neon_compare.pg_bin

    def run_pgbench_on_branch(branch: str, cmd: List[str]):
        run_start_timestamp = utc_now_timestamp()
        t0 = timeit.default_timer()
        out = pg_bin.run_capture(
            cmd,
        )
        run_duration = timeit.default_timer() - t0
        run_end_timestamp = utc_now_timestamp()

        stdout = Path(f"{out}.stdout").read_text()

        res = PgBenchRunResult.parse_from_stdout(
            stdout=stdout,
            run_duration=run_duration,
            run_start_timestamp=run_start_timestamp,
            run_end_timestamp=run_end_timestamp,
        )
        neon_compare.zenbenchmark.record_pg_bench_result(branch, res)

    env.neon_cli.create_branch("root")
    pg_root = env.postgres.create_start("root")
    pg_bin.run_capture(["pgbench", "-i", pg_root.connstr(), "-s10"])

    env.neon_cli.create_branch("child", "root")
    pg_child = env.postgres.create_start("child")

    run_pgbench_on_branch("root", ["pgbench", "-c10", "-T10", pg_root.connstr()])
    run_pgbench_on_branch("child", ["pgbench", "-c10", "-T10", pg_child.connstr()])


def test_compare_child_and_root_write_perf(neon_compare: NeonCompare):
    env = neon_compare.env
    env.neon_cli.create_branch("root")
    pg_root = env.postgres.create_start("root")

    pg_root.safe_psql(
        "CREATE TABLE foo(key serial primary key, t text default 'foooooooooooooooooooooooooooooooooooooooooooooooooooo')",
    )

    env.neon_cli.create_branch("child", "root")
    pg_child = env.postgres.create_start("child")

    with neon_compare.record_duration("root_run_duration"):
        pg_root.safe_psql("INSERT INTO foo SELECT FROM generate_series(1,1000000)")
    with neon_compare.record_duration("child_run_duration"):
        pg_child.safe_psql("INSERT INTO foo SELECT FROM generate_series(1,1000000)")


def test_compare_child_and_root_read_perf(neon_compare: NeonCompare):
    env = neon_compare.env
    env.neon_cli.create_branch("root")
    pg_root = env.postgres.create_start("root")

    pg_root.safe_psql_many(
        [
            "CREATE TABLE foo(key serial primary key, t text default 'foooooooooooooooooooooooooooooooooooooooooooooooooooo')",
            "INSERT INTO foo SELECT FROM generate_series(1,1000000)",
        ]
    )

    env.neon_cli.create_branch("child", "root")
    pg_child = env.postgres.create_start("child")

    with neon_compare.record_duration("root_run_duration"):
        pg_root.safe_psql("SELECT count(*) from foo")
    with neon_compare.record_duration("child_run_duration"):
        pg_child.safe_psql("SELECT count(*) from foo")


# -----------------------------------------------------------------------
# End of `test_compare_child_and_root_*` tests
# -----------------------------------------------------------------------
