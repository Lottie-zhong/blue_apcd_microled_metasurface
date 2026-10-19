# Git Commit and Push Record (V2)

## Branch / upstream

- Branch：`work/mdc-np-coupling-ml-v1`
- Upstream：`refs/remotes/origin/work/mdc-np-coupling-ml-v1`
- Remote：`ssh://git@ssh.github.com:443/Lottie-zhong/blue_apcd_microled_metasurface.git`
- V2 报告提交前 ahead/behind：`10/0`

## V2 已生成的提交

- `c65602fc archive: preserve native Coupling data receipts`
- `52e0a052 chore: scope native output ignores`
- `9f85444c test: preserve isolated runner fixtures`
- `a4fe45d6 archive: preserve coupling data indexes`
- `ba0185f2 archive: preserve coupling scientific reports`
- `8d6752a1 archive: preserve coupling analysis scripts`
- `ce2ec07e chore: ignore coupling science binaries`
- `11e9cf66 feat: add scoped partial development diagnostic purpose`
- `3600560d fix: scope K6 controller status paths and reconciliation`
- `982f0581 docs: record Coupling worktree cleanup audit`

以上十个提交均为正常后续提交，无 reset/rebase/amend/force-push。逐批 add 使用文件 allowlist；4 项原 staging 已精确 unstage。

## Push preflight

Outgoing-object scan 覆盖当前待推送历史：3,703 Git objects、2,886 blobs、98,620,223 bytes；凭据/密钥模式命中 0；大于 10 MiB 的 blob 0；FSP/H5/NPZ/model binary 大型 blob 0。正式 origin 和 tracking ref 已现场确认。

三项定向零求解测试：18 passed。随后对包含 V2 最终报告提交的当前分支执行普通 fast-forward `git push origin work/mdc-np-coupling-ml-v1`，并以本地 HEAD 与 `refs/remotes/origin/work/mdc-np-coupling-ml-v1` 对账；不使用 force push。最终执行结果在 closeout 中记录。

本文件随 V2 最终报告组提交；避免自引用，此处不列该报告组自身 commit hash。
