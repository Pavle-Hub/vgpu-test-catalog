# vGPU Test Catalog

This synthetic catalog demonstrates guarded maintenance of a mixed-ownership
software artifact. Text outside the marked derived blocks is not mechanically
rewritten by `catalog-check --write`.

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

## TC-002

### Purpose

Exercise the graphics capability used by rendering-oriented workloads.

### Notes

The test is intentionally independent of advanced compute requirements.

### Derived fields

<!-- catalog:derived:start TC-002 -->
- **Supported GPUs:** `GPU-A`, `GPU-B`, `GPU-C`
- **Timeout:** `34 s`
- **Pass rate:** `degraded` (`90.00%`)
- **Last measurement:** `2025-12-09T12:00:00Z` (`fresh`)
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
      "value": "2025-12-09T12:00:00Z"
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
      "value": 34
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-002"
}
-->
<!-- catalog:derived:end TC-002 -->

### Summary

Graphics coverage currently spans every GPU model exposing that capability.

## TC-003

### Purpose

Validate the advanced compute path on capable vGPU configurations.

### Notes

Basic-only GPU configurations are intentionally excluded by the capability rule.

### Derived fields

<!-- catalog:derived:start TC-003 -->
- **Supported GPUs:** `GPU-B`, `GPU-C`
- **Timeout:** `41 s`
- **Pass rate:** `degraded` (`86.67%`)
- **Last measurement:** `2025-12-12T00:00:00Z` (`fresh`)
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
      "value": "2025-12-12T00:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 86.67,
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
      "value": 41
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-003"
}
-->
<!-- catalog:derived:end TC-003 -->

### Summary

Advanced compute measurements are available on the compatible GPU subset.

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

## TC-005

### Purpose

Validate behavior that depends on synthetic multi-instance support.

### Notes

This single-capability case provides a narrow compatibility example.

### Derived fields

<!-- catalog:derived:start TC-005 -->
- **Supported GPUs:** `GPU-C`
- **Timeout:** `56 s`
- **Pass rate:** `degraded` (`83.33%`)
- **Last measurement:** `2025-12-15T18:00:00Z` (`fresh`)
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
      "value": "2025-12-15T18:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 83.33,
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
      "value": 56
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-005"
}
-->
<!-- catalog:derived:end TC-005 -->

### Summary

Multi-instance behavior currently has evidence on its sole compatible GPU model.

## TC-006

### Purpose

Exercise a workload requiring both advanced compute and graphics capabilities.

### Notes

Both declared requirements must be present for a GPU to be considered supported.

### Derived fields

<!-- catalog:derived:start TC-006 -->
- **Supported GPUs:** `GPU-B`, `GPU-C`
- **Timeout:** `63 s`
- **Pass rate:** `degraded` (`86.67%`)
- **Last measurement:** `2025-12-18T06:00:00Z` (`fresh`)
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
      "value": "2025-12-18T06:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 86.67,
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
      "value": 63
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-006"
}
-->
<!-- catalog:derived:end TC-006 -->

### Summary

The combined compute and graphics path is measured on compatible GPU models.

## TC-007

### Purpose

Validate a baseline compute workload with an additional large-memory requirement.

### Notes

The entry demonstrates conjunctive capability matching across two requirements.

### Derived fields

<!-- catalog:derived:start TC-007 -->
- **Supported GPUs:** `GPU-B`, `GPU-C`
- **Timeout:** `70 s`
- **Pass rate:** `degraded` (`93.33%`)
- **Last measurement:** `2025-12-20T18:00:00Z` (`fresh`)
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
      "value": "2025-12-20T18:00:00Z"
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
      "value": 70
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-007"
}
-->
<!-- catalog:derived:end TC-007 -->

### Summary

Current evidence covers the GPUs satisfying both compute and memory requirements.

## TC-008

### Purpose

Exercise advanced compute together with the multi-instance capability.

### Notes

The strict capability combination intentionally narrows the supported GPU set.

### Derived fields

<!-- catalog:derived:start TC-008 -->
- **Supported GPUs:** `GPU-C`
- **Timeout:** `78 s`
- **Pass rate:** `critical` (`73.33%`)
- **Last measurement:** `2025-12-22T00:00:00Z` (`fresh`)
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
      "value": "2025-12-22T00:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 73.33,
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "requires_each_gpu_samples>=10; min_gpu(passed / samples * 100), round_half_up(2); healthy>=95, degraded>=80",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": "critical"
    },
    "supported_gpus": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "required_capabilities subset_of gpu.capabilities",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": [
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
      "value": 78
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-008"
}
-->
<!-- catalog:derived:end TC-008 -->

### Summary

This advanced multi-instance workload is measured on its compatible environment.

## TC-009

### Purpose

Validate a graphics workload that also requires the large-memory capability.

### Notes

Support is computed from the intersection of graphics and memory capabilities.

### Derived fields

<!-- catalog:derived:start TC-009 -->
- **Supported GPUs:** `GPU-B`, `GPU-C`
- **Timeout:** `84 s`
- **Pass rate:** `degraded` (`86.67%`)
- **Last measurement:** `2025-12-24T12:00:00Z` (`fresh`)
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
      "value": "2025-12-24T12:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": 86.67,
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
      "value": 84
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-009"
}
-->
<!-- catalog:derived:end TC-009 -->

### Summary

Graphics and large-memory measurements cover the compatible GPU subset.

## TC-010

### Purpose

Exercise the strictest workload requiring advanced compute, memory, and isolation.

### Notes

The reference snapshot intentionally contains too few samples for confidence.

### Derived fields

<!-- catalog:derived:start TC-010 -->
- **Supported GPUs:** `GPU-C`
- **Timeout:** `insufficient-data`
- **Pass rate:** `insufficient-data`
- **Last measurement:** `2025-12-24T17:00:00Z` (`fresh`)
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
      "value": "2025-12-24T17:00:00Z"
    },
    "pass_rate_badge": {
      "pass_rate_percent": null,
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "requires_each_gpu_samples>=10; min_gpu(passed / samples * 100), round_half_up(2); healthy>=95, degraded>=80",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "insufficient-data",
      "value": "insufficient-data"
    },
    "supported_gpus": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "required_capabilities subset_of gpu.capabilities",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "ok",
      "value": [
        "GPU-C"
      ]
    },
    "timeout_seconds": {
      "provenance": {
        "computed_at": "2026-01-01T00:00:00Z",
        "formula": "requires_each_gpu_samples>=10; ceil(max_gpu(nearest_rank_p95(duration_seconds)) * 1.25)",
        "source_hash": "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
      },
      "status": "insufficient-data",
      "value": null
    }
  },
  "format_version": "1.0",
  "testcase_id": "TC-010"
}
-->
<!-- catalog:derived:end TC-010 -->

### Summary

Available evidence is intentionally insufficient for reliable metric derivation.
