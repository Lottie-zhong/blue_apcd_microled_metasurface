# NP-K6 P1-D1A0 H500/D110 recovery closure

The remote worktree already contained a post-run FSP whose SHA256 matched the historical P1-D1A H500/D110 result record. Per the recovery gate, no new solver run was started. A foreground SSH read-only Lumerical session loaded the post-run FSP, verified the fixed geometry/reference coordinates and required monitor results, then closed it with an unchanged SHA256, size, and mtime.

The recovered x-polarized result is `T=0.9669356649635495`, `R_total=0.015635996934177582`, `|t_xx|=1.0213655336993614`, and wrapped `t_xx` phase `91.23263843960147 deg`. The energy residual is `0.017428338102272872` and the x-input reconstruction residual is `0.027641829271883477`; both meet the <=0.03 pass gate. This is one completed x-only point, not a completed H500 phase line or a full Jones matrix.
