# R2-4D8 Center-vs-X-Line Failure Diagnosis

D7 shows that center-only behavior is not representative for `D5_BASE_13461`.

| quantity | center source | x-line average |
|---|---:|---:|
| peak_abs_angle_deg | 0.028662222062435815 | 14.041304042576005 |
| normal/offaxis ratio | 0.2304507616040059 | 0.18235750919538307 |
| eta20 | 0.6830131767548334 | 0.5769653296309408 |
| eta30 | 0.7686416902764788 | 0.6578371753948261 |

The center source is near-normal, but the x-line ensemble is not. Some x positions revive the 30-40 deg off-axis lobe, and the averaged normal/offaxis ratio remains below 1. Therefore the old center-only proxy failed because it optimized a single local source condition instead of source-position stability.
