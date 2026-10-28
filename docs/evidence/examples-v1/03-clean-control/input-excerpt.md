## TC-001

### Purpose

Verify the baseline compute path required by every synthetic vGPU workload.

### Notes

This entry is the broad compatibility baseline for the catalog.

### Derived fields

<!-- catalog:derived:start TC-001 -->
- **Supported GPUs:** `GPU-A`, `GPU-B`, `GPU-C`
- **Timeout:** `26 s`
- **Pass rate:** `degraded` (`90.00%`)
- **Last measurement:** `2025-12-05T18:00:00Z` (`fresh`)
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
      "value": "2025-12-05T18:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 90.0,
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
        "GPU-A",
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
      "value": 26
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-001"
}
-->
<!-- catalog:derived:end TC-001 -->

### Summary

Baseline compute currently has measurements across all compatible GPU models.
