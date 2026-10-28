## TC-004

### Purpose

Exercise workloads that require the synthetic large-memory capability.

### Notes

Compatibility is derived from capabilities rather than manually maintained lists.

### Derived fields

<!-- catalog:derived:start TC-004 -->
- **Supported GPUs:** `GPU-B`, `GPU-C`
- **Timeout:** `49 s`
- **Pass rate:** `degraded` (`93.33%`)
- **Last measurement:** `2025-12-14T12:00:00Z` (`fresh`)
<!-- catalog:derived-data
{
  "fields": {
    "last_measurement": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "max(executed_at); fresh_if_age_days<=30",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "fresh",
      "value": "2025-12-14T12:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 93.33,
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "requires_each_gpu_samples>=10; min_gpu(passed / samples * 100), round_half_up(2); healthy>=95, degraded>=80",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": "degraded"
    },
    "supported_gpus": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "required_capabilities subset_of gpu.capabilities",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": [
        "GPU-B",
        "GPU-C"
      ]
    },
    "timeout_seconds": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "requires_each_gpu_samples>=10; ceil(max_gpu(nearest_rank_p95(duration_seconds)) * 1.25)",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": 49
    }
  },
  "format_version": "1.0"
  "testcase_id": "TC-004"
}
-->
<!-- catalog:derived:end TC-004 -->

### Summary

Large-memory coverage is currently limited to GPUs that advertise the capability.
