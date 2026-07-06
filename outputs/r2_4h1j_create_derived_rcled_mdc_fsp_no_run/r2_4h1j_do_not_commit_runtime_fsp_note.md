# Do not commit runtime FSP

The derived FSP is a runtime artifact only:

`D:\project\worktrees\blue_apcd_rcled_mdc\runtime\r2_4h1j_rcled_mdc_derived_fsp_DO_NOT_COMMIT\MDC_blue_oujizi_RCLED_QWexact10pair_H1J.fsp`

The runtime directory contains a `.gitignore` that blocks `.fsp`, `.fspx`, `.ldf`, `.mat`, `.h5`, image, and video files. Commit only lightweight audit files and the `.gitignore`, never the derived FSP.
