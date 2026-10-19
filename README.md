# AutoScale Load Tester (MVP)

A small async HTTP load tester that runs staged concurrency levels and reports request count, errors, throughput, and latency percentiles. It does not automatically scale infrastructure; it scales test concurrency only.

## Run
```bash
python load_test.py https://your-authorized-host.example --duration 10 --concurrency 5 --stages 1,3,5
```
Use only against systems you own or have explicit permission to test. The runner intentionally limits concurrency to 100 and duration to 120 seconds.
